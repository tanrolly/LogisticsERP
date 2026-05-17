"""预警提醒 API —— 按类型返回预警列表"""
from flask import Blueprint, jsonify
from flask_login import login_required
from datetime import timedelta
from app.utils.time_helper import beijing_now
from app import db
from app.models.stock import Inventory
from app.models.finance import AccountsPayable, AccountsReceivable
from app.models.transport import Order
from app.models.contract import PurchaseContract, TransportContract

bp = Blueprint('alerts', __name__)


@bp.route('/alerts', methods=['GET'])
@login_required
def get_alerts():
    try:
        data = {
            'inventory': _inventory_alerts(),
            'expiry': _expiry_alerts(),
            'payable': _payable_alerts(),
            'receivable': _receivable_alerts(),
            'transport': _transport_alerts(),
            'contract': _contract_alerts(),
        }
        total = sum(len(v) for v in data.values())
        return jsonify({'code': 200, 'message': 'success', 'data': data, 'total': total})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@bp.route('/alerts/count', methods=['GET'])
@login_required
def get_alert_count():
    try:
        total = (
            len(_inventory_alerts()) +
            len(_expiry_alerts()) +
            len(_payable_alerts()) +
            len(_receivable_alerts()) +
            len(_transport_alerts()) +
            len(_contract_alerts())
        )
        return jsonify({'code': 200, 'message': 'success', 'data': {'total': total}})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


# ========== 各类预警计算函数 ==========

def _inventory_alerts():
    """库存预警：可用数量 <= 安全库存"""
    alerts = []
    items = Inventory.query.filter(
        Inventory.safety_stock > 0,
        Inventory.available_qty <= Inventory.safety_stock,
        Inventory.status == 'normal'
    ).all()

    for inv in items:
        gname = inv.goods.name if inv.goods else '未知商品'
        wname = inv.warehouse.name if inv.warehouse else '未知仓库'
        alerts.append({
            'id': f'inv_{inv.id}',
            'type': 'low_stock',
            'severity': 'high',
            'goods_name': gname,
            'warehouse_name': wname,
            'message': f'库存预警：{gname} 可用{inv.available_qty} ≤ 安全{inv.safety_stock}',
            'link': '/inventory',
        })
    return alerts


def _expiry_alerts():
    """库存有效期预警：30天内过期"""
    alerts = []
    today = beijing_now().date()
    threshold = today + timedelta(days=30)

    items = Inventory.query.filter(
        Inventory.expiry_date.isnot(None),
        Inventory.expiry_date <= threshold,
        Inventory.expiry_date >= today,
        Inventory.quantity > 0
    ).all()

    for inv in items:
        days_left = (inv.expiry_date - today).days
        gname = inv.goods.name if inv.goods else '未知商品'
        wname = inv.warehouse.name if inv.warehouse else '未知仓库'
        alerts.append({
            'id': f'exp_{inv.id}',
            'type': 'expiring',
            'severity': 'high' if days_left <= 7 else 'medium',
            'goods_name': gname,
            'warehouse_name': wname,
            'message': f'库存即将过期：{gname} 还剩{days_left}天（{inv.expiry_date}）',
            'link': '/inventory',
        })
    return alerts


def _payable_alerts():
    """应付到期提醒"""
    alerts = []
    today = beijing_now().date()

    overdue_items = AccountsPayable.query.filter(
        AccountsPayable.due_date < today,
        AccountsPayable.status.in_(['pending', 'partial_paid'])
    ).all()

    for ap in overdue_items:
        days_overdue = (today - ap.due_date).days
        sname = ap.supplier.name if ap.supplier else '未知供应商'
        alerts.append({
            'id': f'ap_{ap.id}',
            'type': 'overdue',
            'severity': 'high',
            'payable_no': ap.payable_no,
            'supplier_name': sname,
            'message': f'应付账款逾期{days_overdue}天：{ap.payable_no} 金额¥{float(ap.remaining_amount):.2f}',
            'link': f'/finance/payable/{ap.id}',
        })

    threshold = today + timedelta(days=7)
    upcoming_items = AccountsPayable.query.filter(
        AccountsPayable.due_date >= today,
        AccountsPayable.due_date <= threshold,
        AccountsPayable.status.in_(['pending', 'partial_paid'])
    ).all()

    for ap in upcoming_items:
        days_left = (ap.due_date - today).days
        sname = ap.supplier.name if ap.supplier else '未知供应商'
        alerts.append({
            'id': f'ap_up_{ap.id}',
            'type': 'upcoming',
            'severity': 'medium',
            'payable_no': ap.payable_no,
            'supplier_name': sname,
            'message': f'应付账款即将到期：{ap.payable_no} 还剩{days_left}天',
            'link': f'/finance/payable/{ap.id}',
        })

    return alerts


