from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import OutboundOrder, OutboundItem, InboundOrder, InboundItem, Inventory, StockMove
from app.models import Warehouse, Zone, Location, Goods
from app.socket import broadcast_order_status
from app.api.logs import log_operation
from app.utils.scoring import score_operation

bp = Blueprint('warehouse', __name__)

import uuid
from app.utils.time_helper import beijing_now


def generate_order_no(prefix='OUT'):
    """生成单号"""
    return f"{prefix}{beijing_now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4().int)[:4]}"


# ==================== 入库单管理 ====================

@bp.route('/inbound', methods=['GET'])
@login_required
def get_inbound_orders():
    """获取入库单列表"""
    query = InboundOrder.query

    # 过滤条件
    status = request.args.get('status')
    warehouse_id = request.args.get('warehouse_id')
    if status:
        query = query.filter_by(status=status)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    orders = query.order_by(InboundOrder.created_at.desc()).all()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': [order.to_dict() for order in orders]
    })


@bp.route('/inbound/<int:id>', methods=['GET'])
@login_required
def get_inbound_order(id):
    """获取入库单详情"""
    order = InboundOrder.query.get_or_404(id)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': order.to_dict(include_items=True)
    })


@bp.route('/inbound', methods=['POST'])
@login_required
def create_inbound_order():
    """创建入库单"""
    data = request.get_json()

    order = InboundOrder(
        order_no=generate_order_no('INB'),
        warehouse_id=data.get('warehouse_id'),
        source_type=data.get('source_type', 'purchase'),
        source_id=data.get('source_id'),
        remark=data.get('remark', ''),
        group_id=data.get('group_id')
    )

    # 添加明细
    items_data = data.get('items', [])
    for item_data in items_data:
        item = InboundItem(
            goods_id=item_data.get('goods_id'),
            planned_qty=item_data.get('planned_qty'),
            batch_no=item_data.get('batch_no'),
            production_date=item_data.get('production_date'),
            expiry_date=item_data.get('expiry_date')
        )
        order.items.append(item)

    db.session.add(order)
    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='inbound_order',
        action='create',
        target_type='InboundOrder',
        target_id=order.id,
        description=f'创建入库单 {order.order_no}'
    )
    db.session.commit()

    # 评分
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='inbound_order', action='create')

    return jsonify({
        'code': 200,
        'message': '入库单创建成功',
        'data': order.to_dict()
    })


@bp.route('/inbound/<int:id>/shelve', methods=['POST'])
@login_required
def shelve_inbound(id):
    """入库上架（完成入库）"""
    order = InboundOrder.query.get_or_404(id)

    if order.status not in ['pending', 'inspecting']:
        return jsonify({'code': 400, 'message': '当前状态不允许上架'}), 400

    data = request.get_json()
    order.status = 'completed'
    order.operator_id = current_user.id
    order.completed_at = beijing_now()

    # 处理每个明细
    for item in order.items.all():
        item_data = next((i for i in data.get('items', []) if i['id'] == item.id), None)
        if item_data:
            item.actual_qty = item_data.get('actual_qty', item.planned_qty)
            item.location_id = item_data.get('location_id')
            item.status = 'completed'

            # 更新库存
            inventory = Inventory.query.filter_by(
                goods_id=item.goods_id,
                warehouse_id=order.warehouse_id,
                location_id=item.location_id,
                batch_no=item.batch_no
            ).first()

            if inventory:
                inventory.quantity += item.actual_qty
                inventory.available_qty += item.actual_qty
            else:
                inventory = Inventory(
                    goods_id=item.goods_id,
                    warehouse_id=order.warehouse_id,
                    location_id=item.location_id,
                    batch_no=item.batch_no,
                    production_date=item.production_date,
                    expiry_date=item.expiry_date,
                    quantity=item.actual_qty,
                    available_qty=item.actual_qty
                )
                db.session.add(inventory)

            # 记录库存移动
            stock_move = StockMove(
                goods_id=item.goods_id,
                dest_location_id=item.location_id,
                move_type='inbound',
                reference_id=order.id,
                quantity=item.actual_qty,
                operator_id=current_user.id
            )
            db.session.add(stock_move)

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='inbound_order',
        action='shelve',
        target_type='InboundOrder',
        target_id=order.id,
        description=f'完成入库上架 {order.order_no}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='inbound_order', action='shelve')
    broadcast_order_status('inbound_order', order.id, 'completed', current_user.group_id)

    return jsonify({
        'code': 200,
        'message': '上架完成',
        'data': order.to_dict()
    })


# ==================== 出库单管理 ====================

