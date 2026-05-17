"""
数据可视化报表 API
提供库存周转率、采购成本对比、运输准时率、仓库利用率等报表数据
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from flask_login import login_required
from app import db
from app.models import (
    PurchaseOrder, Order, InboundOrder,
    OutboundOrder, Inventory, Warehouse, Location, Goods, Supplier
)
from datetime import datetime, timedelta

bp = Blueprint('reports', __name__)
from app.utils.time_helper import beijing_now


@bp.route('/reports/inventory-turnover', methods=['GET'])
@login_required
def inventory_turnover():
    """库存周转率折线图"""
    try:
        months = []
        turnover_data = []

        for i in range(5, -1, -1):
            date = beijing_now() - timedelta(days=30*i)
            year_month = f"{date.year}-{date.month:02d}"
            months.append(year_month)

            month_start = datetime(date.year, date.month, 1)
            if date.month == 12:
                month_end = datetime(date.year + 1, 1, 1)
            else:
                month_end = datetime(date.year, date.month + 1, 1)

            outbound_count = OutboundOrder.query.filter(
                OutboundOrder.created_at >= month_start,
                OutboundOrder.created_at < month_end,
                OutboundOrder.status == 'shipped'
            ).count()

            avg_inventory = db.session.query(func.coalesce(func.sum(Inventory.quantity), 0)).scalar() or 1
            turnover_rate = round(outbound_count / max(avg_inventory, 1) * 100, 2)
            turnover_data.append(turnover_rate)

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'months': months,
                'turnover_rates': turnover_data
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取数据失败: {str(e)}'}), 500


@bp.route('/reports/procurement-cost', methods=['GET'])
@login_required
def procurement_cost():
    """采购成本对比柱状图"""
    try:
        suppliers = db.session.query(
            PurchaseOrder.supplier_id,
            func.sum(PurchaseOrder.total_amount).label('total_cost')
        ).filter(
            PurchaseOrder.status.in_(['confirmed', 'partial', 'completed'])
        ).group_by(PurchaseOrder.supplier_id).limit(5).all()

        supplier_names = []
        cost_data = []

        for supplier_id, total_cost in suppliers:
            supplier = Supplier.query.get(supplier_id)
            if supplier:
                supplier_names.append(supplier.name[:10])
                cost_data.append(float(total_cost))

        if not supplier_names:
            supplier_names = ['示例供应商A', '示例供应商B', '示例供应商C']
            cost_data = [0, 0, 0]

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'suppliers': supplier_names,
                'costs': cost_data
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取数据失败: {str(e)}'}), 500


@bp.route('/reports/transport-ontime', methods=['GET'])
@login_required
def transport_ontime():
    """运输准时率饼图"""
    try:
        completed_orders = Order.query.filter(
            Order.status == 'completed'
        ).all()

        ontime_count = 0
        delayed_count = 0

        for order in completed_orders:
            if order.actual_arrival and order.plan_arrival:
                if order.actual_arrival <= order.plan_arrival + timedelta(days=1):
                    ontime_count += 1
                else:
                    delayed_count += 1
            else:
                ontime_count += 1

        if ontime_count == 0 and delayed_count == 0:
            ontime_count = 85
            delayed_count = 15

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'ontime_rate': ontime_count,
                'delayed_rate': delayed_count
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取数据失败: {str(e)}'}), 500


@bp.route('/reports/warehouse-utilization', methods=['GET'])
@login_required
def warehouse_utilization():
    """仓库利用率雷达图"""
    try:
        warehouses = Warehouse.query.all()

        warehouse_names = []
        utilization_rates = []

        for warehouse in warehouses:
            warehouse_names.append(warehouse.name)

            total_locations = Location.query.filter_by(warehouse_id=warehouse.id).count()

            used_locations = db.session.query(
                func.count(func.distinct(Inventory.location_id))
            ).filter(
                Inventory.warehouse_id == warehouse.id,
                Inventory.quantity > 0
            ).scalar() or 0

            utilization_rate = round((used_locations / max(total_locations, 1)) * 100, 2)
            utilization_rates.append(utilization_rate)

        if not warehouse_names:
            warehouse_names = ['上海仓', '北京仓', '广州仓', '深圳仓', '成都仓']
            utilization_rates = [0, 0, 0, 0, 0]

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'warehouses': warehouse_names,
                'utilization_rates': utilization_rates
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取数据失败: {str(e)}'}), 500


@bp.route('/reports/overview', methods=['GET'])
@login_required
def reports_overview():
    """报表总览数据"""
    try:
        purchase_count = PurchaseOrder.query.count()
        transport_count = Order.query.count()
        inbound_count = InboundOrder.query.filter_by(status='shelved').count()
        outbound_count = OutboundOrder.query.filter_by(status='shipped').count()

        low_stock_count = db.session.query(func.count(func.distinct(Inventory.goods_id))).filter(
            Inventory.quantity < 10
        ).scalar() or 0

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'purchase_orders': purchase_count,
                'transport_orders': transport_count,
                'inbound_orders': inbound_count,
                'outbound_orders': outbound_count,
                'low_stock_alerts': low_stock_count
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取数据失败: {str(e)}'}), 500
