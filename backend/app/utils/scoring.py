"""自动评分引擎"""
from app import db
from app.models.collab import OperationLog, Score
from datetime import datetime


# 评分规则配置
SCORING_RULES = {
    'purchase_request': {
        'create': 10,       # 正确创建采购申请
        'approve': 5,       # 审批操作
        'reject': 5,        # 驳回操作
        'return': 5,        # 退回修改
        'resubmit': 3,      # 重新提交
    },
    'purchase_order': {
        'create': 15,       # 创建采购订单（关联申请+供应商）
        'confirm': 5,       # 确认订单
        'complete': 10,     # 完成订单
    },
    'transport_order': {
        'create': 15,       # 创建运输订单
        'approve': 5,       # 审核订单
        'reject': 5,        # 驳回订单
        'return': 5,        # 退回修改
        'resubmit': 3,      # 重新提交
        'dispatch': 15,     # 车辆调度
        'update_status': 5, # 状态更新
        'add_record': 5,     # 添加运输记录
        'complete': 10,     # 完成签收
    },
    'inbound_order': {
        'create': 10,       # 创建入库单
        'shelve': 15,       # 上架操作
        'complete': 10,     # 完成入库
    },
    'outbound_order': {
        'create': 10,       # 创建出库单
        'pick': 15,         # 拣货操作
        'ship': 10,         # 发货操作
        'complete': 10,     # 完成出库
    },
    'stock_count': {
        'create': 10,       # 创建盘点
        'count': 15,        # 执行盘点
        'reconcile': 10,    # 调整差异
    },
    'finance': {
        'create_payable': 10,      # 生成应付账款
        'record_payment': 15,      # 记录付款
        'create_receivable': 10,   # 生成应收账款
        'record_receipt': 15,      # 记录收款
        'complete_payable': 10,    # 完成付款（付清）
        'complete_receivable': 10, # 完成收款（收齐）
    },
    'contract': {
        'create_purchase': 10,       # 创建采购合同
        'approve_purchase': 5,       # 审批采购合同
        'create_transport': 10,       # 创建运输合同
        'approve_transport': 5,       # 审批运输合同
        'return': 5,                  # 退回合同
        'terminate': 5,              # 终止合同
    },
    'transport_exception': {
        'create': 10,              # 登记运输异常
        'update': 5,               # 更新异常处理状态
        'delete': -5,              # 删除异常（扣分）
    },
    'customer': {
        'create': 10,              # 创建客户
        'update': 5,               # 更新客户信息
        'delete': -5,              # 删除客户（扣分）
    }
}

# 扣分规则
DEDUCTION_RULES = {
    'operation_error': -5,     # 操作错误（如字段不合规）
    'timeout': -3,             # 操作超时
    'sequence_error': -10,     # 流程顺序错误
    'data_inconsistency': -5,  # 数据不一致
}

# 加分规则
BONUS_RULES = {
    'fast_completion': 10,     # 高效完成（提前30%以上时间）
    'proactive_action': 5,     # 主动发现问题
    'perfect_accuracy': 15,    # 零差错完成
}


def score_operation(user_id, group_id, module, action, is_correct=True, extra_data=None):
    """
    为用户的操作进行评分

    Args:
        user_id: 用户ID
        group_id: 小组ID（可为None）
        module: 模块名（purchase_request/purchase_order/...）
        action: 操作名（create/approve/...）
        is_correct: 操作是否正确
        extra_data: 额外数据

    Returns:
        Score 实例
    """
    points = 0

    if is_correct:
        # 获取该模块+操作的评分
        module_rules = SCORING_RULES.get(module, {})
        points = module_rules.get(action, 5)  # 默认5分
    else:
        points = DEDUCTION_RULES.get('operation_error', -5)

    # 创建评分记录
    score = Score(
        user_id=user_id,
        group_id=group_id,
        module=module,
        action=action,
        points=points,
        is_correct=is_correct,
        extra_data=extra_data or {}
    )
    db.session.add(score)
    db.session.commit()

    return score


def calculate_group_score(group_id):
    """
    计算小组总分和各维度评分

    Returns:
        dict: { total, operation_score, completeness_score, efficiency_score, details }
    """
    scores = Score.query.filter_by(group_id=group_id).all()

    if not scores:
        return {
            'total': 0,
            'operation_score': 0,
            'completeness_score': 0,
            'efficiency_score': 0,
            'member_count': 0,
            'operation_count': 0,
            'error_count': 0,
            'details': []
        }

    # 操作正确性评分（正确操作的得分总和）
    operation_score = sum(s.points for s in scores if s.points > 0)

    # 错误次数
    error_count = sum(1 for s in scores if not s.is_correct)

    # 参与成员数
    member_ids = set(s.user_id for s in scores)

    # 流程完整性评分（各模块是否都有操作记录）
    completed_modules = set(s.module for s in scores if s.is_correct)
    all_modules = set(SCORING_RULES.keys())
    completeness_score = len(completed_modules) / len(all_modules) * 50 if all_modules else 0

    # 效率评分（操作次数/错误次数比）
    total_operations = len(scores)
    if total_operations > 0:
        efficiency_ratio = (total_operations - error_count) / total_operations
        efficiency_score = efficiency_ratio * 50
    else:
        efficiency_score = 0

    total = operation_score + completeness_score + efficiency_score

    return {
        'total': round(total, 1),
        'operation_score': round(operation_score, 1),
        'completeness_score': round(completeness_score, 1),
        'efficiency_score': round(efficiency_score, 1),
        'member_count': len(member_ids),
        'operation_count': total_operations,
        'error_count': error_count,
        'details': [{
            'module': s.module,
            'action': s.action,
            'points': s.points,
            'is_correct': s.is_correct,
            'created_at': s.created_at.isoformat() if s.created_at else None
        } for s in scores]
    }


def calculate_user_score(user_id, group_id=None):
    """
    计算个人评分

    Returns:
        dict: 个人评分详情
    """
    query = Score.query.filter_by(user_id=user_id)
    if group_id:
        query = query.filter_by(group_id=group_id)
    scores = query.all()

    if not scores:
        return {
            'total': 0,
            'operation_score': 0,
            'error_count': 0,
            'operation_count': 0,
            'details': []
        }

    operation_score = sum(s.points for s in scores if s.points > 0)
    error_count = sum(1 for s in scores if not s.is_correct)

    return {
        'total': round(operation_score, 1),
        'operation_score': round(operation_score, 1),
        'error_count': error_count,
        'operation_count': len(scores),
        'details': [{
            'module': s.module,
            'action': s.action,
            'points': s.points,
            'is_correct': s.is_correct,
            'created_at': s.created_at.isoformat() if s.created_at else None
        } for s in scores]
    }
