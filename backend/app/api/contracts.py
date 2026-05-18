"""
合同管理 API 端点

包含采购合同和运输合同的 CRUD、审批流、终止等操作。
"""
from datetime import date
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.contract import PurchaseContract, TransportContract
from app.models.purchase import PurchaseOrder
from app.models.transport import Order
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.utils.scoring import score_operation
from app.utils.time_helper import beijing_now
from app.extensions import socketio
from app.utils.permissions import role_required
from app.models.approval import ApprovalRecord

bp = Blueprint('contracts', __name__, url_prefix='/api/contracts')


# ==================== 编号生成函数 ====================

def generate_purchase_contract_no():
    """生成采购合同编号 PC-YYYYMMDDNNN"""
    today = date.today().strftime('%Y%m%d')
    prefix = f'PC-{today}'
    last = PurchaseContract.query.filter(
        PurchaseContract.contract_no.like(f'{prefix}%')
    ).order_by(PurchaseContract.contract_no.desc()).first()
    seq = 1
    if last:
        try:
            seq = int(last.contract_no[-3:]) + 1
        except ValueError:
            seq = 1
    return f'{prefix}{seq:03d}'


def generate_transport_contract_no():
    """生成运输合同编号 TC-YYYYMMDDNNN"""
    today = date.today().strftime('%Y%m%d')
    prefix = f'TC-{today}'
    last = TransportContract.query.filter(
        TransportContract.contract_no.like(f'{prefix}%')
    ).order_by(TransportContract.contract_no.desc()).first()
    seq = 1
    if last:
        try:
            seq = int(last.contract_no[-3:]) + 1
        except ValueError:
            seq = 1
    return f'{prefix}{seq:03d}'


# ==================== 采购合同 API ====================

