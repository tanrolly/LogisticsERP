"""
审批记录模型

统一的审批操作记录表，记录所有业务模块的审批动作（提交/通过/驳回/退回）。
支持按 target_type + target_id 查询完整的审批历史。
"""
from app import db
from .base import BaseModel


class ApprovalRecord(BaseModel):
    """审批记录表"""
    __tablename__ = 'approval_records'

    # 关联的业务对象
    target_type = db.Column(db.String(50), nullable=False, index=True,
                            comment='业务类型: purchase_request/transport_order/purchase_contract/transport_contract')
    target_id = db.Column(db.Integer, nullable=False, index=True,
                          comment='业务对象ID')

    # 审批动作
    action = db.Column(db.String(20), nullable=False,
                       comment='操作: submit/approve/reject/return')

    # 审批意见
    comment = db.Column(db.Text, comment='审批意见')

    # 操作人（冗余存储姓名，避免多次join）
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                            comment='操作人ID')
    operator_name = db.Column(db.String(50), comment='操作人姓名')

    # 关联关系
    operator = db.relationship('User', backref='approval_records', lazy=True)

    def to_dict(self):
        data = super().to_dict()
        # action 显示名映射
        action_names = {
            'submit': '提交',
            'approve': '审批通过',
            'reject': '驳回',
            'return': '退回修改'
        }
        data['action_name'] = action_names.get(self.action, self.action)
        return data
