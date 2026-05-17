from app import db
from .base import BaseModel
from app.utils.time_helper import beijing_now


class OutboundOrder(BaseModel):
    """出库单表"""
    __tablename__ = 'outbound_orders'

    order_no = db.Column(db.String(32), unique=True, nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    dest_type = db.Column(db.String(32), nullable=False)  # sale/transfer/scrap
    dest_id = db.Column(db.Integer)  # 目标客户/仓库ID
    status = db.Column(db.String(16), default='pending')
    # pending/picking/shipping/completed/cancelled
    total_items = db.Column(db.Integer, default=0)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    picked_at = db.Column(db.DateTime)
    shipped_at = db.Column(db.DateTime)
    remark = db.Column(db.String(512))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))

    # 关系
    warehouse = db.relationship('Warehouse', backref='outbound_orders')
    operator = db.relationship('User', foreign_keys=[operator_id], backref='outbound_orders')
    items = db.relationship('OutboundItem', backref='outbound_order', lazy='dynamic')

    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'order_no': self.order_no,
            'warehouse_id': self.warehouse_id,
            'warehouse_name': self.warehouse.name if self.warehouse else None,
            'dest_type': self.dest_type,
            'dest_id': self.dest_id,
            'status': self.status,
            'total_items': self.total_items,
            'operator_id': self.operator_id,
            'operator_name': self.operator.real_name if self.operator else None,
            'picked_at': self.picked_at.isoformat() if self.picked_at else None,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'remark': self.remark,
            'group_id': self.group_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_items:
            data['items'] = [item.to_dict() for item in self.items.all()]
        return data


