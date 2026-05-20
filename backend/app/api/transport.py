from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.transport import Order, TransportRecord, TransportException
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.goods import Goods
from app.socket import broadcast_order_status
from app.api.logs import log_operation
from app.utils.scoring import score_operation
from app.utils.time_helper import beijing_now
from app.utils.permissions import role_required
from app.utils.notification_helper import send_notification, notify_role_users
from app.models.approval import ApprovalRecord
from datetime import datetime, date
from decimal import Decimal

bp = Blueprint('transport', __name__)


def success_response(data=None, message='success'):
    return jsonify({'code': 200, 'message': message, 'data': data}), 200


def error_response(message, code=400):
    return jsonify({'code': code, 'message': message, 'data': None}), 200


def generate_order_no():
    """生成运输订单号 T-YYYYMMDDNNN"""
    today = date.today().strftime('%Y%m%d')
    count = Order.query.filter(Order.order_no.like(f'T-{today}%')).count()
    return f'T-{today}{count + 1:03d}'


# ==================== 运输订单 ====================

@bp.route('/orders', methods=['GET'])
@login_required
def get_orders():
    """获取运输订单列表"""
    status = request.args.get('status')
    customer_id = request.args.get('customer_id')
    query = Order.query

    if status:
        query = query.filter_by(status=status)
    if customer_id:
        query = query.filter_by(customer_id=int(customer_id))

    orders = query.order_by(Order.created_at.desc()).all()
    return success_response([o.to_dict() for o in orders])


@bp.route('/orders', methods=['POST'])
@login_required
def create_order():
    """创建运输订单"""
    data = request.get_json()

    if not data or not data.get('customer_id') or not data.get('origin') or not data.get('destination'):
        return error_response('客户、发货地和目的地不能为空')

    customer = Customer.query.get(data['customer_id'])
    if not customer:
        return error_response('客户不存在')

    order = Order(
        order_no=generate_order_no(),
        customer_id=customer.id,
        origin=data['origin'],
        destination=data['destination'],
        goods_name=data.get('goods_name', ''),
        goods_id=data.get('goods_id'),
        weight=data.get('weight'),
        volume=data.get('volume'),
        quantity=data.get('quantity'),
        remark=data.get('remark', ''),
        group_id=data.get('group_id'),
        operator_id=current_user.id,
        status='pending'
    )

    db.session.add(order)
    db.session.commit()

    # 记录审批记录（提交）
    _create_approval_record('transport_order', order.id, 'submit', current_user,
                            f'创建运输订单 {order.order_no}')
    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='create',
        target_type='Order',
        target_id=order.id,
        description=f'创建运输订单 {order.order_no}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='create')
    broadcast_order_status('transport_order', order.id, 'pending', current_user.group_id)

    # 通知审批人：有新的运输订单待审核
    notify_role_users('admin', 'approval',
                      '新的运输订单待审核',
                      f'{current_user.real_name} 创建了运输订单 {order.order_no}，请及时审核。',
                      reference_type='transport_order', reference_id=order.id,
                      sender_id=current_user.id)

    return success_response(order.to_dict(), '运输订单创建成功')


