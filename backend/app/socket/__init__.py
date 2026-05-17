"""
WebSocket 事件处理器
需要在 app 工厂中调用 init_socket(socketio) 来注册事件
"""
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app.utils.time_helper import beijing_now


def init_socket(socketio):
    """注册所有 WebSocket 事件处理器"""

    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        if current_user.is_authenticated:
            join_room(f'user_{current_user.id}')
            emit('connected', {
                'user_id': current_user.id,
                'username': current_user.username,
                'real_name': current_user.real_name
            })
        else:
            emit('connected', {'user_id': None})

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开"""
        pass

    @socketio.on('join_group')
    def on_join_group(data):
        """加入协作小组房间"""
        group_id = data.get('group_id')
        if group_id and current_user.is_authenticated:
            room = f'group_{group_id}'
            join_room(room)
            emit('user_joined', {
                'user_id': current_user.id,
                'username': current_user.username,
                'real_name': current_user.real_name
            }, room=room, include_self=False)
            emit('join_success', {'group_id': group_id})

    @socketio.on('leave_group')
    def on_leave_group(data):
        """离开协作小组房间"""
        group_id = data.get('group_id')
        if group_id and current_user.is_authenticated:
            room = f'group_{group_id}'
            emit('user_left', {
                'user_id': current_user.id,
                'username': current_user.username,
                'real_name': current_user.real_name
            }, room=room, include_self=False)
            leave_room(room)

    @socketio.on('join_scene')
    def on_join_scene(data):
        """加入场景监控房间（教师端用）"""
        scene_id = data.get('scene_id')
        if scene_id:
            room = f'scene_{scene_id}'
            join_room(room)
            emit('join_success', {'scene_id': scene_id})


# ============ 业务事件广播辅助函数 ============

def _safe_emit(event, data, room, **kwargs):
    """安全广播：在 threading 模式下使用 start_background_task 避免阻塞 HTTP 请求"""
    from app.extensions import socketio
    try:
        socketio.start_background_task(socketio.emit, event, data, room=room, **kwargs)
    except Exception:
        pass  # 静默忽略广播失败


def broadcast_order_status(order_type, order_id, status, group_id=None, extra_data=None):
    """广播订单状态变更事件"""
    data = {
        'order_type': order_type,
        'order_id': order_id,
        'status': status,
        'operator_id': None,
        'operator_name': '系统',
        'timestamp': beijing_now().isoformat()
    }
    try:
        if current_user and current_user.is_authenticated:
            data['operator_id'] = current_user.id
            data['operator_name'] = current_user.real_name
    except Exception:
        pass

    if extra_data:
        data.update(extra_data)

    if group_id:
        _safe_emit('order_status_changed', data, room=f'group_{group_id}')

    # 同时广播给教师监控
    _safe_emit('order_status_changed', data, room='teacher_monitor')


def broadcast_todo(user_id, message, todo_type=None, reference_id=None):
    """发送待办任务通知给指定用户"""
    data = {
        'message': message,
        'todo_type': todo_type,
        'reference_id': reference_id,
        'timestamp': beijing_now().isoformat()
    }
    _safe_emit('todo_notification', data, room=f'user_{user_id}')


def broadcast_event(group_id, event_data):
    """广播突发事件给小组所有成员"""
    data = {
        **event_data,
        'timestamp': beijing_now().isoformat()
    }
    _safe_emit('event_injected', data, room=f'group_{group_id}')


def broadcast_group_progress(group_id, progress_data):
    """广播小组进度更新（教师监控用）"""
    data = {
        'group_id': group_id,
        **progress_data,
        'timestamp': beijing_now().isoformat()
    }
    _safe_emit('group_progress', data, room='teacher_monitor')
