"""Flask 应用工厂函数"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from app.config import Config

# 初始化扩展（不绑定具体app）
db = SQLAlchemy()
login_manager = LoginManager()

# 导入 SocketIO 实例（在 extensions.py 中创建）
from app.extensions import socketio


def create_app(config_class=Config):
    """Flask 应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    CORS(app, supports_credentials=True, origins=['http://localhost:5173'])

    # 初始化 SocketIO（必须在 app 创建后）
    socketio.init_app(app, cors_allowed_origins='*')

    # 注册蓝图
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.api.purchase import bp as purchase_bp
    app.register_blueprint(purchase_bp, url_prefix='/api')

    from app.api.transport import bp as transport_bp
    app.register_blueprint(transport_bp, url_prefix='/api')

    from app.api.warehouse import bp as warehouse_bp
    app.register_blueprint(warehouse_bp, url_prefix='/api')

    from app.api.inventory import bp as inventory_bp
    app.register_blueprint(inventory_bp, url_prefix='/api')

    from app.api.collab import bp as collab_bp
    app.register_blueprint(collab_bp, url_prefix='/api')

    from app.api.teaching import bp as teaching_bp
    app.register_blueprint(teaching_bp, url_prefix='/api')

    from app.api.logs import bp as logs_bp
    app.register_blueprint(logs_bp, url_prefix='/api')

    from app.api.scores import bp as scores_bp
    app.register_blueprint(scores_bp, url_prefix='/api')

    from app.api.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/api')

    from app.api.export import bp as export_bp
    app.register_blueprint(export_bp, url_prefix='/api')

    from app.api.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/api')

    from app.api.finance import bp as finance_bp
    app.register_blueprint(finance_bp, url_prefix='/api')

    from app.api.contracts import bp as contracts_bp
    app.register_blueprint(contracts_bp)

    from app.api.customers import bp as customers_bp
    app.register_blueprint(customers_bp, url_prefix='/api')

    from app.api.alerts import bp as alerts_bp
    app.register_blueprint(alerts_bp, url_prefix='/api')

    from app.api.users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix='/api')

    from app.api.approval import bp as approval_bp
    app.register_blueprint(approval_bp, url_prefix='/api')

    # 启动时自动初始化预设教学场景（若不存在）
    try:
        from app.api.teaching import init_preset_scenes
        with app.app_context():
            init_preset_scenes()
    except Exception:
        pass  # 表尚未创建时静默跳过

    # 注册 socket 事件处理
    from app.socket import init_socket
    init_socket(socketio)

    # ✅ 启动时自动建表 + 初始化种子数据（首次启动零配置）
    with app.app_context():
        db.create_all()
        _auto_seed()

    # 健康检查接口
    @app.route('/api/health')
    def health():
        return {'code': 200, 'message': 'ok', 'data': {'version': '2.0.0'}}

    return app


