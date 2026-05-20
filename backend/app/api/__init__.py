from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.goods import Goods, Category
from app.models.warehouse import Warehouse, Zone, Location
from app.models.role import Role
from app.utils.permissions import admin_required

bp = Blueprint('api', __name__)


def success_response(data=None, message='success'):
    """统一成功响应格式"""
    return jsonify({'code': 200, 'message': message, 'data': data}), 200


def error_response(message, code=400):
    """统一错误响应格式"""
    return jsonify({'code': code, 'message': message, 'data': None}), 200


# ==================== 供应商管理 ====================

@bp.route('/suppliers', methods=['GET'])
@login_required
def get_suppliers():
    """获取供应商列表"""
    suppliers = Supplier.query.filter_by(status='active').all()
    return success_response([s.to_dict() for s in suppliers])


@bp.route('/suppliers', methods=['POST'])
@login_required
def create_supplier():
    """创建供应商"""
    data = request.get_json()

    if not data or not data.get('name'):
        return error_response('供应商名称不能为空')

    supplier = Supplier(
        name=data['name'],
        contact=data.get('contact'),
        phone=data.get('phone'),
        address=data.get('address')
    )

    db.session.add(supplier)
    db.session.commit()

    return success_response(supplier.to_dict(), '创建成功')


@bp.route('/suppliers/<int:supplier_id>', methods=['GET'])
@login_required
def get_supplier(supplier_id):
    """获取供应商详情"""
    supplier = Supplier.query.get_or_404(supplier_id)
    return success_response(supplier.to_dict())


@bp.route('/suppliers/<int:supplier_id>', methods=['PUT'])
@login_required
def update_supplier(supplier_id):
    """更新供应商"""
    supplier = Supplier.query.get_or_404(supplier_id)
    data = request.get_json()

    if data.get('name'):
        supplier.name = data['name']
    if data.get('contact') is not None:
        supplier.contact = data['contact']
    if data.get('phone') is not None:
        supplier.phone = data['phone']
    if data.get('address') is not None:
        supplier.address = data['address']

    db.session.commit()
    return success_response(supplier.to_dict(), '更新成功')


@bp.route('/suppliers/<int:supplier_id>', methods=['DELETE'])
@admin_required
@login_required
def delete_supplier(supplier_id):
    """删除供应商（软删除）"""
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier.status = 'inactive'
    db.session.commit()
    return success_response(None, '删除成功')


# ==================== 客户管理 ====================

# @bp.route('/customers', methods=['GET'])
# @login_required
# def get_customers():
#     """获取客户列表"""
#     customers = Customer.query.filter_by(status='active').all()
#     return success_response([c.to_dict() for c in customers])


# @bp.route('/customers', methods=['POST'])
# @login_required
# def create_customer():
#     """创建客户"""
#     data = request.get_json()

#     if not data or not data.get('name'):
#         return error_response('客户名称不能为空')

#     customer = Customer(
#         name=data['name'],
#         contact=data.get('contact'),
#         phone=data.get('phone'),
#         address=data.get('address'),
#         credit_level=data.get('credit_level', 'normal')
#     )

#     db.session.add(customer)
#     db.session.commit()

#     return success_response(customer.to_dict(), '创建成功')


# @bp.route('/customers/<int:customer_id>', methods=['GET'])
# @login_required
# def get_customer(customer_id):
#     """获取客户详情"""
#     customer = Customer.query.get_or_404(customer_id)
#     return success_response(customer.to_dict())


# @bp.route('/customers/<int:customer_id>', methods=['PUT'])
# @login_required
# def update_customer(customer_id):
#     """更新客户"""
#     customer = Customer.query.get_or_404(customer_id)
#     data = request.get_json()

#     if data.get('name'):
#         customer.name = data['name']
#     if data.get('contact') is not None:
#         customer.contact = data['contact']
#     if data.get('phone') is not None:
#         customer.phone = data['phone']
#     if data.get('address') is not None:
#         customer.address = data['address']
#     if data.get('credit_level'):
#         customer.credit_level = data['credit_level']

#     db.session.commit()
#     return success_response(customer.to_dict(), '更新成功')


# @bp.route('/customers/<int:customer_id>', methods=['DELETE'])
# @admin_required
# @login_required
# def delete_customer(customer_id):
#     """删除客户（软删除）"""
#     customer = Customer.query.get_or_404(customer_id)
#     customer.status = 'inactive'
#     db.session.commit()
#     return success_response(None, '删除成功')


