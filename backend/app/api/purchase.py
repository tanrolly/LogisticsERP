from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.purchase import PurchaseRequest, PurchaseOrder, PurchaseOrderItem, PurchaseReceipt
from app.models.inbound import InboundOrder, InboundItem
from app.models.goods import Goods
from app.models.supplier import Supplier
from app.socket import broadcast_order_status
from app.api.logs import log_operation
from app.utils.scoring import score_operation
from app.utils.time_helper import beijing_now
from app.utils.permissions import role_required
from app.models.approval import ApprovalRecord
from datetime import date

bp = Blueprint('purchase', __name__)


def success_response(data=None, message='success'):
    return jsonify({'code': 200, 'message': message, 'data': data}), 200


def error_response(message, code=400):
    return jsonify({'code': code, 'message': message, 'data': None}), 200


def generate_req_no():
    """生成采购申请单号 PR-YYYYMMDDNNN"""
    today = date.today().strftime('%Y%m%d')
    count = PurchaseRequest.query.filter(
        PurchaseRequest.req_no.like(f'PR-{today}%')
    ).count()
    return f'PR-{today}{count + 1:03d}'


def generate_po_no():
    """生成采购订单号 PO-YYYYMMDDNNN"""
    today = date.today().strftime('%Y%m%d')
    count = PurchaseOrder.query.filter(
        PurchaseOrder.po_no.like(f'PO-{today}%')
    ).count()
    return f'PO-{today}{count + 1:03d}'


def generate_inbound_no():
    """生成入库单号 IN-YYYYMMDDNNN"""
    today = date.today().strftime('%Y%m%d')
    count = InboundOrder.query.filter(
        InboundOrder.order_no.like(f'IN-{today}%')
    ).count()
    return f'IN-{today}{count + 1:03d}'


# ==================== 采购申请 ====================

@bp.route('/purchase-requests', methods=['GET'])
@login_required
def get_purchase_requests():
    """获取采购申请列表"""
    status = request.args.get('status')
    query = PurchaseRequest.query

    if status:
        query = query.filter_by(status=status)

    requests = query.order_by(PurchaseRequest.created_at.desc()).all()
    return success_response([r.to_dict() for r in requests])


@bp.route('/purchase-requests', methods=['POST'])
@login_required
def create_purchase_request():
    """创建采购申请"""
    data = request.get_json()

    if not data or not data.get('goods_id') or not data.get('quantity'):
        return error_response('商品和数量不能为空')

    goods = Goods.query.get(data['goods_id'])
    if not goods:
        return error_response('商品不存在')

    est_unit_price = data.get('est_unit_price')
    est_total_price = None
    if est_unit_price:
        est_total_price = float(est_unit_price) * int(data['quantity'])

    pr = PurchaseRequest(
        req_no=generate_req_no(),
        applicant_id=current_user.id,
        goods_id=data['goods_id'],
        quantity=int(data['quantity']),
        est_unit_price=est_unit_price,
        est_total_price=est_total_price,
        reason=data.get('reason', ''),
        urgency=data.get('urgency', 'normal'),
        status='pending'
    )

    db.session.add(pr)
    db.session.commit()

    # 记录审批记录（提交）
    _create_approval_record('purchase_request', pr.id, 'submit', current_user,
                            f'创建采购申请 {pr.req_no}')
    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='purchase_request',
        action='create',
        target_type='PurchaseRequest',
        target_id=pr.id,
        description=f'创建采购申请 {pr.req_no}'
    )
    db.session.commit()

    # 评分
    score_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='purchase_request',
        action='create'
    )

    return success_response(pr.to_dict(), '采购申请创建成功')


@bp.route('/purchase-requests/<int:pr_id>', methods=['GET'])
@login_required
def get_purchase_request(pr_id):
    """获取采购申请详情"""
    pr = PurchaseRequest.query.get_or_404(pr_id)
    return success_response(pr.to_dict())


