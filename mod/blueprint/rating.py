"""
客服评价API
"""
from flask import Blueprint, request, jsonify
from exts import db
from mod.mysql.models import ServiceRating, Service, Queue, Visitor
from datetime import datetime, timedelta
import log

logger = log.get_logger(__name__)

rating_bp = Blueprint('rating', __name__, url_prefix='/api/rating')


@rating_bp.route('/check-eligible', methods=['POST'])
def check_rating_eligible():
    """
    检查访客是否可以评价客服
    24小时内只能评价一次
    """
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        service_id = data.get('service_id')
        
        if not visitor_id or not service_id:
            return jsonify({
                'code': -1,
                'msg': '缺少必要参数'
            }), 400
        
        # 查询最近一次评价
        last_rating = ServiceRating.query.filter_by(
            visitor_id=visitor_id,
            service_id=service_id
        ).order_by(ServiceRating.created_at.desc()).first()
        
        # 24小时限制检查
        if last_rating:
            time_diff = datetime.now() - last_rating.created_at
            if time_diff < timedelta(hours=24):
                remaining_hours = 24 - (time_diff.total_seconds() / 3600)
                return jsonify({
                    'code': 0,
                    'data': {
                        'eligible': False,
                        'reason': f'您已评价过该客服，请在{int(remaining_hours)}小时后再次评价',
                        'last_rating_time': last_rating.created_at.isoformat(),
                        'remaining_hours': round(remaining_hours, 1)
                    }
                })
        
        # 可以评价
        return jsonify({
            'code': 0,
            'data': {
                'eligible': True,
                'reason': '可以评价'
            }
        })
        
    except Exception as e:
        logger.error(f'检查评价资格失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@rating_bp.route('/submit', methods=['POST'])
def submit_rating():
    """
    提交评价
    """
    try:
        data = request.get_json()
        visitor_id = data.get('visitor_id')
        service_id = data.get('service_id')
        business_id = data.get('business_id', 1)
        rating = data.get('rating')  # 1-5星
        comment = data.get('comment', '')
        tags = data.get('tags', [])  # 标签列表
        
        # 参数验证
        if not visitor_id or not service_id or not rating:
            return jsonify({
                'code': -1,
                'msg': '缺少必要参数'
            }), 400
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({
                'code': -1,
                'msg': '评分必须是1-5之间的整数'
            }), 400
        
        # 检查24小时限制
        last_rating = ServiceRating.query.filter_by(
            visitor_id=visitor_id,
            service_id=service_id
        ).order_by(ServiceRating.created_at.desc()).first()
        
        if last_rating:
            time_diff = datetime.now() - last_rating.created_at
            if time_diff < timedelta(hours=24):
                remaining_hours = 24 - (time_diff.total_seconds() / 3600)
                return jsonify({
                    'code': -1,
                    'msg': f'评价过于频繁，请在{int(remaining_hours)}小时后再试'
                }), 429
        
        # 获取访客信息
        visitor = Visitor.query.filter_by(visitor_id=visitor_id).first()
        visitor_name = visitor.visitor_name if visitor else '访客'
        visitor_ip = visitor.ip if visitor else request.remote_addr
        
        # 查找队列ID
        queue = Queue.query.filter_by(
            visitor_id=visitor_id,
            service_id=service_id
        ).order_by(Queue.updated_at.desc()).first()
        queue_id = queue.qid if queue else None
        
        # 创建评价记录
        new_rating = ServiceRating(
            visitor_id=visitor_id,
            service_id=service_id,
            business_id=business_id,
            queue_id=queue_id,
            rating=rating,
            comment=comment.strip() if comment else None,
            tags=','.join(tags) if tags else None,
            visitor_name=visitor_name,
            visitor_ip=visitor_ip
        )
        
        db.session.add(new_rating)
        db.session.commit()
        
        logger.info(f"✅ 访客{visitor_id}评价客服{service_id}: {rating}星")
        
        return jsonify({
            'code': 0,
            'msg': '评价提交成功，感谢您的反馈！',
            'data': {
                'rating_id': new_rating.id,
                'rating': rating
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'提交评价失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': '提交失败，请稍后重试'}), 500


@rating_bp.route('/list', methods=['GET'])
def get_ratings():
    """
    获取评价列表（可选：按客服ID筛选）
    """
    try:
        service_id = request.args.get('service_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = ServiceRating.query
        
        if service_id:
            query = query.filter_by(service_id=service_id)
        
        pagination = query.order_by(
            ServiceRating.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        ratings_list = []
        for rating in pagination.items:
            rating_dict = rating.to_dict()
            
            # 获取客服信息
            service = Service.query.get(rating.service_id)
            if service:
                rating_dict['service_name'] = service.nick_name
            
            ratings_list.append(rating_dict)
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'ratings': ratings_list,
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages
            }
        })
        
    except Exception as e:
        logger.error(f'获取评价列表失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@rating_bp.route('/stats/<int:service_id>', methods=['GET'])
def get_rating_stats(service_id):
    """
    获取客服评价统计
    """
    try:
        # 获取所有评价
        ratings = ServiceRating.query.filter_by(service_id=service_id).all()
        
        if not ratings:
            return jsonify({
                'code': 0,
                'data': {
                    'total_count': 0,
                    'average_rating': 0,
                    'rating_distribution': {
                        '5': 0, '4': 0, '3': 0, '2': 0, '1': 0
                    }
                }
            })
        
        # 计算统计数据
        total_count = len(ratings)
        total_score = sum(r.rating for r in ratings)
        average_rating = round(total_score / total_count, 2)
        
        # 评分分布
        rating_distribution = {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
        for r in ratings:
            rating_distribution[str(r.rating)] += 1
        
        return jsonify({
            'code': 0,
            'data': {
                'total_count': total_count,
                'average_rating': average_rating,
                'rating_distribution': rating_distribution
            }
        })
        
    except Exception as e:
        logger.error(f'获取评价统计失败: {e}')
        return jsonify({'code': -1, 'msg': str(e)}), 500


@rating_bp.route('/statistics', methods=['GET'])
def get_overall_statistics():
    """
    获取整体评价统计（不区分客服）
    """
    try:
        # 可选参数
        days = request.args.get('days', type=int)
        service_id = request.args.get('service_id', type=int)
        
        # 构建查询
        query = ServiceRating.query
        
        # 筛选客服
        if service_id:
            query = query.filter_by(service_id=service_id)
        
        # 筛选时间范围
        if days:
            from datetime import datetime, timedelta
            start_date = datetime.now() - timedelta(days=days)
            query = query.filter(ServiceRating.created_at >= start_date)
        
        ratings = query.all()
        
        if not ratings:
            return jsonify({
                'code': 0,
                'data': {
                    'total_count': 0,
                    'avg_score': 0,
                    'satisfaction_rate': 0,
                    'level_distribution': {
                        '5': 0, '4': 0, '3': 0, '2': 0, '1': 0
                    }
                }
            })
        
        # 计算统计数据
        total_count = len(ratings)
        total_score = sum(r.rating for r in ratings)
        avg_score = total_score / total_count
        
        # 评分分布
        level_distribution = {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
        for r in ratings:
            level_distribution[str(r.rating)] += 1
        
        # 满意度（4星及以上视为满意）
        satisfied_count = level_distribution['5'] + level_distribution['4']
        satisfaction_rate = (satisfied_count / total_count * 100) if total_count > 0 else 0
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'total_count': total_count,
                'avg_score': round(avg_score, 2),
                'satisfaction_rate': round(satisfaction_rate, 2),
                'level_distribution': level_distribution
            }
        })
        
    except Exception as e:
        logger.error(f'获取整体评价统计失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500


@rating_bp.route('/ranking', methods=['GET'])
def get_rating_ranking():
    """
    获取客服评价排行榜
    """
    try:
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # 筛选时间范围
        from datetime import datetime, timedelta
        start_date = datetime.now() - timedelta(days=days)
        
        # 查询评价数据
        ratings = ServiceRating.query.filter(
            ServiceRating.created_at >= start_date
        ).all()
        
        # 按客服ID分组统计
        service_stats = {}
        for rating in ratings:
            service_id = rating.service_id
            if service_id not in service_stats:
                service_stats[service_id] = {
                    'service_id': service_id,
                    'total_count': 0,
                    'total_score': 0,
                    'rating_distribution': {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
                }
            
            service_stats[service_id]['total_count'] += 1
            service_stats[service_id]['total_score'] += rating.rating
            service_stats[service_id]['rating_distribution'][str(rating.rating)] += 1
        
        # 计算平均分并获取客服信息
        ranking = []
        for service_id, stats in service_stats.items():
            service = Service.query.get(service_id)
            if service:
                avg_score = stats['total_score'] / stats['total_count']
                satisfied_count = stats['rating_distribution']['5'] + stats['rating_distribution']['4']
                satisfaction_rate = (satisfied_count / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
                
                ranking.append({
                    'service_id': service_id,
                    'service_name': service.nick_name,
                    'total_count': stats['total_count'],
                    'avg_score': round(avg_score, 2),
                    'satisfaction_rate': round(satisfaction_rate, 2),
                    'level_distribution': stats['rating_distribution']
                })
        
        # 按平均分降序排序
        ranking.sort(key=lambda x: x['avg_score'], reverse=True)
        
        # 限制返回数量
        ranking = ranking[:limit]
        
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': ranking
        })
        
    except Exception as e:
        logger.error(f'获取评价排行榜失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e)}), 500