# ==================== 车辆管理 ====================

@bp.route('/vehicles', methods=['GET'])
@login_required
def get_vehicles():
    """获取车辆列表"""
    status = request.args.get('status')
    query = Vehicle.query
    if status:
        query = query.filter_by(status=status)
    vehicles = query.all()
    return success_response([v.to_dict() for v in vehicles])


@bp.route('/vehicles', methods=['POST'])
@login_required
def create_vehicle():
    """创建车辆"""
    data = request.get_json()

    if not data or not data.get('plate_no') or not data.get('type'):
        return error_response('车牌号和车型不能为空')

    vehicle = Vehicle(
        plate_no=data['plate_no'],
        type=data['type'],
        capacity_weight=data.get('capacity_weight'),
        capacity_volume=data.get('capacity_volume'),
        status=data.get('status', 'idle')
    )

    db.session.add(vehicle)
    db.session.commit()

    return success_response(vehicle.to_dict(), '创建成功')


@bp.route('/vehicles/<int:vehicle_id>', methods=['GET'])
@login_required
def get_vehicle(vehicle_id):
    """获取车辆详情"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    return success_response(vehicle.to_dict())


@bp.route('/vehicles/<int:vehicle_id>', methods=['PUT'])
@login_required
def update_vehicle(vehicle_id):
    """更新车辆"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json()

    if data.get('plate_no'):
        vehicle.plate_no = data['plate_no']
    if data.get('type'):
        vehicle.type = data['type']
    if data.get('capacity_weight') is not None:
        vehicle.capacity_weight = data['capacity_weight']
    if data.get('capacity_volume') is not None:
        vehicle.capacity_volume = data['capacity_volume']
    if data.get('status'):
        vehicle.status = data['status']

    db.session.commit()
    return success_response(vehicle.to_dict(), '更新成功')