@bp.route('/purchase-requests/<int:pr_id>/approve', methods=['PUT'])
@role_required('admin', 'purchaser')
@login_required
def approve_purchase_request(pr_id):
    """审批通过采购申请"""
    pr = PurchaseRequest.query.get_or_404(pr_id)

    if pr.status != 'pending':
        return error_response('该申请不在待审批状态')

    pr.status = 'approved'
    pr.reviewer_id = current_user.id
    pr.review_comment = request.get_json().get('comment', '') if request.get_json() else ''
    pr.reviewed_at = beijing_now()
    db.session.commit()

    _create_approval_record('purchase_request', pr.id, 'approve', current_user,
                            pr.review_comment)

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='purchase_request',
        action='approve',
        target_type='PurchaseRequest',
        target_id=pr.id,
        description=f'审批通过采购申请 {pr.req_no}'
    )
    db.session.commit()

    # 评分 + WebSocket 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='purchase_request', action='approve')
    broadcast_order_status('purchase_request', pr.id, 'approved', current_user.group_id)

    return success_response(pr.to_dict(), '审批通过')


@bp.route('/purchase-requests/<int:pr_id>/reject', methods=['PUT'])
@role_required('admin', 'purchaser')
@login_required
def reject_purchase_request(pr_id):
    """审批驳回采购申请"""
    pr = PurchaseRequest.query.get_or_404(pr_id)

    if pr.status != 'pending':
        return error_response('该申请不在待审批状态')

    data = request.get_json() or {}
    pr.status = 'rejected'
    pr.reviewer_id = current_user.id
    pr.review_comment = data.get('comment', '驳回')
    pr.reviewed_at = beijing_now()
    db.session.commit()

    _create_approval_record('purchase_request', pr.id, 'reject', current_user,
                            pr.review_comment)

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='purchase_request',
        action='reject',
        target_type='PurchaseRequest',
        target_id=pr.id,
        description=f'驳回采购申请 {pr.req_no}'
    )
    db.session.commit()

    # 评分（驳回操作也计分）
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='purchase_request', action='reject')
    broadcast_order_status('purchase_request', pr.id, 'rejected', current_user.group_id)

    return success_response(pr.to_dict(), '已驳回')


def _create_approval_record(target_type, target_id, action, operator, comment=''):
    """写入审批记录"""
    record = ApprovalRecord(
        target_type=target_type,
        target_id=target_id,
        action=action,
        comment=comment,
        operator_id=operator.id,
        operator_name=operator.real_name
    )
    db.session.add(record)


@bp.route('/purchase-requests/<int:pr_id>/return', methods=['PUT'])
@role_required('admin', 'purchaser')
@login_required
def return_purchase_request(pr_id):
    """退回采购申请（可重新提交）"""
    pr = PurchaseRequest.query.get_or_404(pr_id)

    if pr.status != 'pending':
        return error_response('该申请不在待审批状态')

    data = request.get_json() or {}
    comment = data.get('comment', '')
    if not comment:
        return error_response('退回意见不能为空')

    pr.status = 'returned'
    pr.reviewer_id = current_user.id
    pr.review_comment = comment
    pr.reviewed_at = beijing_now()
    db.session.commit()

    _create_approval_record('purchase_request', pr.id, 'return', current_user, comment)

    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='purchase_request',
        action='return',
        target_type='PurchaseRequest',
        target_id=pr.id,
        description=f'退回采购申请 {pr.req_no}，意见：{comment}'
    )
    db.session.commit()

    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='purchase_request', action='return')
    broadcast_order_status('purchase_request', pr.id, 'returned', current_user.group_id)

    return success_response(pr.to_dict(), '已退回，申请人可修改后重新提交')


@bp.route('/purchase-requests/<int:pr_id>/resubmit', methods=['PUT'])
@login_required
def resubmit_purchase_request(pr_id):
    """重新提交采购申请（仅申请人可操作）"""
    pr = PurchaseRequest.query.get_or_404(pr_id)

    if pr.status != 'returned':
        return error_response('只有被退回的申请才能重新提交')
    if pr.applicant_id != current_user.id:
        return error_response('只有申请人才能重新提交')

    pr.status = 'pending'
    pr.review_comment = None
    db.session.commit()

    _create_approval_record('purchase_request', pr.id, 'resubmit', current_user, '重新提交')

    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='purchase_request',
        action='resubmit',
        target_type='PurchaseRequest',
        target_id=pr.id,
        description=f'重新提交采购申请 {pr.req_no}'
    )
    db.session.commit()

    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='purchase_request', action='resubmit')
    broadcast_order_status('purchase_request', pr.id, 'pending', current_user.group_id)

    return success_response(pr.to_dict(), '采购申请已重新提交，等待审批')