def _receivable_alerts():
    """应收到期提醒"""
    alerts = []
    today = beijing_now().date()

    overdue_items = AccountsReceivable.query.filter(
        AccountsReceivable.due_date < today,
        AccountsReceivable.status.in_(['pending', 'partial_received'])
    ).all()

    for ar in overdue_items:
        days_overdue = (today - ar.due_date).days
        cname = ar.customer.name if ar.customer else '未知客户'
        alerts.append({
            'id': f'ar_{ar.id}',
            'type': 'overdue',
            'severity': 'high',
            'receivable_no': ar.receivable_no,
            'customer_name': cname,
            'message': f'应收账款逾期{days_overdue}天：{ar.receivable_no} 金额¥{float(ar.remaining_amount):.2f}',
            'link': f'/finance/receivable/{ar.id}',
        })

    threshold = today + timedelta(days=7)
    upcoming_items = AccountsReceivable.query.filter(
        AccountsReceivable.due_date >= today,
        AccountsReceivable.due_date <= threshold,
        AccountsReceivable.status.in_(['pending', 'partial_received'])
    ).all()

    for ar in upcoming_items:
        days_left = (ar.due_date - today).days
        cname = ar.customer.name if ar.customer else '未知客户'
        alerts.append({
            'id': f'ar_up_{ar.id}',
            'type': 'upcoming',
            'severity': 'medium',
            'receivable_no': ar.receivable_no,
            'customer_name': cname,
            'message': f'应收账款即将到期：{ar.receivable_no} 还剩{days_left}天',
            'link': f'/finance/receivable/{ar.id}',
        })

    return alerts


def _transport_alerts():
    """运输超时预警"""
    alerts = []
    now = beijing_now()

    orders = Order.query.filter(
        Order.status == 'in_transit',
        Order.plan_arrival.isnot(None),
        Order.plan_arrival < now
    ).all()

    for order in orders:
        hours_delayed = int((now - order.plan_arrival).total_seconds() / 3600)
        cname = order.customer.name if order.customer else '未知客户'
        alerts.append({
            'id': f'to_{order.id}',
            'type': 'delayed',
            'severity': 'high' if hours_delayed > 24 else 'medium',
            'order_no': order.order_no,
            'customer_name': cname,
            'message': f'运输超时：{order.order_no} 已超时{hours_delayed}小时',
            'link': f'/transport/orders/{order.id}',
        })

    return alerts


def _contract_alerts():
    """合同到期提醒"""
    alerts = []
    today = beijing_now().date()
    threshold = today + timedelta(days=30)

    pc_items = PurchaseContract.query.filter(
        PurchaseContract.end_date.isnot(None),
        PurchaseContract.end_date <= threshold,
        PurchaseContract.end_date >= today,
        PurchaseContract.status.in_(['active', 'approved'])
    ).all()

    for pc in pc_items:
        days_left = (pc.end_date - today).days
        alerts.append({
            'id': f'pc_{pc.id}',
            'type': 'expiring',
            'severity': 'medium',
            'contract_no': pc.contract_no,
            'message': f'采购合同即将到期：{pc.contract_no} 还剩{days_left}天',
            'link': f'/contract/detail/purchase/{pc.id}',
        })

    tc_items = TransportContract.query.filter(
        TransportContract.end_date.isnot(None),
        TransportContract.end_date <= threshold,
        TransportContract.end_date >= today,
        TransportContract.status.in_(['active', 'approved'])
    ).all()

    for tc in tc_items:
        days_left = (tc.end_date - today).days
        alerts.append({
            'id': f'tc_{tc.id}',
            'type': 'expiring',
            'severity': 'medium',
            'contract_no': tc.contract_no,
            'message': f'运输合同即将到期：{tc.contract_no} 还剩{days_left}天',
            'link': f'/contract/detail/transport/{tc.id}',
        })

    return alerts