@bp.route('/purchase', methods=['GET'])
@login_required
def get_purchase_contracts():
    """获取采购合同列表（分页+筛选）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status', '')
    supplier_id = request.args.get('supplier_id', type=int)

    query = PurchaseContract.query
    if status:
        query = query.filter_by(status=status)
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)

    total = query.count()
    contracts = query.order_by(PurchaseContract.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    ).items

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total': total,
            'items': [c.to_dict() for c in contracts]
        }
    })


@bp.route('/purchase/eligible', methods=['GET'])
@login_required
def get_eligible_purchase_orders():
    """获取可生成采购合同的采购订单列表（已审批通过的订单）"""
    # 查找已审批通过但未生成合同的采购订单
    subquery = db.session.query(PurchaseContract.po_id).filter(
        PurchaseContract.po_id.isnot(None)
    ).all()
    used_po_ids = [row[0] for row in subquery]
    
    query = PurchaseOrder.query.filter_by(status='approved')
    if used_po_ids:
        query = query.filter(~PurchaseOrder.id.in_(used_po_ids))
    
    orders = query.order_by(PurchaseOrder.created_at.desc()).all()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': [o.to_dict() for o in orders]
    })


@bp.route('/purchase', methods=['POST'])
@login_required
def create_purchase_contract():
    """从采购订单生成采购合同"""
    if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
        return jsonify({'code': 401, 'message': '请先登录', 'data': None}), 401

    data = request.get_json()
    po_id = data.get('po_id')
    if not po_id:
        return jsonify({'code': 400, 'message': '缺少采购订单ID', 'data': None}), 400

    # 检查采购订单是否存在且已审批
    po = PurchaseOrder.query.get(po_id)
    if not po:
        return jsonify({'code': 404, 'message': '采购订单不存在', 'data': None}), 404
    if po.status != 'approved':
        return jsonify({'code': 400, 'message': '只有已审批通过的采购订单才能生成合同', 'data': None}), 400

    # 检查是否已生成合同
    existing = PurchaseContract.query.filter_by(po_id=po_id).first()
    if existing:
        return jsonify({'code': 400, 'message': '该采购订单已生成合同', 'data': None}), 400

    # 创建合同
    contract = PurchaseContract(
        contract_no=generate_purchase_contract_no(),
        po_id=po_id,
        supplier_id=po.supplier_id,
        total_amount=po.total_amount,
        payment_terms=data.get('payment_terms', ''),
        delivery_terms=data.get('delivery_terms', ''),
        status=PurchaseContract.STATUS_PENDING,
        operator_id=current_user.id,
    )
    # 可选字段
    if data.get('sign_date'):
        contract.sign_date = datetime.strptime(data['sign_date'], '%Y-%m-%d').date()
    if data.get('start_date'):
        contract.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    if data.get('end_date'):
        contract.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()

    db.session.add(contract)
    db.session.commit()

    # 写入审批记录（提交）
    record = ApprovalRecord(
        target_type='purchase_contract', target_id=contract.id,
        action='submit', comment=f'创建采购合同 {contract.contract_no}',
        operator_id=current_user.id, operator_name=current_user.real_name
    )
    db.session.add(record)

    # 评分
    score_operation(
        user_id=current_user.id,
        group_id=None,
        module='contract',
        action='create_purchase',
        is_correct=True,
        extra_data={'description': f'创建采购合同 {contract.contract_no}'}
    )

    # 操作日志
    from app.models.collab import OperationLog
    log = OperationLog(
        user_id=current_user.id,
        module='contract',
        action='create_purchase',
        target_type='PurchaseContract',
        target_id=contract.id,
        description=f'创建采购合同 {contract.contract_no}，关联采购订单 {po.po_no}',
        is_correct=True,
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': '采购合同创建成功，请等待审批',
        'data': contract.to_dict()
    })


@bp.route('/purchase/<int:contract_id>', methods=['GET'])
@login_required
def get_purchase_contract_detail(contract_id):
    """获取采购合同详情"""
    contract = PurchaseContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    return jsonify({'code': 200, 'message': 'success', 'data': contract.to_dict()})


@bp.route('/purchase/<int:contract_id>/approve', methods=['PUT'])
@role_required('admin', 'purchaser')
@login_required
def approve_purchase_contract(contract_id):
    """审批通过采购合同"""
    contract = PurchaseContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    if contract.status != PurchaseContract.STATUS_PENDING:
        return jsonify({'code': 400, 'message': '只有待审批的合同才能审批', 'data': None}), 400

    data = request.get_json() or {}
    contract.status = PurchaseContract.STATUS_APPROVED
    contract.reviewer_id = current_user.id
    contract.review_comment = data.get('comment', '')
    contract.reviewed_at = beijing_now()

    db.session.commit()

    # 写入审批记录
    record = ApprovalRecord(
        target_type='purchase_contract', target_id=contract.id,
        action='approve', comment=data.get('comment', ''),
        operator_id=current_user.id, operator_name=current_user.real_name
    )
    db.session.add(record)

    # 评分
    score_operation(
        user_id=current_user.id,
        group_id=None,
        module='contract',
        action='approve_purchase',
        is_correct=True,
        extra_data={'description': f'审批通过采购合同 {contract.contract_no}'}
    )

    return jsonify({'code': 200, 'message': '审批通过', 'data': contract.to_dict()})


@bp.route('/purchase/<int:contract_id>/return', methods=['PUT'])
@role_required('admin', 'purchaser')
@login_required
def return_purchase_contract(contract_id):
    """退回采购合同（可重新提交）"""
    contract = PurchaseContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    if contract.status != PurchaseContract.STATUS_PENDING:
        return jsonify({'code': 400, 'message': '只有待审批的合同才能退回', 'data': None}), 400

    data = request.get_json() or {}
    comment = data.get('comment', '')
    if not comment:
        return jsonify({'code': 400, 'message': '退回意见不能为空', 'data': None}), 400

    contract.status = PurchaseContract.STATUS_REJECTED  # 复用rejected状态标记退回
    contract.reviewer_id = current_user.id
    contract.review_comment = comment
    contract.reviewed_at = beijing_now()

    db.session.commit()

    record = ApprovalRecord(
        target_type='purchase_contract', target_id=contract.id,
        action='return', comment=comment,
        operator_id=current_user.id, operator_name=current_user.real_name
    )
    db.session.add(record)

    return jsonify({'code': 200, 'message': '已退回', 'data': contract.to_dict()})


@bp.route('/purchase/<int:contract_id>/reject', methods=['PUT'])
@role_required('admin', 'purchaser')
@login_required
def reject_purchase_contract(contract_id):
    """驳回采购合同"""
    contract = PurchaseContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    if contract.status != PurchaseContract.STATUS_PENDING:
        return jsonify({'code': 400, 'message': '只有待审批的合同才能驳回', 'data': None}), 400

    data = request.get_json() or {}
    contract.status = PurchaseContract.STATUS_REJECTED
    contract.reviewer_id = current_user.id
    contract.review_comment = data.get('comment', '')
    contract.reviewed_at = beijing_now()

    db.session.commit()

    # 写入审批记录
    record = ApprovalRecord(
        target_type='purchase_contract', target_id=contract.id,
        action='reject', comment=data.get('comment', ''),
        operator_id=current_user.id, operator_name=current_user.real_name
    )
    db.session.add(record)

    return jsonify({'code': 200, 'message': '已驳回', 'data': contract.to_dict()})


@bp.route('/purchase/<int:contract_id>/terminate', methods=['PUT'])
@role_required('admin')
@login_required
def terminate_purchase_contract(contract_id):
    """终止采购合同"""
    contract = PurchaseContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    if contract.status not in (PurchaseContract.STATUS_APPROVED, PurchaseContract.STATUS_ACTIVE):
        return jsonify({'code': 400, 'message': '只有已审批或生效的合同才能终止', 'data': None}), 400

    contract.status = PurchaseContract.STATUS_TERMINATED
    db.session.commit()

    # 评分
    score_operation(
        user_id=current_user.id,
        group_id=None,
        module='contract',
        action='terminate',
        is_correct=True,
        extra_data={'description': f'终止采购合同 {contract.contract_no}'}
    )

    return jsonify({'code': 200, 'message': '合同已终止', 'data': contract.to_dict()})


# ==================== 运输合同 API ====================

@bp.route('/transport', methods=['GET'])
@login_required
def get_transport_contracts():
    """获取运输合同列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status', '')
    customer_id = request.args.get('customer_id', type=int)

    query = TransportContract.query
    if status:
        query = query.filter_by(status=status)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)

    total = query.count()
    contracts = query.order_by(TransportContract.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    ).items

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total': total,
            'items': [c.to_dict() for c in contracts]
        }
    })


