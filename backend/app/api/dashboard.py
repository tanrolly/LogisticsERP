"""Dashboard 数据看板 API"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.purchase import PurchaseRequest, PurchaseOrder
from app.models.transport import Order as TransportOrder
from app.models.inbound import InboundOrder
from app.models.stock import OutboundOrder, Inventory
from app.models.collab import OperationLog
from app.models.group import Group
from app.models.finance import AccountsPayable, AccountsReceivable
from app.models.contract import PurchaseContract, TransportContract
from app.utils.time_helper import beijing_now

bp = Blueprint('dashboard', __name__)


@bp.route('/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """获取Dashboard统计数据"""
    try:
        # 采购模块统计
        pr_total = PurchaseRequest.query.count()
        pr_pending = PurchaseRequest.query.filter_by(status='pending').count()
        pr_approved = PurchaseRequest.query.filter_by(status='approved').count()

        po_total = PurchaseOrder.query.count()
        po_active = PurchaseOrder.query.filter(
            PurchaseOrder.status.in_(['approved', 'partial_received'])
        ).count()

        # 运输模块统计
        to_total = TransportOrder.query.count()
        to_in_transit = TransportOrder.query.filter_by(status='in_transit').count()
        to_pending = TransportOrder.query.filter_by(status='pending').count()

        # 仓储模块统计
        io_pending = InboundOrder.query.filter_by(status='pending').count()
        oo_pending = OutboundOrder.query.filter_by(status='pending').count()

        # 库存统计
        inv_total = Inventory.query.count()
        # 库存预警：可用数量为0或库存被锁定
        inv_low = Inventory.query.filter(
            (Inventory.available_qty <= 0) | (Inventory.status == 'locked')
        ).count()

        # 协作房间统计
        active_rooms = Group.query.filter_by(status='active').count()

        # 近期操作统计（今日）
        today = beijing_now().date()
        today_ops = OperationLog.query.filter(
            db.func.date(OperationLog.created_at) == today
        ).count()

        # 财务模块统计
        ap_pending = AccountsPayable.query.filter_by(status='pending').count()
        ar_pending = AccountsReceivable.query.filter_by(status='pending').count()
        ap_total_amount = db.session.query(
            db.func.coalesce(db.func.sum(AccountsPayable.total_amount), 0)
        ).scalar()
        ar_total_amount = db.session.query(
            db.func.coalesce(db.func.sum(AccountsReceivable.total_amount), 0)
        ).scalar()

        # 合同管理统计
        pc_pending = PurchaseContract.query.filter_by(status='pending').count()
        pc_approved = PurchaseContract.query.filter_by(status='approved').count()
        pc_active = PurchaseContract.query.filter_by(status='active').count()
        tc_pending = TransportContract.query.filter_by(status='pending').count()
        tc_approved = TransportContract.query.filter_by(status='approved').count()
        tc_active = TransportContract.query.filter_by(status='active').count()

        stats = {
            'purchase': {
                'request_total': pr_total,
                'request_pending': pr_pending,
                'request_approved': pr_approved,
                'order_total': po_total,
                'order_active': po_active,
            },
            'transport': {
                'order_total': to_total,
                'order_in_transit': to_in_transit,
                'order_pending': to_pending,
            },
            'warehouse': {
                'inbound_pending': io_pending,
                'outbound_pending': oo_pending,
            },
            'inventory': {
                'item_total': inv_total,
                'item_low_stock': inv_low,
            },
            'collab': {
                'active_rooms': active_rooms,
            },
            'today_ops': today_ops,
            'finance': {
                'payable_pending': ap_pending,
                'receivable_pending': ar_pending,
                'payable_total_amount': float(ap_total_amount),
                'receivable_total_amount': float(ar_total_amount),
            },
            'contract': {
                'purchase_pending': pc_pending,
                'purchase_approved': pc_approved,
                'purchase_active': pc_active,
                'transport_pending': tc_pending,
                'transport_approved': tc_approved,
                'transport_active': tc_active,
            },
        }

        return jsonify({'code': 200, 'message': 'success', 'data': stats})

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None})


@bp.route('/dashboard/recent-activities', methods=['GET'])
@login_required
def get_recent_activities():
    """获取近期操作动态"""
    try:
        limit = request.args.get('limit', 10, type=int)

        logs = OperationLog.query.order_by(
            OperationLog.created_at.desc()
        ).limit(limit).all()

        result = []
        for log in logs:
            result.append({
                'id': log.id,
                'user_name': log.user.real_name if log.user else '未知用户',
                'action': log.action,
                'module': log.module,
                'target': log.target_type or log.module,
                'detail': log.description,
                'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

        return jsonify({'code': 200, 'message': 'success', 'data': result})

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None})


@bp.route('/dashboard/my-tasks', methods=['GET'])
@login_required
def get_my_tasks():
    """获取当前用户的待办事项"""
    try:
        tasks = []
        role_code = current_user.role_code

        # 待审批的采购申请（管理员/采购经理）
        if role_code in ('admin', 'purchase_manager'):
            prs = PurchaseRequest.query.filter_by(status='pending').limit(5).all()
            for pr in prs:
                tasks.append({
                    'type': 'purchase_request',
                    'id': pr.id,
                    'title': f'采购申请审批 - {pr.pr_no}',
                    'status': pr.status,
                    'created_at': pr.created_at.strftime('%Y-%m-%d %H:%M'),
                })

        # 待处理的运输订单（管理员/调度员）
        if role_code in ('admin', 'dispatcher'):
            tos = TransportOrder.query.filter_by(status='pending').limit(5).all()
            for to in tos:
                tasks.append({
                    'type': 'transport_order',
                    'id': to.id,
                    'title': f'运输订单待调度 - {to.order_no}',
                    'status': to.status,
                    'created_at': to.created_at.strftime('%Y-%m-%d %H:%M'),
                })

        # 待处理的入库单（管理员/仓管员）
        if role_code in ('admin', 'warehouse_keeper'):
            ios = InboundOrder.query.filter_by(status='pending').limit(5).all()
            for io in ios:
                tasks.append({
                    'type': 'inbound_order',
                    'id': io.id,
                    'title': f'入库单待处理 - {io.order_no}',
                    'status': io.status,
                    'created_at': io.created_at.strftime('%Y-%m-%d %H:%M'),
                })

        # 按创建时间排序
        tasks.sort(key=lambda x: x['created_at'], reverse=True)

        return jsonify({'code': 200, 'message': 'success', 'data': tasks[:10]})

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None})