class OutboundItem(BaseModel):
    """出库明细表"""
    __tablename__ = 'outbound_items'

    outbound_id = db.Column(db.Integer, db.ForeignKey('outbound_orders.id'), nullable=False)
    goods_id = db.Column(db.Integer, db.ForeignKey('goods.id'), nullable=False)
    requested_qty = db.Column(db.Integer, nullable=False)
    picked_qty = db.Column(db.Integer, default=0)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    batch_no = db.Column(db.String(64))
    status = db.Column(db.String(16), default='pending')  # pending/picked/shipped

    # 关系
    goods = db.relationship('Goods', backref='outbound_items')
    location = db.relationship('Location', backref='outbound_items')

    def to_dict(self):
        return {
            'id': self.id,
            'outbound_id': self.outbound_id,
            'goods_id': self.goods_id,
            'goods_name': self.goods.name if self.goods else None,
            'goods_sku': self.goods.sku if self.goods else None,
            'requested_qty': self.requested_qty,
            'picked_qty': self.picked_qty,
            'location_id': self.location_id,
            'loc_code': self.location.loc_code if self.location else None,
            'batch_no': self.batch_no,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Inventory(BaseModel):
    """库存记录表"""
    __tablename__ = 'inventory'

    goods_id = db.Column(db.Integer, db.ForeignKey('goods.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    batch_no = db.Column(db.String(64))
    production_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    quantity = db.Column(db.Integer, default=0)
    available_qty = db.Column(db.Integer, default=0)  # 可用数量
    reserved_qty = db.Column(db.Integer, default=0)  # 预留数量
    safety_stock = db.Column(db.Integer, default=0, comment='安全库存')
    min_stock = db.Column(db.Integer, default=0, comment='最小库存')
    status = db.Column(db.String(16), default='normal')  # normal/locked/expired

    # 关系
    goods = db.relationship('Goods', backref='inventory_records')
    warehouse = db.relationship('Warehouse', backref='inventory_records')
    location = db.relationship('Location', backref='inventory_records')

    def to_dict(self):
        return {
            'id': self.id,
            'goods_id': self.goods_id,
            'goods_name': self.goods.name if self.goods else None,
            'goods_sku': self.goods.sku if self.goods else None,
            'warehouse_id': self.warehouse_id,
            'warehouse_name': self.warehouse.name if self.warehouse else None,
            'location_id': self.location_id,
            'loc_code': self.location.loc_code if self.location else None,
            'batch_no': self.batch_no,
            'production_date': self.production_date.isoformat() if self.production_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'quantity': self.quantity,
            'available_qty': self.available_qty,
            'reserved_qty': self.reserved_qty,
            'safety_stock': self.safety_stock,
            'min_stock': self.min_stock,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StockMove(BaseModel):
    """库存移动记录表"""
    __tablename__ = 'stock_moves'

    goods_id = db.Column(db.Integer, db.ForeignKey('goods.id'), nullable=False)
    source_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    dest_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    move_type = db.Column(db.String(32), nullable=False)  # inbound/outbound/transfer/adjust
    reference_id = db.Column(db.Integer)  # 关联单据ID
    quantity = db.Column(db.Integer, nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    moved_at = db.Column(db.DateTime, default=beijing_now)
    remark = db.Column(db.String(256))

    # 关系
    goods = db.relationship('Goods', backref='stock_moves')
    source_location = db.relationship('Location', foreign_keys=[source_location_id], backref='moves_from')
    dest_location = db.relationship('Location', foreign_keys=[dest_location_id], backref='moves_to')
    operator = db.relationship('User', backref='stock_moves')

    def to_dict(self):
        return {
            'id': self.id,
            'goods_id': self.goods_id,
            'goods_name': self.goods.name if self.goods else None,
            'source_location_id': self.source_location_id,
            'source_loc_code': self.source_location.loc_code if self.source_location else None,
            'dest_location_id': self.dest_location_id,
            'dest_loc_code': self.dest_location.loc_code if self.dest_location else None,
            'move_type': self.move_type,
            'reference_id': self.reference_id,
            'quantity': self.quantity,
            'operator_id': self.operator_id,
            'operator_name': self.operator.real_name if self.operator else None,
            'moved_at': self.moved_at.isoformat() if self.moved_at else None,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class StockCount(BaseModel):
    """库存盘点单表"""
    __tablename__ = 'stock_counts'

    count_no = db.Column(db.String(32), unique=True, nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    count_type = db.Column(db.String(32), default='full')  # full/partial/cycle
    status = db.Column(db.String(16), default='draft')
    # draft/counting/reconciled/completed
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    counted_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    remark = db.Column(db.String(512))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))

    # 关系
    warehouse = db.relationship('Warehouse', backref='stock_counts')
    operator = db.relationship('User', foreign_keys=[operator_id], backref='stock_counts')
    items = db.relationship('StockCountItem', backref='stock_count', lazy='dynamic')

    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'count_no': self.count_no,
            'warehouse_id': self.warehouse_id,
            'warehouse_name': self.warehouse.name if self.warehouse else None,
            'count_type': self.count_type,
            'status': self.status,
            'operator_id': self.operator_id,
            'operator_name': self.operator.real_name if self.operator else None,
            'counted_at': self.counted_at.isoformat() if self.counted_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'remark': self.remark,
            'group_id': self.group_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_items:
            data['items'] = [item.to_dict() for item in self.items.all()]
        return data


class StockCountItem(BaseModel):
    """盘点明细表"""
    __tablename__ = 'stock_count_items'

    count_id = db.Column(db.Integer, db.ForeignKey('stock_counts.id'), nullable=False)
    goods_id = db.Column(db.Integer, db.ForeignKey('goods.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    batch_no = db.Column(db.String(64))
    book_qty = db.Column(db.Integer, default=0)  # 账面数量
    actual_qty = db.Column(db.Integer)  # 实盘数量
    variance = db.Column(db.Integer, default=0)  # 差异数量
    variance_reason = db.Column(db.String(256))
    status = db.Column(db.String(16), default='pending')  # pending/counted/reconciled

    # 关系
    goods = db.relationship('Goods', backref='stock_count_items')
    location = db.relationship('Location', backref='stock_count_items')

    def to_dict(self):
        return {
            'id': self.id,
            'count_id': self.count_id,
            'goods_id': self.goods_id,
            'goods_name': self.goods.name if self.goods else None,
            'goods_sku': self.goods.sku if self.goods else None,
            'location_id': self.location_id,
            'loc_code': self.location.loc_code if self.location else None,
            'batch_no': self.batch_no,
            'book_qty': self.book_qty,
            'actual_qty': self.actual_qty,
            'variance': self.variance,
            'variance_reason': self.variance_reason,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