@bp.route('/outbound', methods=['GET'])
@login_required
def get_outbound_orders():
    """获取出库单列表"""
    query = OutboundOrder.query

    status = request.args.get('status')
    warehouse_id = request.args.get('warehouse_id')
    if status:
        query = query.filter_by(status=status)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    orders = query.order_by(OutboundOrder.created_at.desc()).all()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': [order.to_dict() for order in orders]
    })


@bp.route('/outbound/<int:id>', methods=['GET'])
@login_required
def get_outbound_order(id):
    """获取出库单详情"""
    order = OutboundOrder.query.get_or_404(id)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': order.to_dict(include_items=True)
    })


@bp.route('/outbound', methods=['POST'])
@login_required
def create_outbound_order():
    """创建出库单"""
    data = request.get_json()

    order = OutboundOrder(
        order_no=generate_order_no('OUT'),
        warehouse_id=data.get('warehouse_id'),
        dest_type=data.get('dest_type', 'sale'),
        dest_id=data.get('dest_id'),
        remark=data.get('remark', ''),
        group_id=data.get('group_id')
    )

    # 添加明细
    items_data = data.get('items', [])
    for item_data in items_data:
        item = OutboundItem(
            goods_id=item_data.get('goods_id'),
            requested_qty=item_data.get('requested_qty'),
            batch_no=item_data.get('batch_no')
        )
        order.items.append(item)

    db.session.add(order)
    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='outbound_order',
        action='create',
        target_type='OutboundOrder',
        target_id=order.id,
        description=f'创建出库单 {order.order_no}'
    )
    db.session.commit()

    # 评分
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='outbound_order', action='create')

    return jsonify({
        'code': 200,
        'message': '出库单创建成功',
        'data': order.to_dict()
    })


@bp.route('/outbound/<int:id>/pick', methods=['POST'])
@login_required
def pick_outbound(id):
    """出库拣货"""
    order = OutboundOrder.query.get_or_404(id)

    if order.status != 'pending':
        return jsonify({'code': 400, 'message': '当前状态不允许拣货'}), 400

    data = request.get_json()
    order.status = 'picking'
    order.operator_id = current_user.id
    order.picked_at = beijing_now()

    # 处理每个明细
    for item in order.items.all():
        item_data = next((i for i in data.get('items', []) if i['id'] == item.id), None)
        if item_data:
            item.picked_qty = item_data.get('picked_qty', item.requested_qty)
            item.location_id = item_data.get('location_id')
            item.batch_no = item_data.get('batch_no')
            item.status = 'picked'

            # 检查并更新库存
            inventory = Inventory.query.filter_by(
                goods_id=item.goods_id,
                warehouse_id=order.warehouse_id,
                location_id=item.location_id,
                batch_no=item.batch_no
            ).first()

            if not inventory or inventory.available_qty < item.picked_qty:
                return jsonify({
                    'code': 400,
                    'message': f'商品 {item.goods.name if item.goods else ""} 库存不足'
                }), 400

            inventory.quantity -= item.picked_qty
            inventory.available_qty -= item.picked_qty

            # 记录库存移动
            stock_move = StockMove(
                goods_id=item.goods_id,
                source_location_id=item.location_id,
                move_type='outbound',
                reference_id=order.id,
                quantity=item.picked_qty,
                operator_id=current_user.id
            )
            db.session.add(stock_move)

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='outbound_order',
        action='pick',
        target_type='OutboundOrder',
        target_id=order.id,
        description=f'完成出库拣货 {order.order_no}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='outbound_order', action='pick')
    broadcast_order_status('outbound_order', order.id, 'picking', current_user.group_id)

    return jsonify({
        'code': 200,
        'message': '拣货完成',
        'data': order.to_dict()
    })


@bp.route('/outbound/<int:id>/ship', methods=['POST'])
@login_required
def ship_outbound(id):
    """出库发货"""
    order = OutboundOrder.query.get_or_404(id)

    if order.status != 'picking':
        return jsonify({'code': 400, 'message': '请先完成拣货'}), 400

    order.status = 'completed'
    order.shipped_at = beijing_now()

    # 更新明细状态
    for item in order.items.all():
        item.status = 'shipped'

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='outbound_order',
        action='ship',
        target_type='OutboundOrder',
        target_id=order.id,
        description=f'完成出库发货 {order.order_no}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='outbound_order', action='ship')
    broadcast_order_status('outbound_order', order.id, 'completed', current_user.group_id)

    return jsonify({
        'code': 200,
        'message': '发货完成',
        'data': order.to_dict()
    })