# ==================== 采购订单 ====================

@bp.route('/purchase-orders', methods=['GET'])
@login_required
def get_purchase_orders():
    """获取采购订单列表"""
    status = request.args.get('status')
    query = PurchaseOrder.query

    if status:
        query = query.filter_by(status=status)

    orders = query.order_by(PurchaseOrder.created_at.desc()).all()
    return success_response([o.to_dict() for o in orders])


@bp.route('/purchase-orders', methods=['POST'])
@login_required
def create_purchase_order():
    """创建采购订单"""
    data = request.get_json()

    if not data or not data.get('request_id') or not data.get('supplier_id'):
        return error_response('采购申请和供应商不能为空')

    # 检查采购申请是否已审批通过
    pr = PurchaseRequest.query.get(data['request_id'])
    if not pr:
        return error_response('采购申请不存在')
    if pr.status != 'approved':
        return error_response('采购申请未审批通过')
    if pr.order:
        return error_response('该申请已创建订单')

    supplier = Supplier.query.get(data['supplier_id'])
    if not supplier:
        return error_response('供应商不存在')

    # 构建订单明细
    items_data = data.get('items', [])
    if not items_data:
        return error_response('订单明细不能为空')

    total_amount = 0
    expected_date = data.get('expected_date')
    if expected_date:
        if isinstance(expected_date, str):
            from datetime import date as date_type
            expected_date = date_type.fromisoformat(expected_date)

    po = PurchaseOrder(
        po_no=generate_po_no(),
        request_id=pr.id,
        supplier_id=supplier.id,
        total_amount=0,
        expected_date=expected_date,
        status='pending',
        operator_id=current_user.id
    )

    db.session.add(po)
    db.session.flush()  # 获取po.id

    for item_data in items_data:
        goods_id = item_data.get('goods_id', pr.goods_id)
        quantity = int(item_data.get('quantity', pr.quantity))
        unit_price = float(item_data.get('unit_price', 0))
        subtotal = quantity * unit_price

        item = PurchaseOrderItem(
            po_id=po.id,
            goods_id=goods_id,
            ordered_qty=quantity,
            unit_price=unit_price,
            subtotal=subtotal
        )
        db.session.add(item)
        total_amount += subtotal

    po.total_amount = total_amount
    db.session.commit()

    return success_response(po.to_dict(include_items=True), '采购订单创建成功')


@bp.route('/purchase-orders/<int:po_id>', methods=['GET'])
@login_required
def get_purchase_order(po_id):
    """获取采购订单详情"""
    po = PurchaseOrder.query.get_or_404(po_id)
    return success_response(po.to_dict(include_items=True))


@bp.route('/purchase-orders/<int:po_id>/confirm', methods=['PUT'])
@login_required
def confirm_purchase_order(po_id):
    """确认采购订单"""
    po = PurchaseOrder.query.get_or_404(po_id)

    if po.status != 'pending':
        return error_response('订单状态不允许此操作')

    po.status = 'confirmed'
    db.session.commit()

    return success_response(po.to_dict(), '订单已确认')


@bp.route('/purchase-orders/<int:po_id>/status', methods=['PUT'])
@login_required
def update_purchase_order_status(po_id):
    """更新采购订单状态"""
    po = PurchaseOrder.query.get_or_404(po_id)
    data = request.get_json()

    new_status = data.get('status') if data else None
    valid_transitions = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['shipped', 'cancelled'],
        'shipped': ['partial_received', 'completed'],
        'partial_received': ['completed'],
    }

    allowed = valid_transitions.get(po.status, [])
    if not new_status or new_status not in allowed:
        return error_response(f'状态不允许从 {po.status} 变更为 {new_status}')

    po.status = new_status
    db.session.commit()

    return success_response(po.to_dict(), '状态已更新')