@bp.route('/vehicles/<int:vehicle_id>', methods=['DELETE'])
@admin_required
@login_required
def delete_vehicle(vehicle_id):
    """删除车辆（软删除）"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    vehicle.status = 'retired'
    db.session.commit()
    return success_response(None, '删除成功')


# ==================== 司机管理 ====================

@bp.route('/drivers', methods=['GET'])
@login_required
def get_drivers():
    """获取司机列表"""
    status = request.args.get('status')
    query = Driver.query
    if status:
        query = query.filter_by(status=status)
    drivers = query.all()
    return success_response([d.to_dict() for d in drivers])


@bp.route('/drivers', methods=['POST'])
@login_required
def create_driver():
    """创建司机"""
    data = request.get_json()

    if not data or not data.get('name'):
        return error_response('司机姓名不能为空')

    driver = Driver(
        name=data['name'],
        phone=data.get('phone'),
        license_no=data.get('license_no'),
        license_type=data.get('license_type'),
        status=data.get('status', 'available')
    )

    db.session.add(driver)
    db.session.commit()

    return success_response(driver.to_dict(), '创建成功')


@bp.route('/drivers/<int:driver_id>', methods=['GET'])
@login_required
def get_driver(driver_id):
    """获取司机详情"""
    driver = Driver.query.get_or_404(driver_id)
    return success_response(driver.to_dict())


@bp.route('/drivers/<int:driver_id>', methods=['PUT'])
@login_required
def update_driver(driver_id):
    """更新司机"""
    driver = Driver.query.get_or_404(driver_id)
    data = request.get_json()

    if data.get('name'):
        driver.name = data['name']
    if data.get('phone') is not None:
        driver.phone = data['phone']
    if data.get('license_no') is not None:
        driver.license_no = data['license_no']
    if data.get('license_type') is not None:
        driver.license_type = data['license_type']
    if data.get('status'):
        driver.status = data['status']

    db.session.commit()
    return success_response(driver.to_dict(), '更新成功')


@bp.route('/drivers/<int:driver_id>', methods=['DELETE'])
@admin_required
@login_required
def delete_driver(driver_id):
    """删除司机（软删除）"""
    driver = Driver.query.get_or_404(driver_id)
    driver.status = 'dismissed'
    db.session.commit()
    return success_response(None, '删除成功')


# ==================== 商品管理 ====================

@bp.route('/goods', methods=['GET'])
@login_required
def get_goods():
    """获取商品列表"""
    goods = Goods.query.filter_by(status='active').all()
    return success_response([g.to_dict() for g in goods])


@bp.route('/goods', methods=['POST'])
@login_required
def create_goods():
    """创建商品"""
    data = request.get_json()

    if not data or not data.get('sku') or not data.get('name'):
        return error_response('SKU和商品名称不能为空')

    goods = Goods(
        sku=data['sku'],
        name=data['name'],
        spec=data.get('spec'),
        unit=data.get('unit', '个'),
        category_id=data.get('category_id'),
        min_stock=data.get('min_stock', 0),
        max_stock=data.get('max_stock', 99999),
        purchase_price=data.get('purchase_price'),
        selling_price=data.get('selling_price')
    )

    db.session.add(goods)
    db.session.commit()

    return success_response(goods.to_dict(), '创建成功')


@bp.route('/goods/<int:goods_id>', methods=['GET'])
@login_required
def get_goods_detail(goods_id):
    """获取商品详情"""
    goods = Goods.query.get_or_404(goods_id)
    return success_response(goods.to_dict())


@bp.route('/goods/<int:goods_id>', methods=['PUT'])
@login_required
def update_goods(goods_id):
    """更新商品"""
    goods = Goods.query.get_or_404(goods_id)
    data = request.get_json()

    if data.get('sku'):
        goods.sku = data['sku']
    if data.get('name'):
        goods.name = data['name']
    if data.get('spec') is not None:
        goods.spec = data['spec']
    if data.get('unit'):
        goods.unit = data['unit']
    if data.get('category_id') is not None:
        goods.category_id = data['category_id']
    if data.get('min_stock') is not None:
        goods.min_stock = data['min_stock']
    if data.get('max_stock') is not None:
        goods.max_stock = data['max_stock']
    if data.get('purchase_price') is not None:
        goods.purchase_price = data['purchase_price']
    if data.get('selling_price') is not None:
        goods.selling_price = data['selling_price']

    db.session.commit()
    return success_response(goods.to_dict(), '更新成功')


@bp.route('/goods/<int:goods_id>', methods=['DELETE'])
@admin_required
@login_required
def delete_goods(goods_id):
    """删除商品（软删除）"""
    goods = Goods.query.get_or_404(goods_id)
    goods.status = 'inactive'
    db.session.commit()
    return success_response(None, '删除成功')


# ==================== 仓库管理 ====================

@bp.route('/warehouses', methods=['GET'])
@login_required
def get_warehouses():
    """获取仓库列表"""
    warehouses = Warehouse.query.filter_by(status='active').all()
    return success_response([w.to_dict() for w in warehouses])


@bp.route('/warehouses', methods=['POST'])
@login_required
def create_warehouse():
    """创建仓库"""
    data = request.get_json()

    if not data or not data.get('name'):
        return error_response('仓库名称不能为空')

    warehouse = Warehouse(
        name=data['name'],
        address=data.get('address'),
        type=data.get('type', 'normal')
    )

    db.session.add(warehouse)
    db.session.commit()

    return success_response(warehouse.to_dict(), '创建成功')


@bp.route('/warehouses/<int:warehouse_id>', methods=['PUT'])
@login_required
def update_warehouse(warehouse_id):
    """更新仓库"""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    data = request.get_json()

    if data.get('name'):
        warehouse.name = data['name']
    if data.get('address') is not None:
        warehouse.address = data['address']
    if data.get('type'):
        warehouse.type = data['type']

    db.session.commit()
    return success_response(warehouse.to_dict(), '更新成功')


@bp.route('/warehouses/<int:warehouse_id>', methods=['DELETE'])
@admin_required
@login_required
def delete_warehouse(warehouse_id):
    """删除仓库（软删除）"""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    # 检查是否有关联库区
    zone_count = Zone.query.filter_by(warehouse_id=warehouse_id).count()
    if zone_count > 0:
        return error_response('该仓库下有库区，无法删除')
    warehouse.status = 'inactive'
    db.session.commit()
    return success_response(None, '删除成功')


@bp.route('/warehouses/<int:warehouse_id>/zones', methods=['GET'])
@login_required
def get_zones(warehouse_id):
    """获取某仓库的库区列表"""
    zones = Zone.query.filter_by(warehouse_id=warehouse_id).all()
    return success_response([z.to_dict() for z in zones])


@bp.route('/zones', methods=['POST'])
@login_required
def create_zone():
    """创建库区"""
    data = request.get_json()

    if not data or not data.get('warehouse_id') or not data.get('zone_code') or not data.get('zone_name'):
        return error_response('仓库ID、库区编码和名称不能为空')

    zone = Zone(
        warehouse_id=data['warehouse_id'],
        zone_code=data['zone_code'],
        zone_name=data['zone_name'],
        sort_order=data.get('sort_order', 0)
    )

    db.session.add(zone)
    db.session.commit()

    return success_response(zone.to_dict(), '创建成功')


@bp.route('/zones/<int:zone_id>', methods=['PUT'])
@login_required
def update_zone(zone_id):
    """更新库区"""
    zone = Zone.query.get_or_404(zone_id)
    data = request.get_json()

    if data.get('zone_code'):
        zone.zone_code = data['zone_code']
    if data.get('zone_name'):
        zone.zone_name = data['zone_name']
    if data.get('sort_order') is not None:
        zone.sort_order = data['sort_order']

    db.session.commit()
    return success_response(zone.to_dict(), '更新成功')


@bp.route('/zones/<int:zone_id>', methods=['DELETE'])
@admin_required
@login_required
def delete_zone(zone_id):
    """删除库区"""
    zone = Zone.query.get_or_404(zone_id)
    # 检查是否有关联货位
    loc_count = Location.query.filter_by(zone_id=zone_id).count()
    if loc_count > 0:
        return error_response('该库区下有货位，无法删除')
    db.session.delete(zone)
    # 更新仓库总货位数
    warehouse = Warehouse.query.get(zone.warehouse_id)
    if warehouse:
        warehouse.total_locations = Location.query.join(Zone).filter(
            Zone.warehouse_id == warehouse.id
        ).count()
    db.session.commit()
    return success_response(None, '删除成功')


@bp.route('/zones/<int:zone_id>/locations', methods=['GET'])
@login_required
def get_locations(zone_id):
    """获取某库区的货位列表"""
    locations = Location.query.filter_by(zone_id=zone_id).all()
    return success_response([l.to_dict() for l in locations])


@bp.route('/locations', methods=['POST'])
@login_required
def create_location():
    """创建货位"""
    data = request.get_json()

    if not data or not data.get('zone_id') or not data.get('loc_code'):
        return error_response('库区ID和货位编码不能为空')

    location = Location(
        zone_id=data['zone_id'],
        loc_code=data['loc_code'],
        capacity_weight=data.get('capacity_weight'),
        capacity_volume=data.get('capacity_volume'),
        status=data.get('status', 'empty')
    )

    db.session.add(location)
    db.session.commit()

    # 更新仓库总货位数
    zone = Zone.query.get(data['zone_id'])
    if zone:
        warehouse = Warehouse.query.get(zone.warehouse_id)
        if warehouse:
            warehouse.total_locations = Location.query.join(Zone).filter(
                Zone.warehouse_id == warehouse.id
            ).count()
            db.session.commit()

    return success_response(location.to_dict(), '创建成功')


@bp.route('/locations/<int:location_id>', methods=['PUT'])
@login_required
def update_location(location_id):
    """更新货位"""
    location = Location.query.get_or_404(location_id)
    data = request.get_json()

    if data.get('loc_code'):
        location.loc_code = data['loc_code']
    if data.get('capacity_weight') is not None:
        location.capacity_weight = data['capacity_weight']
    if data.get('capacity_volume') is not None:
        location.capacity_volume = data['capacity_volume']
    if data.get('status'):
        location.status = data['status']

    db.session.commit()
    return success_response(location.to_dict(), '更新成功')


@bp.route('/locations/<int:location_id>', methods=['DELETE'])
@admin_required
@login_required
def delete_location(location_id):
    """删除货位"""
    location = Location.query.get_or_404(location_id)
    if location.status == 'occupied':
        return error_response('该货位已被占用，无法删除')
    zone_id = location.zone_id
    db.session.delete(location)
    # 更新仓库总货位数
    zone = Zone.query.get(zone_id)
    if zone:
        warehouse = Warehouse.query.get(zone.warehouse_id)
        if warehouse:
            warehouse.total_locations = Location.query.join(Zone).filter(
                Zone.warehouse_id == warehouse.id
            ).count()
    db.session.commit()
    return success_response(None, '删除成功')


# ==================== 角色管理 ====================

@bp.route('/roles', methods=['GET'])
@login_required
def get_roles():
    """获取角色列表"""
    roles = Role.query.all()
    return success_response([r.to_dict() for r in roles])
