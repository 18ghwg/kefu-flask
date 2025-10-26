"""
机器人知识库API
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from mod.mysql.ModuleClass.RobotServiceClass import RobotService
from mod.decorators.log_operation import log_operation
import log

robot_bp = Blueprint('robot', __name__)
logger = log.get_logger(__name__)


@robot_bp.route('/list', methods=['GET'])
@login_required
def get_knowledge_list():
    """获取知识库列表"""
    try:
        # 获取参数
        keyword = request.args.get('keyword', '')
        type = request.args.get('type', '')  # faq, keyword, 或空（全部）
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 获取商户ID
        business_id = current_user.business_id
        
        # 查询知识库
        pagination = RobotService.get_knowledge_list(
            business_id=business_id,
            keyword=keyword,
            type=type if type else None,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'list': [item.to_dict() for item in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages
            }
        })
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500


@robot_bp.route('/add', methods=['POST'])
@login_required
@log_operation('robot', 'create', '添加知识库：{keyword}')
def add_knowledge():
    """添加知识库"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('keyword') or not data.get('reply'):
            return jsonify({'code': -1, 'msg': '关键词和回复内容不能为空'}), 400
        
        # 获取商户ID
        business_id = current_user.business_id
        
        # 添加知识库
        robot = RobotService.add_knowledge(
            business_id=business_id,
            keyword=data['keyword'],
            reply=data['reply'],
            sort=data.get('sort', 0),
            status=data.get('status', 1),
            type=data.get('type', 'keyword')  # 默认为智能关键词
        )
        
        logger.info(f"添加知识库成功: {robot.keyword} (类型: {robot.type})")
        
        return jsonify({
            'code': 0,
            'msg': '添加成功',
            'data': robot.to_dict()
        })
    except Exception as e:
        logger.error(f"添加知识库失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500


@robot_bp.route('/update/<int:robot_id>', methods=['PUT'])
@login_required
@log_operation('robot', 'update', '更新知识库 ID:{robot_id}')
def update_knowledge(robot_id):
    """更新知识库"""
    try:
        data = request.get_json()
        
        # 更新知识库
        robot = RobotService.update_knowledge(
            robot_id=robot_id,
            keyword=data.get('keyword'),
            reply=data.get('reply'),
            sort=data.get('sort'),
            status=data.get('status'),
            type=data.get('type')  # 支持更新类型
        )
        
        if not robot:
            return jsonify({'code': -1, 'msg': '知识库不存在'}), 404
        
        logger.info(f"更新知识库成功: {robot.keyword} (类型: {robot.type})")
        
        return jsonify({
            'code': 0,
            'msg': '更新成功',
            'data': robot.to_dict()
        })
    except Exception as e:
        logger.error(f"更新知识库失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500


@robot_bp.route('/delete/<int:robot_id>', methods=['DELETE'])
@login_required
@log_operation('robot', 'delete', '删除知识库 ID:{robot_id}')
def delete_knowledge(robot_id):
    """删除知识库"""
    try:
        success = RobotService.delete_knowledge(robot_id)
        
        if not success:
            return jsonify({'code': -1, 'msg': '知识库不存在'}), 404
        
        logger.info(f"删除知识库成功: ID={robot_id}")
        
        return jsonify({
            'code': 0,
            'msg': '删除成功'
        })
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500


@robot_bp.route('/get/<int:robot_id>', methods=['GET'])
@login_required
def get_knowledge(robot_id):
    """获取知识库详情"""
    try:
        robot = RobotService.get_knowledge(robot_id)
        
        if not robot:
            return jsonify({'code': -1, 'msg': '知识库不存在'}), 404
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': robot.to_dict()
        })
    except Exception as e:
        logger.error(f"获取知识库详情失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500


@robot_bp.route('/match', methods=['POST'])
def match_keyword():
    """
    匹配关键词（无需登录，供聊天系统调用）
    """
    try:
        data = request.get_json()
        user_input = data.get('message', '')
        business_id = data.get('business_id', 1)
        
        if not user_input:
            return jsonify({'code': -1, 'msg': '消息内容不能为空'}), 400
        
        # 匹配关键词
        reply = RobotService.match_keyword_static(user_input, business_id)
        
        if reply:
            return jsonify({
                'code': 0,
                'msg': '匹配成功',
                'data': {
                    'matched': True,
                    'reply': reply
                }
            })
        else:
            return jsonify({
                'code': 0,
                'msg': '未匹配到',
                'data': {
                    'matched': False,
                    'reply': None
                }
            })
    except Exception as e:
        logger.error(f"关键词匹配失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500


@robot_bp.route('/welcome', methods=['GET'])
def get_welcome():
    """获取欢迎语"""
    try:
        business_id = request.args.get('business_id', 1, type=int)
        welcome = RobotService.get_welcome_message(business_id)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'welcome': welcome
            }
        })
    except Exception as e:
        logger.error(f"获取欢迎语失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500


@robot_bp.route('/import', methods=['POST'])
@login_required
def batch_import():
    """批量导入知识库"""
    try:
        data = request.get_json()
        data_list = data.get('data', [])
        
        if not data_list:
            return jsonify({'code': -1, 'msg': '导入数据不能为空'}), 400
        
        business_id = current_user.business_id
        
        count = RobotService.batch_import(business_id, data_list)
        
        logger.info(f"批量导入知识库成功: {count}条")
        
        return jsonify({
            'code': 0,
            'msg': f'成功导入{count}条知识库',
            'data': {
                'count': count
            }
        })
    except Exception as e:
        logger.error(f"批量导入失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500


@robot_bp.route('/export', methods=['GET'])
@login_required
def export_knowledge():
    """导出知识库"""
    try:
        business_id = current_user.business_id
        
        data = RobotService.export_knowledge(business_id)
        
        return jsonify({
            'code': 0,
            'msg': '导出成功',
            'data': data
        })
    except Exception as e:
        logger.error(f"导出知识库失败: {e}")
        return jsonify({'code': -1, 'msg': str(e)}), 500

