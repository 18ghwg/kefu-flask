#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评价系统业务逻辑
负责会话评价、统计分析等功能
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from exts import db
from mod.mysql.models import Comment, Queue, Visitor, Service


class CommentService:
    """评价服务"""
    
    @staticmethod
    def submit_comment(queue_id, visitor_id, service_id, level, content=''):
        """
        提交评价
        
        Args:
            queue_id: 队列ID
            visitor_id: 访客ID
            service_id: 客服ID
            level: 评分等级（1-5星）
            content: 评价内容
        
        Returns:
            dict: 提交结果
        """
        try:
            # 验证评分等级
            if not 1 <= level <= 5:
                return {'code': -1, 'msg': '评分必须在1-5之间'}
            
            # 检查会话是否存在
            queue = Queue.query.get(queue_id)
            if not queue:
                return {'code': -1, 'msg': '会话不存在'}
            
            # 检查会话是否已结束
            if queue.state != 'complete':
                return {'code': -1, 'msg': '会话未结束，无法评价'}
            
            # 检查是否已评价
            existing_comment = Comment.query.filter_by(
                queue_id=queue_id
            ).first()
            
            if existing_comment:
                return {'code': -1, 'msg': '该会话已评价'}
            
            # 创建评价
            comment = Comment(
                queue_id=queue_id,
                visiter_id=visitor_id,
                service_id=service_id,
                level=level,
                content=content,
                timestamp=datetime.now()
            )
            
            db.session.add(comment)
            db.session.commit()
            
            return {
                'code': 0,
                'msg': '评价提交成功',
                'data': {
                    'comment_id': comment.id,
                    'level': level
                }
            }
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'提交评价失败: {str(e)}'}
    
    @staticmethod
    def get_comment_list(business_id, service_id=None, level=None, 
                        start_date=None, end_date=None, page=1, per_page=20):
        """
        获取评价列表
        
        Args:
            business_id: 商户ID
            service_id: 客服ID（可选）
            level: 评分等级（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            page: 页码
            per_page: 每页数量
        
        Returns:
            dict: 评价列表
        """
        try:
            # 构建查询（通过Queue关联business_id）
            query = Comment.query.join(
                Queue, Comment.queue_id == Queue.qid
            ).filter(Queue.business_id == business_id)
            
            if service_id:
                query = query.filter(Comment.service_id == service_id)
            
            if level:
                query = query.filter(Comment.level == level)
            
            if start_date:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Comment.timestamp >= start)
            
            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Comment.timestamp < end)
            
            # 排序和分页
            query = query.order_by(Comment.timestamp.desc())
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # 组装数据
            comment_list = []
            for comment in pagination.items:
                visitor = Visitor.query.filter_by(visitor_id=comment.visiter_id).first()
                service = Service.query.filter_by(service_id=comment.service_id).first()
                
                comment_list.append({
                    'id': comment.id,
                    'queue_id': comment.queue_id,
                    'visitor_id': comment.visiter_id,
                    'visitor_name': visitor.visitor_name if visitor else '未知',
                    'service_id': comment.service_id,
                    'service_name': service.nick_name if service else '未知',
                    'level': comment.level,
                    'content': comment.content,
                    'timestamp': comment.timestamp.isoformat()
                })
            
            return {
                'code': 0,
                'data': {
                    'list': comment_list,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'page': page
                }
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取评价列表失败: {str(e)}'}
    
    @staticmethod
    def get_comment_statistics(business_id, service_id=None, days=7):
        """
        获取评价统计
        
        Args:
            business_id: 商户ID
            service_id: 客服ID（可选）
            days: 统计天数
        
        Returns:
            dict: 统计数据
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 构建查询
            query = Comment.query.join(
                Queue, Comment.queue_id == Queue.qid
            ).filter(
                Queue.business_id == business_id,
                Comment.timestamp >= start_date
            )
            
            if service_id:
                query = query.filter(Comment.service_id == service_id)
            
            # 获取所有评价
            comments = query.all()
            
            if not comments:
                return {
                    'code': 0,
                    'data': {
                        'total_count': 0,
                        'avg_score': 0,
                        'satisfaction_rate': 0,
                        'level_distribution': {
                            '5': 0, '4': 0, '3': 0, '2': 0, '1': 0
                        }
                    }
                }
            
            # 计算统计数据
            total_count = len(comments)
            avg_score = sum([c.level for c in comments]) / total_count
            satisfaction_rate = len([c for c in comments if c.level >= 4]) / total_count * 100
            
            # 评分分布
            level_distribution = {
                '5': len([c for c in comments if c.level == 5]),
                '4': len([c for c in comments if c.level == 4]),
                '3': len([c for c in comments if c.level == 3]),
                '2': len([c for c in comments if c.level == 2]),
                '1': len([c for c in comments if c.level == 1])
            }
            
            return {
                'code': 0,
                'data': {
                    'total_count': total_count,
                    'avg_score': round(avg_score, 2),
                    'satisfaction_rate': round(satisfaction_rate, 2),
                    'level_distribution': level_distribution
                }
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取统计数据失败: {str(e)}'}
    
    @staticmethod
    def get_service_comment_ranking(business_id, days=7, limit=10):
        """
        获取客服评价排行
        
        Args:
            business_id: 商户ID
            days: 统计天数
            limit: 返回数量
        
        Returns:
            dict: 排行数据
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 查询所有客服
            services = Service.query.filter_by(business_id=business_id).all()
            
            ranking_list = []
            for service in services:
                # 获取该客服的评价
                comments = Comment.query.join(
                    Queue, Comment.queue_id == Queue.qid
                ).filter(
                    Queue.business_id == business_id,
                    Comment.service_id == service.service_id,
                    Comment.timestamp >= start_date
                ).all()
                
                if not comments:
                    continue
                
                # 计算统计
                total_count = len(comments)
                avg_score = sum([c.level for c in comments]) / total_count
                satisfaction_rate = len([c for c in comments if c.level >= 4]) / total_count * 100
                
                ranking_list.append({
                    'service_id': service.service_id,
                    'service_name': service.nick_name,
                    'total_count': total_count,
                    'avg_score': round(avg_score, 2),
                    'satisfaction_rate': round(satisfaction_rate, 2)
                })
            
            # 按平均分排序
            ranking_list.sort(key=lambda x: x['avg_score'], reverse=True)
            
            return {
                'code': 0,
                'data': ranking_list[:limit]
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取排行失败: {str(e)}'}
    
    @staticmethod
    def get_comment_trend(business_id, days=7):
        """
        获取评价趋势
        
        Args:
            business_id: 商户ID
            days: 统计天数
        
        Returns:
            dict: 趋势数据
        """
        try:
            trend_data = []
            
            for i in range(days):
                date = datetime.now() - timedelta(days=days-i-1)
                start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1)
                
                # 当天评价
                comments = Comment.query.join(
                    Queue, Comment.queue_id == Queue.qid
                ).filter(
                    Queue.business_id == business_id,
                    Comment.timestamp >= start,
                    Comment.timestamp < end
                ).all()
                
                if comments:
                    avg_score = sum([c.level for c in comments]) / len(comments)
                    count = len(comments)
                else:
                    avg_score = 0
                    count = 0
                
                trend_data.append({
                    'date': start.strftime('%Y-%m-%d'),
                    'count': count,
                    'avg_score': round(avg_score, 2)
                })
            
            return {
                'code': 0,
                'data': trend_data
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取趋势失败: {str(e)}'}
    
    @staticmethod
    def delete_comment(comment_id):
        """
        删除评价（管理员功能）
        
        Args:
            comment_id: 评价ID
        
        Returns:
            dict: 删除结果
        """
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return {'code': -1, 'msg': '评价不存在'}
            
            db.session.delete(comment)
            db.session.commit()
            
            return {'code': 0, 'msg': '删除成功'}
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'删除失败: {str(e)}'}


# 创建单例实例
comment_service = CommentService()