@bp.route('/orders/<int:order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    """获取运输订单详情"""
    order = Order.query.get_or_404(order_id)
    return success_response(order.to_dict())


@bp.route('/orders/<int:order_id>/approve', methods=['PUT'])
@role_required('admin', 'dispatcher')
@login_required
def approve_order(order_id):
    """审核通过运输订单"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'pending':
        return error_response('该订单不在待审核状态')

    order.status = 'approved'
    db.session.commit()

    _create_approval_record('transport_order', order.id, 'approve', current_user)

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='approve',
        target_type='Order',
        target_id=order.id,
        description=f'审核通过运输订单 {order.order_no}'
    )
    db.session.commit()

    # 评分 + 通知待办
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='approve')
    broadcast_order_status('transport_order', order.id, 'approved', current_user.group_id)

    # 通知创建人：运输订单已审核通过
    if order.operator_id:
        send_notification(order.operator_id, 'approval',
                          '运输订单已审核通过',
                          f'您的运输订单 {order.order_no} 已审核通过，等待调度。',
                          reference_type='transport_order', reference_id=order.id,
                          sender_id=current_user.id)

    return success_response(order.to_dict(), '审核通过')


@bp.route('/orders/<int:order_id>/reject', methods=['PUT'])
@role_required('admin', 'dispatcher')
@login_required
def reject_order(order_id):
    """审核驳回运输订单"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'pending':
        return error_response('该订单不在待审核状态')

    data = request.get_json() or {}
    reject_comment = data.get('comment', '驳回')
    order.status = 'cancelled'
    db.session.commit()

    _create_approval_record('transport_order', order.id, 'reject', current_user,
                            reject_comment)

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='reject',
        target_type='Order',
        target_id=order.id,
        description=f'驳回运输订单 {order.order_no}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='reject')
    broadcast_order_status('transport_order', order.id, 'cancelled', current_user.group_id)

    # 通知创建人：运输订单已驳回
    if order.operator_id:
        send_notification(order.operator_id, 'approval',
                          '运输订单已驳回',
                          f'您的运输订单 {order.order_no} 已被驳回。原因：{reject_comment}',
                          reference_type='transport_order', reference_id=order.id,
                          sender_id=current_user.id)

    return success_response(order.to_dict(), '已驳回')


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


@bp.route('/orders/<int:order_id>/return', methods=['PUT'])
@role_required('admin', 'dispatcher')
@login_required
def return_order(order_id):
    """退回运输订单（可重新提交）"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'pending':
        return error_response('该订单不在待审核状态')

    data = request.get_json() or {}
    comment = data.get('comment', '')
    if not comment:
        return error_response('退回意见不能为空')

    order.status = 'returned'
    db.session.commit()

    _create_approval_record('transport_order', order.id, 'return', current_user, comment)

    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='return',
        target_type='Order',
        target_id=order.id,
        description=f'退回运输订单 {order.order_no}，意见：{comment}'
    )
    db.session.commit()

    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='return')
    broadcast_order_status('transport_order', order.id, 'returned', current_user.group_id)

    # 通知创建人：运输订单被退回
    if order.operator_id:
        send_notification(order.operator_id, 'approval',
                          '运输订单已退回',
                          f'您的运输订单 {order.order_no} 已被退回。意见：{comment}，请修改后重新提交。',
                          reference_type='transport_order', reference_id=order.id,
                          sender_id=current_user.id)

    return success_response(order.to_dict(), '已退回，申请人可修改后重新提交')


@bp.route('/orders/<int:order_id>/resubmit', methods=['PUT'])
@login_required
def resubmit_order(order_id):
    """重新提交运输订单（仅创建人可操作）"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'returned':
        return error_response('只有被退回的订单才能重新提交')
    if order.operator_id != current_user.id:
        return error_response('只有创建人才能重新提交')

    order.status = 'pending'
    db.session.commit()

    _create_approval_record('transport_order', order.id, 'resubmit', current_user, '重新提交')

    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='resubmit',
        target_type='Order',
        target_id=order.id,
        description=f'重新提交运输订单 {order.order_no}'
    )
    db.session.commit()

    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='resubmit')
    broadcast_order_status('transport_order', order.id, 'pending', current_user.group_id)

    return success_response(order.to_dict(), '运输订单已重新提交，等待审核')