@bp.route('/transport/eligible', methods=['GET'])
@login_required
def get_eligible_transport_orders():
    """获取可生成运输合同的运输订单列表（已审批通过的订单）"""
    # 查找已审批通过但未生成合同的运输订单
    subquery = db.session.query(TransportContract.order_id).filter(
        TransportContract.order_id.isnot(None)
    ).all()
    used_order_ids = [row[0] for row in subquery]
    
    query = Order.query.filter_by(status='approved')
    if used_order_ids:
        query = query.filter(~Order.id.in_(used_order_ids))
    
    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': [o.to_dict() for o in orders]
    })


@bp.route('/transport', methods=['POST'])
@login_required
def create_transport_contract():
    """从运输订单生成运输合同"""
    if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
        return jsonify({'code': 401, 'message': '请先登录', 'data': None}), 401

    data = request.get_json()
    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'code': 400, 'message': '缺少运输订单ID', 'data': None}), 400

    # 检查运输订单是否存在且已审批
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'code': 404, 'message': '运输订单不存在', 'data': None}), 404
    if order.status != 'approved':
        return jsonify({'code': 400, 'message': '只有已审批通过的运输订单才能生成合同', 'data': None}), 400

    # 检查是否已生成合同
    existing = TransportContract.query.filter_by(order_id=order_id).first()
    if existing:
        return jsonify({'code': 400, 'message': '该运输订单已生成合同', 'data': None}), 400

    # 创建合同
    contract = TransportContract(
        contract_no=generate_transport_contract_no(),
        order_id=order_id,
        customer_id=order.customer_id,
        freight_amount=order.freight_amount or 0,
        payment_terms=data.get('payment_terms', ''),
        transport_terms=data.get('transport_terms', ''),
        status=TransportContract.STATUS_PENDING,
        operator_id=current_user.id,
    )
    if data.get('sign_date'):
        contract.sign_date = datetime.strptime(data['sign_date'], '%Y-%m-%d').date()
    if data.get('start_date'):
        contract.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    if data.get('end_date'):
        contract.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()

    db.session.add(contract)
    db.session.commit()

    # 写入审批记录（提交）
    record = ApprovalRecord(
        target_type='transport_contract', target_id=contract.id,
        action='submit', comment=f'创建运输合同 {contract.contract_no}',
        operator_id=current_user.id, operator_name=current_user.real_name
    )
    db.session.add(record)

    # 评分
    score_operation(
        user_id=current_user.id,
        group_id=None,
        module='contract',
        action='create_transport',
        is_correct=True,
        extra_data={'description': f'创建运输合同 {contract.contract_no}'}
    )

    # 操作日志
    from app.models.collab import OperationLog
    log = OperationLog(
        user_id=current_user.id,
        module='contract',
        action='create_transport',
        target_type='TransportContract',
        target_id=contract.id,
        description=f'创建运输合同 {contract.contract_no}，关联运输订单 {order.order_no}',
        is_correct=True,
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': '运输合同创建成功，请等待审批',
        'data': contract.to_dict()
    })


