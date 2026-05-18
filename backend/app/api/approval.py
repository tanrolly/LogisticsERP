"""
审批记录查询 API

提供统一的审批历史查询接口，支持按业务类型和ID筛选。
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.models.approval import ApprovalRecord

bp = Blueprint('approval', __name__)


@bp.route('/approval-records', methods=['GET'])
@login_required
def get_approval_records():
    """查询审批记录

    参数:
        target_type - 业务类型 (purchase_request/transport_order/purchase_contract/transport_contract)
        target_id - 业务对象ID
    """
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id', type=int)

    query = ApprovalRecord.query

    if target_type:
        query = query.filter_by(target_type=target_type)
    if target_id:
        query = query.filter_by(target_id=target_id)

    records = query.order_by(ApprovalRecord.created_at.asc()).all()

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': [r.to_dict() for r in records]
    })


@bp.route('/approval-records/<int:record_id>', methods=['GET'])
@login_required
def get_approval_record(record_id):
    """获取审批记录详情"""
    record = ApprovalRecord.query.get(record_id)
    if not record:
        return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': record.to_dict()
    })