@bp.route('/orders/<int:order_id>/dispatch', methods=['PUT'])
@role_required('admin', 'dispatcher')
@login_required
def dispatch_order(order_id):
    """车辆调度"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'approved':
        return error_response('订单状态不允许调度')

    data = request.get_json() or {}

    vehicle_id = data.get('vehicle_id')
    driver_id = data.get('driver_id')

    if vehicle_id:
        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle:
            order.vehicle_id = vehicle.id
            vehicle.status = 'in_transport'

    if driver_id:
        driver = Driver.query.get(driver_id)
        if driver:
            order.driver_id = driver.id
            driver.status = 'on_road'

    order.status = 'dispatched'

    if data.get('plan_departure'):
        order.plan_departure = datetime.fromisoformat(data['plan_departure'])
    if data.get('plan_arrival'):
        order.plan_arrival = datetime.fromisoformat(data['plan_arrival'])

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='dispatch',
        target_type='Order',
        target_id=order.id,
        description=f'调度运输订单 {order.order_no}，车辆:{vehicle.plate_no if vehicle else ""}，司机:{driver.name if driver else ""}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='dispatch')
    broadcast_order_status('transport_order', order.id, 'dispatched', current_user.group_id)

    # 通知司机：有新的运输任务
    if driver_id:
        send_notification(driver_id, 'todo',
                          '新的运输任务',
                          f'运输订单 {order.order_no} 已调度给您，{order.origin} → {order.destination}，请准备出发。',
                          reference_type='transport_order', reference_id=order.id,
                          sender_id=current_user.id)

    return success_response(order.to_dict(), '调度完成')


@bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@role_required('admin', 'driver', 'dispatcher')
@login_required
def update_order_status(order_id):
    """更新订单状态（发车/到达/签收/完成）"""
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}

    new_status = data.get('status')
    valid_transitions = {
        'dispatched': ['in_transit'],
        'in_transit': ['arrived'],
        'arrived': ['signed'],
        'signed': ['completed'],
    }

    allowed = valid_transitions.get(order.status, [])
    if not new_status or new_status not in allowed:
        return error_response(f'状态不允许从 {order.status} 变更为 {new_status}')

    # 更新实际时间
    now = beijing_now()
    if new_status == 'in_transit' and not order.actual_departure:
        order.actual_departure = now
    elif new_status == 'arrived' and not order.actual_arrival:
        order.actual_arrival = now
    elif new_status == 'signed':
        order.signee_name = data.get('signee_name', '')
        order.signee_phone = data.get('signee_phone', '')

    order.status = new_status
    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='update_status',
        target_type='Order',
        target_id=order.id,
        description=f'更新运输订单 {order.order_no} 状态为 {new_status}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='update_status')
    broadcast_order_status('transport_order', order.id, new_status, current_user.group_id)

    return success_response(order.to_dict(), '状态已更新')


@bp.route('/orders/<int:order_id>/pod', methods=['POST'])
@role_required('admin', 'driver', 'dispatcher')
@login_required
def confirm_pod(order_id):
    """POD签收确认"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'arrived':
        return error_response('订单未到达，不能确认POD')

    data = request.get_json() or {}

    order.pod_status = 'signed'
    order.signee_name = data.get('signee_name', order.signee_name or '')
    order.signee_phone = data.get('signee_phone', order.signee_phone or '')
    order.pod_signed_at = beijing_now()

    # 处理POD图片上传（模拟）
    if data.get('pod_image'):
        order.pod_image = data['pod_image']

    order.status = 'signed'
    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='pod_confirm',
        target_type='Order',
        target_id=order.id,
        description=f'POD签收确认 {order.order_no}，签收人：{order.signee_name}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='pod_confirm')
    broadcast_order_status('transport_order', order.id, 'signed', current_user.group_id)

    return success_response(order.to_dict(), 'POD签收确认成功')


@bp.route('/orders/<int:order_id>/complete', methods=['PUT'])
@role_required('admin', 'driver', 'dispatcher')
@login_required
def complete_order(order_id):
    """完成订单（POD确认后）"""
    order = Order.query.get_or_404(order_id)

    if order.status != 'signed':
        return error_response('订单未完成POD签收，不能完成')

    order.status = 'completed'

    # ① 释放车辆：恢复为空闲
    if order.vehicle_id:
        vehicle = Vehicle.query.get(order.vehicle_id)
        if vehicle:
            vehicle.status = 'idle'

    # ② 释放司机：恢复为可用
    if order.driver_id:
        driver = Driver.query.get(order.driver_id)
        if driver:
            driver.status = 'available'

    # 获取请求数据（实际运费）
    data = request.get_json() or {}
    actual_freight = data.get('actual_freight')
    remark = data.get('remark', '')
  
    # 如果提供了实际运费，更新运费金额
    if actual_freight is not None:
        order.freight_amount = actual_freight
  
    # 如果有备注，保存到订单
    if remark and hasattr(order, 'remark'):
        if not order.remark:
            order.remark = remark
        else:
            order.remark += f' | {remark}'

    db.session.commit()

    # ④ 自动生成应收账款（幂等：已存在则跳过）
    _auto_create_receivable(order)

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='complete',
        target_type='Order',
        target_id=order.id,
        description=f'完成运输订单 {order.order_no}，运费 {order.freight_amount} 元，车辆/司机已释放'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='complete')
    broadcast_order_status('transport_order', order.id, 'completed', current_user.group_id)

    return success_response(order.to_dict(), '订单已完成，运费已计算，应收账款已生成')