@bp.route('/transport/<int:contract_id>', methods=['GET'])
@login_required
def get_transport_contract_detail(contract_id):
    """获取运输合同详情"""
    contract = TransportContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    return jsonify({'code': 200, 'message': 'success', 'data': contract.to_dict()})


@bp.route('/transport/<int:contract_id>/approve', methods=['PUT'])
@role_required('admin', 'dispatcher')
@login_required
def approve_transport_contract(contract_id):
    """审批通过运输合同"""
    contract = TransportContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    if contract.status != TransportContract.STATUS_PENDING:
        return jsonify({'code': 400, 'message': '只有待审批的合同才能审批', 'data': None}), 400

    data = request.get_json() or {}
    contract.status = TransportContract.STATUS_APPROVED
    contract.reviewer_id = current_user.id
    contract.review_comment = data.get('comment', '')
    contract.reviewed_at = beijing_now()

    db.session.commit()

    # 写入审批记录
    record = ApprovalRecord(
        target_type='transport_contract', target_id=contract.id,
        action='approve', comment=data.get('comment', ''),
        operator_id=current_user.id, operator_name=current_user.real_name
    )
    db.session.add(record)

    # 评分
    score_operation(
        user_id=current_user.id,
        group_id=None,
        module='contract',
        action='approve_transport',
        is_correct=True,
        extra_data={'description': f'审批通过运输合同 {contract.contract_no}'}
    )

    return jsonify({'code': 200, 'message': '审批通过', 'data': contract.to_dict()})


@bp.route('/transport/<int:contract_id>/return', methods=['PUT'])
@role_required('admin', 'dispatcher')
@login_required
def return_transport_contract(contract_id):
    """退回运输合同（可重新提交）"""
    contract = TransportContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    if contract.status != TransportContract.STATUS_PENDING:
        return jsonify({'code': 400, 'message': '只有待审批的合同才能退回', 'data': None}), 400

    data = request.get_json() or {}
    comment = data.get('comment', '')
    if not comment:
        return jsonify({'code': 400, 'message': '退回意见不能为空', 'data': None}), 400

    contract.status = TransportContract.STATUS_REJECTED
    contract.reviewer_id = current_user.id
    contract.review_comment = comment
    contract.reviewed_at = beijing_now()

    db.session.commit()

    record = ApprovalRecord(
        target_type='transport_contract', target_id=contract.id,
        action='return', comment=comment,
        operator_id=current_user.id, operator_name=current_user.real_name
    )
    db.session.add(record)

    return jsonify({'code': 200, 'message': '已退回', 'data': contract.to_dict()})


