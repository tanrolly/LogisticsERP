from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Inventory, StockMove, StockCount, StockCountItem, Goods, Warehouse, Location
from app.socket import broadcast_order_status
from app.api.logs import log_operation
from app.utils.scoring import score_operation

bp = Blueprint('inventory', __name__)

import uuid
from app.utils.time_helper import beijing_now


def generate_count_no():
    """生成盘点单号"""
    return f"COUNT{beijing_now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4().int)[:4]}"


# ==================== 库存查询 ====================

@bp.route('/inventory', methods=['GET'])
@login_required
def get_inventory():
    """获取库存列表"""
    query = Inventory.query

    # 过滤条件
    goods_id = request.args.get('goods_id')
    warehouse_id = request.args.get('warehouse_id')
    location_id = request.args.get('location_id')
    status = request.args.get('status')

    if goods_id:
        query = query.filter_by(goods_id=goods_id)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)
    if location_id:
        query = query.filter_by(location_id=location_id)
    if status:
        query = query.filter_by(status=status)

    inventory = query.all()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': [inv.to_dict() for inv in inventory]
    })


@bp.route('/inventory/<int:id>', methods=['GET'])
@login_required
def get_inventory_item(id):
    """获取库存详情"""
    inventory = Inventory.query.get_or_404(id)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': inventory.to_dict()
    })


@bp.route('/inventory/summary', methods=['GET'])
@login_required
def get_inventory_summary():
    """库存汇总统计"""
    warehouse_id = request.args.get('warehouse_id')

    query = Inventory.query
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    inventory = query.all()

    # 统计
    total_skus = len(set(inv.goods_id for inv in inventory))
    total_qty = sum(inv.quantity for inv in inventory)
    total_locations = len(set(inv.location_id for inv in inventory if inv.location_id))

    # 按仓库分组
    by_warehouse = {}
    for inv in inventory:
        wid = inv.warehouse_id
        if wid not in by_warehouse:
            by_warehouse[wid] = {
                'warehouse_name': inv.warehouse.name if inv.warehouse else '',
                'sku_count': 0,
                'total_qty': 0
            }
        by_warehouse[wid]['sku_count'] += 1
        by_warehouse[wid]['total_qty'] += inv.quantity

    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'total_skus': total_skus,
            'total_qty': total_qty,
            'total_locations': total_locations,
            'by_warehouse': list(by_warehouse.values())
        }
    })


# ==================== 库存移动记录 ====================

@bp.route('/stock-moves', methods=['GET'])
@login_required
def get_stock_moves():
    """获取库存移动记录"""
    query = StockMove.query

    goods_id = request.args.get('goods_id')
    move_type = request.args.get('move_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if goods_id:
        query = query.filter_by(goods_id=goods_id)
    if move_type:
        query = query.filter_by(move_type=move_type)
    if start_date:
        query = query.filter(StockMove.moved_at >= start_date)
    if end_date:
        query = query.filter(StockMove.moved_at <= end_date)

    moves = query.order_by(StockMove.moved_at.desc()).limit(500).all()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': [move.to_dict() for move in moves]
    })


# ==================== 库存盘点 ====================

@bp.route('/stock-counts', methods=['GET'])
@login_required
def get_stock_counts():
    """获取盘点单列表"""
    query = StockCount.query

    status = request.args.get('status')
    warehouse_id = request.args.get('warehouse_id')

    if status:
        query = query.filter_by(status=status)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    counts = query.order_by(StockCount.created_at.desc()).all()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': [c.to_dict() for c in counts]
    })


@bp.route('/stock-counts/<int:id>', methods=['GET'])
@login_required
def get_stock_count(id):
    """获取盘点单详情"""
    count = StockCount.query.get_or_404(id)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': count.to_dict(include_items=True)
    })