def _auto_create_receivable(order):
    """订单完成时自动生成应收账款（幂等）"""
    try:
        from app.models.finance import AccountsReceivable
        from app.api.finance import generate_receivable_no

        # 已有则跳过
        if AccountsReceivable.query.filter_by(order_id=order.id).first():
            return

        total_amount = float(order.freight_amount) if order.freight_amount else 0
        if total_amount <= 0:
            return

        group_id = None
        try:
            if hasattr(current_user, 'group_id'):
                group_id = current_user.group_id
        except Exception:
            pass

        receivable = AccountsReceivable(
            receivable_no=generate_receivable_no(),
            order_id=order.id,
            customer_id=order.customer_id,
            total_amount=total_amount,
            received_amount=0,
            remaining_amount=total_amount,
            status='pending',
            operator_id=current_user.id,
            group_id=group_id
        )
        db.session.add(receivable)
        db.session.commit()

        log_operation(
            user_id=current_user.id,
            group_id=group_id,
            module='finance',
            action='create_receivable',
            target_type='AccountsReceivable',
            target_id=receivable.id,
            description=f'[自动] 运输订单 {order.order_no} 完成，生成应收账款 {receivable.receivable_no}，金额 {total_amount}'
        )
        score_operation(
            user_id=current_user.id,
            group_id=group_id,
            module='finance',
            action='create_receivable',
            extra_data={'description': f'自动生成应收账款 {receivable.receivable_no}'}
        )
    except Exception as e:
        # 自动生成失败不影响订单完成流程，只记录日志
        import traceback
        print(f'[WARN] 自动生成应收账款失败: {e}\n{traceback.format_exc()}')


# ==================== 运输跟踪 ====================

@bp.route('/transport-records', methods=['GET'])
@login_required
def get_transport_records():
    """获取运输跟踪记录"""
    order_id = request.args.get('order_id')
    if not order_id:
        return error_response('缺少 order_id 参数')

    records = TransportRecord.query.filter_by(
        order_id=int(order_id)
    ).order_by(TransportRecord.recorded_at.asc()).all()

    return success_response([r.to_dict() for r in records])


@bp.route('/transport-records', methods=['POST'])
@login_required
def create_transport_record():
    """添加运输跟踪记录"""
    data = request.get_json()

    if not data or not data.get('order_id') or not data.get('status'):
        return error_response('订单ID和状态不能为空')

    order = Order.query.get_or_404(data['order_id'])

    record = TransportRecord(
        order_id=order.id,
        status=data['status'],
        location=data.get('location', ''),
        description=data.get('description', ''),
        recorded_by=current_user.id,
        recorded_at=beijing_now()
    )

    db.session.add(record)

    # 自动更新订单状态
    status_map = {
        'departed': 'in_transit',
        'in_transit': 'in_transit',
        'rest': 'in_transit',
        'arrived': 'arrived',
        'unloading': 'arrived',
        'signed': 'signed'
    }
    if data['status'] in status_map:
        order.status = status_map[data['status']]
        if data['status'] in ('arrived', 'signed') and not order.actual_arrival:
            order.actual_arrival = beijing_now()
        if data['status'] == 'signed':
            order.status = 'completed'

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_order',
        action='add_record',
        target_type='TransportRecord',
        target_id=record.id,
        description=f'添加运输跟踪记录：{record.description}'
    )
    db.session.commit()

    # 评分 + 通知
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                    module='transport_order', action='update_status')
    broadcast_order_status('transport_order', order.id, order.status, current_user.group_id)

    return success_response(record.to_dict(), '跟踪记录已添加')


# ==================== 运费查询 ====================