@bp.route('/transport/<int:contract_id>/reject', methods=['PUT'])
@role_required('admin', 'dispatcher')
@login_required
def reject_transport_contract(contract_id):
    """驳回运输合同"""
    contract = TransportContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    if contract.status != TransportContract.STATUS_PENDING:
        return jsonify({'code': 400, 'message': '只有待审批的合同才能驳回', 'data': None}), 400

    data = request.get_json() or {}
    contract.status = TransportContract.STATUS_REJECTED
    contract.reviewer_id = current_user.id
    contract.review_comment = data.get('comment', '')
    contract.reviewed_at = beijing_now()

    db.session.commit()

    # 写入审批记录
    record = ApprovalRecord(
        target_type='transport_contract', target_id=contract.id,
        action='reject', comment=data.get('comment', ''),
        operator_id=current_user.id, operator_name=current_user.real_name
    )
    db.session.add(record)

    return jsonify({'code': 200, 'message': '已驳回', 'data': contract.to_dict()})


@bp.route('/transport/<int:contract_id>/terminate', methods=['PUT'])
@role_required('admin')
@login_required
def terminate_transport_contract(contract_id):
    """终止运输合同"""
    contract = TransportContract.query.get(contract_id)
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在', 'data': None}), 404
    if contract.status not in (TransportContract.STATUS_APPROVED, TransportContract.STATUS_ACTIVE):
        return jsonify({'code': 400, 'message': '只有已审批或生效的合同才能终止', 'data': None}), 400

    contract.status = TransportContract.STATUS_TERMINATED
    db.session.commit()

    # 评分
    score_operation(
        user_id=current_user.id,
        group_id=None,
        module='contract',
        action='terminate',
        is_correct=True,
        extra_data={'description': f'终止运输合同 {contract.contract_no}'}
    )

    return jsonify({'code': 200, 'message': '合同已终止', 'data': contract.to_dict()})


# ==================== 统计 API ====================

@bp.route('/overview', methods=['GET'])
@login_required
def get_contract_overview():
    """获取合同概览统计"""
    # 采购合同统计
    pc_total = PurchaseContract.query.count()
    pc_pending = PurchaseContract.query.filter_by(status=PurchaseContract.STATUS_PENDING).count()
    pc_approved = PurchaseContract.query.filter_by(status=PurchaseContract.STATUS_APPROVED).count()
    pc_active = PurchaseContract.query.filter_by(status=PurchaseContract.STATUS_ACTIVE).count()
    pc_completed = PurchaseContract.query.filter_by(status=PurchaseContract.STATUS_COMPLETED).count()
    pc_terminated = PurchaseContract.query.filter_by(status=PurchaseContract.STATUS_TERMINATED).count()

    # 运输合同统计
    tc_total = TransportContract.query.count()
    tc_pending = TransportContract.query.filter_by(status=TransportContract.STATUS_PENDING).count()
    tc_approved = TransportContract.query.filter_by(status=TransportContract.STATUS_APPROVED).count()
    tc_active = TransportContract.query.filter_by(status=TransportContract.STATUS_ACTIVE).count()
    tc_completed = TransportContract.query.filter_by(status=TransportContract.STATUS_COMPLETED).count()
    tc_terminated = TransportContract.query.filter_by(status=TransportContract.STATUS_TERMINATED).count()

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'purchase': {
                'total': pc_total,
                'pending': pc_pending,
                'approved': pc_approved,
                'active': pc_active,
                'completed': pc_completed,
                'terminated': pc_terminated,
            },
            'transport': {
                'total': tc_total,
                'pending': tc_pending,
                'approved': tc_approved,
                'active': tc_active,
                'completed': tc_completed,
                'terminated': tc_terminated,
            }
        }
    })