@bp.route('/stock-counts', methods=['POST'])
@login_required
def create_stock_count():
    """创建盘点单"""
    data = request.get_json()

    count = StockCount(
        count_no=generate_count_no(),
        warehouse_id=data.get('warehouse_id'),
        count_type=data.get('count_type', 'full'),
        operator_id=current_user.id,
        remark=data.get('remark', '')
    )

    db.session.add(count)
    db.session.flush()  # 获取count.id

    # 生成盘点明细（基于当前库存）
    inventory_query = Inventory.query.filter_by(warehouse_id=count.warehouse_id)

    if count.count_type == 'partial' and data.get('location_ids'):
        # 部分盘点（指定货位）
        inventory_query = inventory_query.filter(Inventory.location_id.in_(data.get('location_ids')))

    for inv in inventory_query.all():
        item = StockCountItem(
            count_id=count.id,
            goods_id=inv.goods_id,
            location_id=inv.location_id,
            batch_no=inv.batch_no,
            book_qty=inv.quantity
        )
        db.session.add(item)

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='stock_count',
        action='create',
        target_type='StockCount',
        target_id=count.id,
        description=f'创建盘点单 {count.count_no}（{count.count_type}盘点）'
    )
    db.session.commit()

    # 评分
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='stock_count', action='create')

    return jsonify({
        'code': 200,
        'message': '盘点单创建成功',
        'data': count.to_dict(include_items=True)
    })


@bp.route('/stock-counts/<int:id>/count', methods=['POST'])
@login_required
def perform_count(id):
    """执行盘点（录入实盘数量）"""
    count = StockCount.query.get_or_404(id)

    if count.status != 'draft':
        return jsonify({'code': 400, 'message': '盘点单状态不正确'}), 400

    count.status = 'counting'
    count.counted_at = beijing_now()

    data = request.get_json()
    items_data = data.get('items', [])

    for item in count.items.all():
        item_data = next((i for i in items_data if i['id'] == item.id), None)
        if item_data:
            item.actual_qty = item_data.get('actual_qty', 0)
            item.variance = item.actual_qty - item.book_qty
            item.status = 'counted'

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='stock_count',
        action='count',
        target_type='StockCount',
        target_id=count.id,
        description=f'执行盘点 {count.count_no}'
    )
    db.session.commit()

    # 评分
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='stock_count', action='count')

    return jsonify({
        'code': 200,
        'message': '盘点完成',
        'data': count.to_dict(include_items=True)
    })


@bp.route('/stock-counts/<int:id>/reconcile', methods=['POST'])
@login_required
def reconcile_count(id):
    """盘点 reconciliation（调整库存差异）"""
    count = StockCount.query.get_or_404(id)

    if count.status != 'counting':
        return jsonify({'code': 400, 'message': '请先完成盘点'}), 400

    count.status = 'completed'
    count.completed_at = beijing_now()

    # 调整库存差异
    for item in count.items.all():
        if item.variance != 0:
            # 查找对应库存记录
            inventory = Inventory.query.filter_by(
                goods_id=item.goods_id,
                warehouse_id=count.warehouse_id,
                location_id=item.location_id,
                batch_no=item.batch_no
            ).first()

            if inventory:
                inventory.quantity = item.actual_qty
                inventory.available_qty = item.actual_qty

        item.status = 'reconciled'

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='stock_count',
        action='reconcile',
        target_type='StockCount',
        target_id=count.id,
        description=f'盘点调整完成 {count.count_no}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='stock_count', action='reconcile')
    broadcast_order_status('stock_count', count.id, 'completed', current_user.group_id)

    return jsonify({
        'code': 200,
        'message': '盘点调整完成',
        'data': count.to_dict(include_items=True)
    })


# ==================== 库存预警 ====================

@bp.route('/inventory/alerts', methods=['GET'])
@login_required
def get_inventory_alerts():
    """获取库存预警（过期、低库存等）"""
    alerts = {
        'expiring': [],  # 即将过期
        'expired': [],   # 已过期
        'low_stock': []  # 低库存
    }

    # 检查过期商品（30天内过期）
    from datetime import timedelta
    thirty_days_later = beijing_now().date() + timedelta(days=30)

    inventory = Inventory.query.filter(
        Inventory.expiry_date.isnot(None),
        Inventory.quantity > 0
    ).all()

    for inv in inventory:
        if inv.expiry_date < beijing_now().date():
            alerts['expired'].append(inv.to_dict())
        elif inv.expiry_date <= thirty_days_later:
            alerts['expiring'].append(inv.to_dict())

    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': alerts
    })
