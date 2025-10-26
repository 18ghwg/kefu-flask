"""
常见问题API蓝图
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from mod.mysql.ModuleClass import question_service
from mod.decorators.log_operation import log_operation
import log

question_bp = Blueprint('question', __name__, url_prefix='/api/question')
logger = log.get_logger(__name__)


@question_bp.route('/list', methods=['GET'])
@login_required
def get_question_list():
    """获取常见问题列表"""
    try:
        business_id = current_user.business_id
        keyword = request.args.get('keyword', '')
        
        if keyword:
            questions = question_service.search_questions(business_id, keyword)
        else:
            questions = question_service.get_all_questions(business_id)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': [q.to_dict() for q in questions]
        })
        
    except Exception as e:
        logger.error(f'获取常见问题列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@question_bp.route('/create', methods=['POST'])
@login_required
@log_operation('question', 'create', '创建常见问题：{question}')
def create_question():
    """创建常见问题"""
    try:
        data = request.get_json()
        business_id = current_user.business_id
        
        question = data.get('question')
        answer = data.get('answer')
        keyword = data.get('keyword', '')
        answer_text = data.get('answer_text', '')
        sort = data.get('sort', 0)
        
        if not question or not answer:
            return jsonify({'code': -1, 'msg': '问题和答案不能为空'}), 400
        
        new_question = question_service.create_question(
            business_id=business_id,
            question=question,
            answer=answer,
            keyword=keyword,
            answer_text=answer_text,
            sort=sort
        )
        
        if new_question:
            return jsonify({
                'code': 0,
                'msg': '创建成功',
                'data': new_question.to_dict()
            })
        else:
            return jsonify({'code': -1, 'msg': '创建失败'}), 500
            
    except Exception as e:
        logger.error(f'创建常见问题失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@question_bp.route('/update/<int:qid>', methods=['PUT'])
@login_required
@log_operation('question', 'update', '更新常见问题 ID:{qid}')
def update_question(qid):
    """更新常见问题"""
    try:
        data = request.get_json()
        
        success = question_service.update_question(
            qid=qid,
            question=data.get('question'),
            answer=data.get('answer'),
            keyword=data.get('keyword'),
            answer_text=data.get('answer_text'),
            sort=data.get('sort'),
            status=data.get('status')
        )
        
        if success:
            return jsonify({'code': 0, 'msg': '更新成功'})
        else:
            return jsonify({'code': -1, 'msg': '更新失败'}), 500
            
    except Exception as e:
        logger.error(f'更新常见问题失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@question_bp.route('/delete/<int:qid>', methods=['DELETE'])
@login_required
@log_operation('question', 'delete', '删除常见问题 ID:{qid}')
def delete_question(qid):
    """删除常见问题"""
    try:
        success = question_service.delete_question(qid)
        
        if success:
            return jsonify({'code': 0, 'msg': '删除成功'})
        else:
            return jsonify({'code': -1, 'msg': '删除失败'}), 404
            
    except Exception as e:
        logger.error(f'删除常见问题失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@question_bp.route('/random', methods=['GET'])
def get_random_questions():
    """获取随机常见问题（用于机器人回复，无需登录）"""
    try:
        business_id = request.args.get('business_id', 1, type=int)
        limit = request.args.get('limit', 3, type=int)
        
        reply = question_service.get_random_questions(business_id, limit)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {'reply': reply}
        })
        
    except Exception as e:
        logger.error(f'获取随机常见问题失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500