def _auto_seed():
    """首次启动自动初始化种子数据（幂等，不重复创建）"""
    from app.models.user import User
    from app.models.role import Role
    # 已有用户则跳过
    if User.query.count() > 0:
        return

    print("\n🌱 首次启动，自动初始化基础数据...")

    from decimal import Decimal
    from app.models.supplier import Supplier
    from app.models.customer import Customer
    from app.models.vehicle import Vehicle
    from app.models.driver import Driver
    from app.models.goods import Category, Goods
    from app.models.warehouse import Warehouse, Zone, Location

    # ===== 角色 =====
    roles_data = [
        ('admin', '系统管理员', '管理系统的所有功能和数据'),
        ('teacher', '教师', '创建教学场景、监控学生进度、评分'),
        ('student', '学生', '参与学习任务的学生'),
        ('purchaser', '采购专员', '负责采购申请和供应商管理'),
        ('customer_service', '客服', '负责接单和客户沟通'),
        ('dispatcher', '调度员', '负责车辆调度和路线规划'),
        ('warehouse_keeper', '仓库管理员', '负责出入库和库存管理'),
        ('driver', '司机', '负责运输执行'),
    ]
    for code, name, desc in roles_data:
        if not Role.query.filter_by(code=code).first():
            db.session.add(Role(code=code, name=name, description=desc))
    db.session.commit()

    # ===== 用户 =====
    role_map = {r.code: r for r in Role.query.all()}
    users_data = [
        ('admin',         '系统管理员',   'admin',         'admin123'),
        ('teacher01',     '张老师',        'teacher',       '123456'),
        ('student01',     '学生甲',        'student',       '123456'),
        ('student02',     '学生乙',        'student',       '123456'),
        ('purchaser01',   '采购员小李',    'purchaser',     '123456'),
        ('cs01',          '客服小王',      'customer_service', '123456'),
        ('dispatcher01',  '调度员老赵',    'dispatcher',    '123456'),
        ('keeper01',      '仓管员小陈',    'warehouse_keeper', '123456'),
        ('driver01',      '司机小刘',      'driver',        '123456'),
    ]
    for username, real_name, role_code, pwd in users_data:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, real_name=real_name,
                     role_id=role_map[role_code].id, status='active')
            u.password = pwd
            db.session.add(u)
    db.session.commit()

    # ===== 供应商 =====
    suppliers_data = [
        ('华东供应链有限公司', '李经理', '021-5555-1001', '上海市浦东新区供应链路88号', '4.5'),
        ('南方物流科技有限公司', '王总监', '020-5555-2002', '广州市天河区科技园99号', '4.8'),
        ('北方商贸集团', '赵部长', '010-5555-3003', '北京市朝阳区商贸大厦12层', '4.2'),
        ('中原材料供应商', '孙经理', '0371-5555-4004', '郑州市高新区材料城A区', '4.0'),
        ('西部仓储物流中心', '周主任', '028-5555-5005', '成都市青白江区物流港6号', '4.6'),
    ]
    for name, contact, phone, address, rating in suppliers_data:
        if not Supplier.query.filter_by(name=name).first():
            db.session.add(Supplier(name=name, contact=contact, phone=phone,
                                    address=address, rating=Decimal(rating)))
    db.session.commit()

    # ===== 客户 =====
    customers_data = [
        ('CUS-20260101001', '优品零售集团', '陈经理', '021-8888-1001', '上海市静安区南京路1266号', 'vip'),
        ('CUS-20260101002', '恒通电子科技', '林总', '0755-8888-2002', '深圳市南山区科技园大厦', 'normal'),
        ('CUS-20260101003', '绿源食品加工厂', '吴主管', '0571-8888-3003', '杭州市余杭区食品工业园', 'normal'),
        ('CUS-20260101004', '金达建材有限公司', '郑经理', '023-8888-4004', '重庆市九龙坡区建材城B栋', 'normal'),
        ('CUS-20260101005', '宝康医药连锁', '黄采购', '020-8888-5005', '广州市越秀区医药广场3层', 'vip'),
    ]
    for customer_no, name, contact_person, phone, address, level in customers_data:
        if not Customer.query.filter_by(name=name).first():
            db.session.add(Customer(customer_no=customer_no, name=name,
                                    contact_person=contact_person, phone=phone,
                                    address=address, level=level))
    db.session.commit()

    # ===== 车辆 =====
    vehicles_data = [
        ('沪A12345', '中型', '10.0', '30.0', 'idle'),
        ('沪B23456', '大型', '20.0', '60.0', 'idle'),
        ('沪C34567', '冷藏', '8.0',  '25.0', 'idle'),
        ('粤D45678', '中型', '10.0', '30.0', 'idle'),
        ('京E56789', '大型', '25.0', '80.0', 'idle'),
    ]
    for plate_no, v_type, weight, volume, status in vehicles_data:
        if not Vehicle.query.filter_by(plate_no=plate_no).first():
            db.session.add(Vehicle(plate_no=plate_no, type=v_type,
                                   capacity_weight=Decimal(weight),
                                   capacity_volume=Decimal(volume),
                                   status=status))
    db.session.commit()

    # ===== 司机 =====
    drivers_data = [
        ('刘大伟', '13800001001', 'A2', 'A2', 'available'),
        ('张志强', '13800002002', 'A1', 'A1', 'available'),
        ('王建国', '13800003003', 'B2', 'B2', 'available'),
        ('李文斌', '13800004004', 'A2', 'A2', 'available'),
        ('陈国强', '13800005005', 'A1', 'A1', 'available'),
    ]
    for name, phone, license_no, license_type, status in drivers_data:
        if not Driver.query.filter_by(name=name).first():
            db.session.add(Driver(name=name, phone=phone, license_no=license_no,
                                  license_type=license_type, status=status))
    db.session.commit()

    # ===== 商品分类 =====
    categories_data = [
        ('电子元件', None, 1), ('食品原料', None, 2), ('建筑材料', None, 3),
        ('医疗器械', None, 4), ('日用消费品', None, 5),
        ('芯片', 1, 1), ('电阻电容', 1, 2), ('面粉', 2, 1), ('调味料', 2, 2),
    ]
    for name, parent_id, sort_order in categories_data:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, parent_id=parent_id, sort_order=sort_order))
    db.session.commit()

    # ===== 商品 =====
    goods_data = [
        ('SKU001', 'CPU处理器', 'i7-13700K', '个', 1, 5, 50, '2000.00', '2800.00'),
        ('SKU002', '内存条', 'DDR5 16GB', '个', 1, 10, 100, '200.00', '350.00'),
        ('SKU003', '高筋面粉', '25kg/袋', '袋', 3, 20, 500, '80.00', '120.00'),
        ('SKU004', '酱油', '1.9L桶装', '箱', 4, 30, 200, '25.00', '45.00'),
        ('SKU005', '水泥', 'P.O 42.5 50kg/袋', '袋', 3, 50, 1000, '18.00', '30.00'),
        ('SKU006', '体温计', '电子款', '个', 4, 10, 200, '15.00', '35.00'),
        ('SKU007', '口罩', '医用N95', '箱', 4, 50, 500, '50.00', '98.00'),
        ('SKU008', '洗衣液', '2kg瓶装', '箱', 5, 20, 300, '30.00', '55.00'),
    ]
    for sku, name, spec, unit, cat_id, min_stock, max_stock, purchase, selling in goods_data:
        if not Goods.query.filter_by(sku=sku).first():
            db.session.add(Goods(sku=sku, name=name, spec=spec, unit=unit,
                                 category_id=cat_id, min_stock=min_stock,
                                 max_stock=max_stock,
                                 purchase_price=Decimal(purchase),
                                 selling_price=Decimal(selling),
                                 status='active'))
    db.session.commit()

    # ===== 仓库+库区+货位 =====
    warehouses_data = [
        ('上海总仓', '上海市闵行区物流园区88号', 'normal'),
        ('广州分仓', '广州市白云区物流大道56号', 'normal'),
        ('北京冷链仓', '北京市大兴区冷链物流中心', 'cold'),
    ]
    for name, address, w_type in warehouses_data:
        if not Warehouse.query.filter_by(name=name).first():
            db.session.add(Warehouse(name=name, address=address, type=w_type,
                                     total_locations=0, used_locations=0))
    db.session.commit()

    for wh_name, zones_cfg in [
        ('上海总仓', [('A', 'A区-电子元件区', 1), ('B', 'B区-食品区', 2), ('C', 'C区-建材区', 3)]),
        ('广州分仓', [('A', 'A区-日用百货区', 1), ('B', 'B区-食品区', 2)]),
    ]:
        wh = Warehouse.query.filter_by(name=wh_name).first()
        if wh and Zone.query.filter_by(warehouse_id=wh.id).count() == 0:
            for code, z_name, sort_order in zones_cfg:
                db.session.add(Zone(warehouse_id=wh.id, zone_code=code,
                                    zone_name=z_name, sort_order=sort_order))
            db.session.flush()
            zones = Zone.query.filter_by(warehouse_id=wh.id).all()
            loc_count = 0
            for zone in zones:
                for i in range(1, 6):
                    db.session.add(Location(
                        zone_id=zone.id,
                        loc_code=f'{zone.zone_code}-{i:02d}',
                        capacity_weight=Decimal('2.00'),
                        capacity_volume=Decimal('5.00'),
                        status='empty'
                    ))
                    loc_count += 1
            wh.total_locations = loc_count
            db.session.commit()

    print("✅ 基础数据初始化完成！")
    print("\n📋 默认账号列表：")
    print("   ┌─────────────────┬──────────┬──────────────────┐")
    print("   │ 用户名           │ 密码     │ 角色             │")
    print("   ├─────────────────┼──────────┼──────────────────┤")
    print("   │ admin           │ admin123 │ 系统管理员       │")
    print("   │ teacher01       │ 123456   │ 教师             │")
    print("   │ student01/02    │ 123456   │ 学生             │")
    print("   │ purchaser01     │ 123456   │ 采购专员         │")
    print("   │ cs01            │ 123456   │ 客服             │")
    print("   │ dispatcher01    │ 123456   │ 调度员           │")
    print("   │ keeper01        │ 123456   │ 仓库管理员       │")
    print("   │ driver01        │ 123456   │ 司机             │")
    print("   └─────────────────┴──────────┴──────────────────┘\n")


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login 加载用户回调"""
    from app.models.user import User
    return User.query.get(int(user_id))
