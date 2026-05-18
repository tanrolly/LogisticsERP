"""财务结算模块测试脚本"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.role import Role
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.goods import Goods
from app.models.purchase import PurchaseRequest, PurchaseOrder, PurchaseOrderItem, PurchaseReceipt
from app.models.transport import Order
from app.models.warehouse import Warehouse
from app.models.inbound import InboundOrder, InboundItem
from app.models.finance import AccountsPayable, PayablePayment, AccountsReceivable, ReceivablePayment
from datetime import date, datetime
from decimal import Decimal
from app.utils.time_helper import beijing_now

app = create_app()

PASSED = 0
FAILED = 0

def test(name, condition, detail=''):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f'  [PASS] {name}')
    else:
        FAILED += 1
        print(f'  [FAIL] {name} {detail}')

with app.app_context():
    # 清空数据
    PayablePayment.query.delete()
    ReceivablePayment.query.delete()
    AccountsPayable.query.delete()
    AccountsReceivable.query.delete()
    PurchaseReceipt.query.delete()
    PurchaseOrderItem.query.delete()
    PurchaseOrder.query.delete()
    PurchaseRequest.query.delete()
    Order.query.delete()
    InboundItem.query.delete()
    InboundOrder.query.delete()
    db.session.commit()

    print('=== 财务结算模块测试 ===')
    print()

    # 创建测试基础数据
    admin = User.query.filter_by(username='admin').first()
    role_student = Role.query.filter_by(code='student').first()
    student = User(username='student_finance', real_name='财务测试学生', email='fin@test.com', role_id=role_student.id)
    student.password = '123456'
    db.session.add(student)
    db.session.flush()

    supplier = Supplier(name='测试供应商', contact='张三', phone='13800000001', status='active')
    db.session.add(supplier)
    db.session.flush()

    customer = Customer(customer_no='C001', name='测试客户', contact_person='李四', phone='13900000001', level='vip', status='active')
    db.session.add(customer)
    db.session.flush()

    goods = Goods(sku='G001', name='测试商品', unit='个', purchase_price=Decimal('50.00'), selling_price=Decimal('80.00'), status='active')
    db.session.add(goods)
    db.session.flush()

    warehouse = Warehouse(name='测试仓库', address='测试地址', status='active')
    db.session.add(warehouse)
    db.session.flush()

    db.session.commit()

    # ---- 准备已完成采购订单 ----
    pr = PurchaseRequest(
        req_no='PR-20260501001', applicant_id=admin.id, goods_id=goods.id,
        quantity=100, est_unit_price=Decimal('50.00'), est_total_price=Decimal('5000.00'),
        status='approved', reviewer_id=admin.id, reviewed_at=beijing_now()
    )
    db.session.add(pr)
    db.session.flush()

    po = PurchaseOrder(
        po_no='PO-20260501001', request_id=pr.id, supplier_id=supplier.id,
        total_amount=Decimal('5000.00'), status='completed', operator_id=admin.id
    )
    db.session.add(po)
    db.session.flush()

    # 准备已完成的运输订单
    transport_order = Order(
        order_no='TO-20260501001', customer_id=customer.id,
        origin='北京', destination='上海', goods_name='测试商品', goods_id=goods.id,
        weight=Decimal('100.00'), quantity=100,
        freight_amount=Decimal('3000.00'), status='completed',
        operator_id=admin.id
    )
    db.session.add(transport_order)
    db.session.flush()

    db.session.commit()

    # ===== 测试1: 模型创建 - 应付账款 =====
    print('--- 测试1: 应付账款模型 ---')
    ap = AccountsPayable(
        payable_no='AP-20260501001', po_id=po.id, supplier_id=supplier.id,
        total_amount=Decimal('5000.00'), paid_amount=Decimal('0'),
        remaining_amount=Decimal('5000.00'), status='pending',
        due_date=date(2026, 6, 1), operator_id=admin.id
    )
    db.session.add(ap)
    db.session.flush()

    test('应付账款创建成功', ap.id is not None)
    test('应付编号正确', ap.payable_no == 'AP-20260501001')
    test('关联采购订单正确', ap.purchase_order.po_no == 'PO-20260501001')
    test('关联供应商正确', ap.supplier.name == '测试供应商')
    test('金额字段正确', float(ap.total_amount) == 5000.00 and float(ap.remaining_amount) == 5000.00)
    test('状态默认pending', ap.status == 'pending')

    # ===== 测试2: 模型创建 - 应收账款 =====
    print('\n--- 测试2: 应收账款模型 ---')
    ar = AccountsReceivable(
        receivable_no='AR-20260501001', order_id=transport_order.id, customer_id=customer.id,
        total_amount=Decimal('3000.00'), received_amount=Decimal('0'),
        remaining_amount=Decimal('3000.00'), status='pending',
        due_date=date(2026, 6, 1), operator_id=admin.id
    )
    db.session.add(ar)
    db.session.flush()

    test('应收账款创建成功', ar.id is not None)
    test('应收编号正确', ar.receivable_no == 'AR-20260501001')
    test('关联运输订单正确', ar.transport_order.order_no == 'TO-20260501001')
    test('关联客户正确', ar.customer.name == '测试客户')
    test('金额字段正确', float(ar.total_amount) == 3000.00)

    db.session.commit()

    # ===== 测试3: 付款记录 =====
    print('\n--- 测试3: 付款记录 ---')
    payment1 = PayablePayment(
        payable_id=ap.id, payment_amount=Decimal('2000.00'),
        payment_method='bank_transfer', payment_date=date.today(),
        remark='第一次付款', operator_id=admin.id
    )
    db.session.add(payment1)
    db.session.flush()

    # 更新应付账款
    ap.paid_amount = Decimal('2000.00')
    ap.remaining_amount = Decimal('3000.00')
    ap.status = 'partial_paid'
    db.session.commit()

    test('付款记录创建成功', payment1.id is not None)
    test('付款金额正确', float(payment1.payment_amount) == 2000.00)
    test('应付状态更新为partial_paid', ap.status == 'partial_paid')
    test('已付金额更新正确', float(ap.paid_amount) == 2000.00)
    test('剩余金额更新正确', float(ap.remaining_amount) == 3000.00)

    # ===== 测试4: 付清逻辑 =====
    print('\n--- 测试4: 付清逻辑 ---')
    payment2 = PayablePayment(
        payable_id=ap.id, payment_amount=Decimal('3000.00'),
        payment_method='cash', payment_date=date.today(),
        remark='第二次付清', operator_id=admin.id
    )
    db.session.add(payment2)
    db.session.flush()

    ap.paid_amount = Decimal('5000.00')
    ap.remaining_amount = Decimal('0')
    ap.status = 'paid'
    db.session.commit()

    test('第二次付款记录创建成功', payment2.id is not None)
    test('应付状态更新为paid', ap.status == 'paid')
    test('已付金额等于总额', float(ap.paid_amount) == float(ap.total_amount))
    test('剩余金额为0', float(ap.remaining_amount) == 0)

    # ===== 测试5: 收款记录 =====
    print('\n--- 测试5: 收款记录 ---')
    receipt1 = ReceivablePayment(
        receivable_id=ar.id, payment_amount=Decimal('1500.00'),
        payment_method='bank_transfer', payment_date=date.today(),
        remark='第一次收款', operator_id=admin.id
    )
    db.session.add(receipt1)
    db.session.flush()

    ar.received_amount = Decimal('1500.00')
    ar.remaining_amount = Decimal('1500.00')
    ar.status = 'partial_received'
    db.session.commit()

    test('收款记录创建成功', receipt1.id is not None)
    test('应收状态更新为partial_received', ar.status == 'partial_received')
    test('已收金额正确', float(ar.received_amount) == 1500.00)

    # ===== 测试6: 收齐逻辑 =====
    print('\n--- 测试6: 收齐逻辑 ---')
    receipt2 = ReceivablePayment(
        receivable_id=ar.id, payment_amount=Decimal('1500.00'),
        payment_method='check', payment_date=date.today(),
        remark='第二次收齐', operator_id=admin.id
    )
    db.session.add(receipt2)
    db.session.flush()

    ar.received_amount = Decimal('3000.00')
    ar.remaining_amount = Decimal('0')
    ar.status = 'received'
    db.session.commit()

    test('应收状态更新为received', ar.status == 'received')
    test('已收金额等于总额', float(ar.received_amount) == float(ar.total_amount))

    # ===== 测试7: to_dict 序列化 =====
    print('\n--- 测试7: to_dict 序列化 ---')
    ap_dict = ap.to_dict(include_payments=True)
    test('应付to_dict包含基本字段', 'payable_no' in ap_dict and 'total_amount' in ap_dict)
    test('应付to_dict包含付款记录', 'payments' in ap_dict and len(ap_dict['payments']) == 2)
    test('应付to_dict金额为float', isinstance(ap_dict['total_amount'], float))

    ar_dict = ar.to_dict(include_payments=True)
    test('应收to_dict包含基本字段', 'receivable_no' in ar_dict and 'total_amount' in ar_dict)
    test('应收to_dict包含收款记录', 'payments' in ar_dict and len(ar_dict['payments']) == 2)

    # ===== 测试8: API端点测试 =====
    print('\n--- 测试8: API端点测试 ---')
    client = app.test_client()

    # 登录
    login_res = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
    test('管理员登录成功', login_res.status_code == 200 and login_res.get_json()['code'] == 200)

    # 财务概览
    overview_res = client.get('/api/finance/overview')
    test('财务概览API可达', overview_res.status_code == 200)
    overview_data = overview_res.get_json()
    test('财务概览返回数据结构正确', overview_data['code'] == 200 and 'payable' in overview_data['data'] and 'receivable' in overview_data['data'])

    # 应付账款列表
    payable_list_res = client.get('/api/finance/payable')
    test('应付账款列表API可达', payable_list_res.status_code == 200)
    payable_list_data = payable_list_res.get_json()
    test('应付账款列表有数据', payable_list_data['code'] == 200 and len(payable_list_data['data']) > 0)

    # 应付账款详情
    payable_detail_res = client.get(f'/api/finance/payable/{ap.id}')
    test('应付账款详情API可达', payable_detail_res.status_code == 200)
    payable_detail_data = payable_detail_res.get_json()
    test('应付账款详情包含付款记录', payable_detail_data['code'] == 200 and len(payable_detail_data['data'].get('payments', [])) >= 2)

    # 应收账款列表
    receivable_list_res = client.get('/api/finance/receivable')
    test('应收账款列表API可达', receivable_list_res.status_code == 200)

    # 应收账款详情
    receivable_detail_res = client.get(f'/api/finance/receivable/{ar.id}')
    test('应收账款详情API可达', receivable_detail_res.status_code == 200)

    # 付款记录列表
    payments_res = client.get(f'/api/finance/payable/{ap.id}/payments')
    test('付款记录列表API可达', payments_res.status_code == 200)

    # 收款记录列表
    receipts_res = client.get(f'/api/finance/receivable/{ar.id}/payments')
    test('收款记录列表API可达', receipts_res.status_code == 200)

    # ===== 测试9: API生成应付账款 =====
    print('\n--- 测试9: API生成应付账款 ---')
    # 创建另一个完成的采购订单
    pr2 = PurchaseRequest(
        req_no='PR-20260501002', applicant_id=admin.id, goods_id=goods.id,
        quantity=50, est_unit_price=Decimal('30.00'), est_total_price=Decimal('1500.00'),
        status='approved', reviewer_id=admin.id, reviewed_at=beijing_now()
    )
    db.session.add(pr2)
    db.session.flush()

    po2 = PurchaseOrder(
        po_no='PO-20260501002', request_id=pr2.id, supplier_id=supplier.id,
        total_amount=Decimal('1500.00'), status='completed', operator_id=admin.id
    )
    db.session.add(po2)
    db.session.commit()

    create_ap_res = client.post('/api/finance/payable', json={'po_id': po2.id})
    test('API生成应付账款成功', create_ap_res.get_json()['code'] == 200)
    new_ap = create_ap_res.get_json()['data']
    test('生成金额正确', float(new_ap['total_amount']) == 1500.00)

    # 重复生成
    create_ap_dup = client.post('/api/finance/payable', json={'po_id': po2.id})
    test('重复生成应付被拒绝', create_ap_dup.get_json()['code'] != 200)

    # 未完成订单生成
    po_pending = PurchaseOrder(
        po_no='PO-20260501003', request_id=pr2.id, supplier_id=supplier.id,
        total_amount=Decimal('1000.00'), status='pending', operator_id=admin.id
    )
    db.session.add(po_pending)
    db.session.commit()

    create_ap_pending = client.post('/api/finance/payable', json={'po_id': po_pending.id})
    test('未完成订单不能生成应付', create_ap_pending.get_json()['code'] != 200)

    # ===== 测试10: API生成应收账款 =====
    print('\n--- 测试10: API生成应收账款 ---')
    order2 = Order(
        order_no='TO-20260501002', customer_id=customer.id,
        origin='广州', destination='深圳', goods_name='测试商品2', goods_id=goods.id,
        weight=Decimal('50.00'), quantity=50,
        freight_amount=Decimal('2000.00'), status='completed',
        operator_id=admin.id
    )
    db.session.add(order2)
    db.session.commit()

    create_ar_res = client.post('/api/finance/receivable', json={'order_id': order2.id})
    test('API生成应收账款成功', create_ar_res.get_json()['code'] == 200)
    new_ar = create_ar_res.get_json()['data']
    test('生成金额正确', float(new_ar['total_amount']) == 2000.00)

    # ===== 测试11: API记录付款 =====
    print('\n--- 测试11: API记录付款 ---')
    pay_res = client.post(f'/api/finance/payable/{new_ap["id"]}/pay', json={
        'payment_amount': 800.00,
        'payment_method': 'bank_transfer',
        'payment_date': date.today().isoformat(),
        'remark': '部分付款测试'
    })
    test('API记录付款成功', pay_res.get_json()['code'] == 200)
    updated_ap = pay_res.get_json()['data']
    test('付款后状态为partial_paid', updated_ap['status'] == 'partial_paid')
    test('付款后已付金额正确', float(updated_ap['paid_amount']) == 800.00)

    # 付款金额超限
    pay_over = client.post(f'/api/finance/payable/{new_ap["id"]}/pay', json={
        'payment_amount': 800.00,  # 剩余700，超过
        'payment_method': 'cash',
        'payment_date': date.today().isoformat()
    })
    test('超限付款被拒绝', pay_over.get_json()['code'] != 200)

    # 付清
    pay_final = client.post(f'/api/finance/payable/{new_ap["id"]}/pay', json={
        'payment_amount': 700.00,
        'payment_method': 'cash',
        'payment_date': date.today().isoformat()
    })
    test('付清后状态为paid', pay_final.get_json()['data']['status'] == 'paid')

    # ===== 测试12: Dashboard集成 =====
    print('\n--- 测试12: Dashboard财务集成 ---')
    dashboard_res = client.get('/api/dashboard/stats')
    test('Dashboard API包含财务数据', dashboard_res.get_json()['data'].get('finance') is not None)
    finance_stats = dashboard_res.get_json()['data']['finance']
    test('Dashboard应付待付数>=0', finance_stats['payable_pending'] >= 0)
    test('Dashboard应收待收数>=0', finance_stats['receivable_pending'] >= 0)

    # ===== 测试13: 状态筛选 =====
    print('\n--- 测试13: 状态筛选 ---')
    filter_res = client.get('/api/finance/payable?status=paid')
    test('按状态筛选应付成功', filter_res.get_json()['code'] == 200)
    filter_data = filter_res.get_json()['data']
    test('筛选结果全部为paid', all(item['status'] == 'paid' for item in filter_data))

    # ===== 汇总 =====
    print()
    print('=' * 40)
    print(f'测试完成: {PASSED} 通过, {FAILED} 失败, 共 {PASSED + FAILED} 项')
    if FAILED == 0:
        print('全部测试通过!')
    else:
        print('存在失败测试，请检查!')
    print('=' * 40)