# ==================== 采购到货验收 ====================

@bp.route('/purchase-receipts', methods=['GET'])
@login_required
def get_purchase_receipts():
    """获取验收记录列表"""
    po_id = request.args.get('po_id')
    query = PurchaseReceipt.query

    if po_id:
        query = query.filter_by(po_id=po_id)

    receipts = query.order_by(PurchaseReceipt.created_at.desc()).all()
    return success_response([r.to_dict() for r in receipts])


@bp.route('/purchase-receipts', methods=['POST'])
@login_required
def create_purchase_receipt():
    """创建验收记录，验收通过自动生成入库单"""
    data = request.get_json()

    if not data or not data.get('po_id'):
        return error_response('采购订单ID不能为空')

    po = PurchaseOrder.query.get_or_404(data['po_id'])

    if po.status not in ('confirmed', 'shipped', 'partial_received'):
        return error_response('订单状态不允许验收')

    # 如果没有传items，默认按订单明细验收
    items_data = data.get('items', [])
    if not items_data:
        # 简化：默认全部合格
        for item in po.items.all():
            items_data.append({
                'goods_id': item.goods_id,
                'ordered_qty': item.ordered_qty,
                'received_qty': item.ordered_qty,
                'quality_status': 'qualified',
                'quality_note': ''
            })

    total_received = 0
    for item_data in items_data:
        received_qty = int(item_data.get('received_qty', 0))
        total_received += received_qty

        receipt = PurchaseReceipt(
            po_id=po.id,
            received_qty=received_qty,
            quality_status=item_data.get('quality_status', 'qualified'),
            quality_note=item_data.get('quality_note', ''),
            receiver_id=current_user.id
        )
        db.session.add(receipt)

        # 更新订单明细已收货数量
        po_item = PurchaseOrderItem.query.filter_by(
            po_id=po.id, goods_id=item_data.get('goods_id')
        ).first()
        if po_item:
            po_item.received_qty = (po_item.received_qty or 0) + received_qty

    # 更新订单状态
    all_items = po.items.all()
    total_ordered = sum(i.ordered_qty for i in all_items)
    total_item_received = sum(i.received_qty or 0 for i in all_items)

    if total_item_received >= total_ordered:
        po.status = 'completed'
    else:
        po.status = 'partial_received'

    # 生成入库单
    warehouse_id = data.get('warehouse_id')
    if not warehouse_id:
        # 取第一个仓库
        from app.models.warehouse import Warehouse
        warehouse = Warehouse.query.filter_by(status='active').first()
        warehouse_id = warehouse.id if warehouse else None

    inbound_order = None
    if warehouse_id:
        inbound_order = InboundOrder(
            order_no=generate_inbound_no(),
            warehouse_id=warehouse_id,
            source_type='purchase',
            source_id=po.id,
            status='pending',
            total_items=len(items_data),
            operator_id=current_user.id,
            remark=f'采购订单 {po.po_no} 到货入库'
        )
        db.session.add(inbound_order)
        db.session.flush()

        for item_data in items_data:
            if item_data.get('quality_status') in ('qualified', 'partial'):
                inbound_item = InboundItem(
                    inbound_id=inbound_order.id,
                    goods_id=item_data.get('goods_id'),
                    planned_qty=int(item_data.get('received_qty', 0)),
                    actual_qty=None,
                    status='pending'
                )
                db.session.add(inbound_item)

        # 关联验收记录到入库单
        for receipt in PurchaseReceipt.query.filter_by(po_id=po.id).all():
            if not receipt.inbound_order_id:
                receipt.inbound_order_id = inbound_order.id

    db.session.commit()

    result = {
        'receipts_count': len(items_data),
        'order_status': po.status,
        'inbound_order': inbound_order.to_dict(include_items=True) if inbound_order else None
    }

    return success_response(result, '验收完成')