@bp.route('/orders/<int:order_id>/freight', methods=['GET'])
@login_required
def get_freight(order_id):
    """查看运费明细"""
    order = Order.query.get_or_404(order_id)

    # 简易运费计算逻辑
    freight = 0
    if order.weight:
        freight += float(order.weight) * 0.005  # 5元/千克
    if order.volume:
        freight += float(order.volume) * 100     # 100元/立方米

    return success_response({
        'order_id': order.id,
        'order_no': order.order_no,
        'weight': float(order.weight) if order.weight else None,
        'volume': float(order.volume) if order.volume else None,
        'calculated_freight': round(freight, 2),
        'recorded_freight': float(order.freight_amount) if order.freight_amount else None
    })


# ==================== 运输异常 ====================

@bp.route('/exceptions', methods=['GET'])
@login_required
def get_exceptions():
    """获取运输异常列表"""
    order_id = request.args.get('order_id')
    handle_status = request.args.get('handle_status')
    exception_type = request.args.get('exception_type')

    query = TransportException.query

    if order_id:
        query = query.filter_by(order_id=int(order_id))
    if handle_status:
        query = query.filter_by(handle_status=handle_status)
    if exception_type:
        query = query.filter_by(exception_type=exception_type)

    exceptions = query.order_by(TransportException.reported_at.desc()).all()
    return success_response([e.to_dict() for e in exceptions])


@bp.route('/exceptions', methods=['POST'])
@login_required
def create_exception():
    """登记运输异常"""
    data = request.get_json()

    if not data or not data.get('order_id') or not data.get('exception_type') or not data.get('description'):
        return error_response('订单ID、异常类型和描述不能为空')

    order = Order.query.get(data['order_id'])
    if not order:
        return error_response('订单不存在')

    exception = TransportException(
        order_id=order.id,
        exception_type=data['exception_type'],
        severity=data.get('severity', 'normal'),
        location=data.get('location', ''),
        description=data['description'],
        image=data.get('image', ''),
        reported_by=current_user.id,
        handle_status='pending'
    )

    db.session.add(exception)
    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_exception',
        action='create',
        target_type='TransportException',
        target_id=exception.id,
        description=f'登记运输异常：{exception.exception_type} - {order.order_no}'
    )
    db.session.commit()

    # 评分
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                   module='transport_exception', action='create')

    return success_response(exception.to_dict(), '异常登记成功')


@bp.route('/exceptions/<int:exception_id>', methods=['GET'])
@login_required
def get_exception(exception_id):
    """获取异常详情"""
    exception = TransportException.query.get_or_404(exception_id)
    return success_response(exception.to_dict())


@bp.route('/exceptions/<int:exception_id>', methods=['PUT'])
@login_required
def update_exception(exception_id):
    """更新异常处理状态"""
    exception = TransportException.query.get_or_404(exception_id)
    data = request.get_json() or {}

    # 更新处理状态
    if 'handle_status' in data:
        old_status = exception.handle_status
        exception.handle_status = data['handle_status']
        if data['handle_status'] == 'resolved' and not exception.handled_at:
            exception.handled_at = beijing_now()
            exception.handled_by = current_user.id

    if 'handle_note' in data:
        exception.handle_note = data['handle_note']

    if 'severity' in data:
        exception.severity = data['severity']

    if 'image' in data:
        exception.image = data['image']

    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_exception',
        action='update',
        target_type='TransportException',
        target_id=exception.id,
        description=f'更新异常处理状态：{exception.handle_status}'
    )
    db.session.commit()

    # 评分
    score_operation(user_id=current_user.id, group_id=current_user.group_id,
                   module='transport_exception', action='update')

    return success_response(exception.to_dict(), '异常处理状态已更新')


@bp.route('/exceptions/<int:exception_id>', methods=['DELETE'])
@login_required
def delete_exception(exception_id):
    """删除异常记录"""
    exception = TransportException.query.get_or_404(exception_id)

    # 只能删除待处理的异常
    if exception.handle_status != 'pending':
        return error_response('只能删除待处理的异常')

    db.session.delete(exception)
    db.session.commit()

    # 记录操作日志
    log_operation(
        user_id=current_user.id,
        group_id=current_user.group_id,
        module='transport_exception',
        action='delete',
        target_type='TransportException',
        target_id=exception.id,
        description=f'删除异常记录'
    )
    db.session.commit()

    return success_response(message='删除成功')
