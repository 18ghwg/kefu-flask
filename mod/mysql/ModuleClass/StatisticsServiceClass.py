#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据统计业务逻辑
负责各种统计数据的计算和查询
"""
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, and_
from exts import db, redis_client
from mod.mysql.models import Visitor, Queue, Chat, Service, Comment
import json
import log

logger = log.get_logger(__name__)


class StatisticsService:
    """数据统计服务类"""
    
    def __init__(self, business_id, service_id=None, level='service'):
        """
        初始化统计服务
        
        Args:
            business_id: 商户ID
            service_id: 客服ID（可选）
            level: 权限级别 (super_manager/manager/service)
        """
        self.business_id = business_id
        self.service_id = service_id
        self.level = level
    
    def _get_where_condition(self):
        """构建权限过滤条件"""
        if self.level == 'super_manager':
            # 超级管理员：查看整个商户
            return {'business_id': self.business_id}
        else:
            # 普通客服：只看自己的
            return {'service_id': self.service_id}
    
    def get_realtime_stats(self):
        """获取实时统计数据（带缓存）"""
        
        # 尝试从缓存获取
        cache_key = f"dashboard:{self.business_id}:realtime"
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # 1. 排队人数（service_id = 0）
        waiting_count = Queue.query.filter(
            Queue.business_id == self.business_id,
            Queue.state == 'normal',
            Queue.service_id == 0
        ).count()
        
        # 2. 正在咨询人数
        # ⚡ 统计活跃会话：5分钟内有消息互动的会话
        # 访客离线后，会话会被自动关闭（state='complete'），不会被计入
        from datetime import datetime, timedelta
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        
        chatting_count = Queue.query.filter(
            Queue.business_id == self.business_id,
            Queue.state == 'normal',
            Queue.service_id != 0,  # 已分配客服
            Queue.last_message_time >= five_minutes_ago  # 5分钟内有消息（更精确）
        ).count()
        
        # 3. 在线客服数（排除机器人）
        where = self._get_where_condition()
        online_services = Service.query.filter_by(
            **where,
            state='online'
        ).filter(
            Service.user_name != 'robot'  # ⚡ 排除机器人
        ).count()
        
        # 4. 接入总量（去重访客）- 多级优化策略
        # 优先级1: 尝试使用汇总表（最快）
        # 优先级2: 使用限制时间范围的查询（较快）
        try:
            # 尝试使用汇总表（如果存在）
            from sqlalchemy import text
            total_visitors = db.session.execute(text("""
                SELECT SUM(visitor_count) 
                FROM visitor_stats_cache 
                WHERE business_id = :business_id 
                AND stat_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """), {"business_id": self.business_id}).scalar() or 0
            logger.debug(f"✅ 使用汇总表查询访客数: {total_visitors}")
        except:
            # 汇总表不存在，使用优化后的查询
            thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
            total_visitors = db.session.query(
                func.count(distinct(Chat.visitor_id))
            ).filter(
                Chat.business_id == self.business_id,
                Chat.timestamp >= thirty_days_ago  # ✅ 限制时间范围
            ).scalar() or 0
            logger.debug(f"✅ 使用时间范围查询访客数: {total_visitors}")
        
        result = {
            'waiting_count': waiting_count,
            'chatting_count': chatting_count,
            'online_services': online_services,
            'total_visitors': total_visitors
        }
        
        # ✅ 增加缓存时间到300秒（5分钟），大幅减少查询频率
        if redis_client:
            redis_client.setex(cache_key, 300, json.dumps(result))
        
        return result
    
    def get_today_stats(self):
        """获取今日统计数据"""
        
        where = self._get_where_condition()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_timestamp = int(today_start.timestamp())
        now_timestamp = int(datetime.now().timestamp())
        
        # 1. 今日会话量
        today_chats = Chat.query.filter(
            and_(
                Chat.timestamp > today_timestamp,
                Chat.timestamp <= now_timestamp
            )
        ).filter_by(**where).count()
        
        # 2. 总会话量
        total_chats = Chat.query.filter_by(**where).count()
        
        # 3. 今日评价数
        today_comments = Comment.query.filter(
            Comment.add_time >= today_start
        ).filter_by(**where).count()
        
        # 4. 总评价数
        total_comments = Comment.query.filter_by(**where).count()
        
        return {
            'today_chats': today_chats,
            'total_chats': total_chats,
            'today_comments': today_comments,
            'total_comments': total_comments
        }
    
    def get_trend_stats(self, days=15):
        """获取趋势统计数据（带缓存）"""
        
        # 尝试从缓存获取
        cache_key = f"dashboard:{self.business_id}:trend:{days}d"
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        
        where = self._get_where_condition()
        result = []
        
        # 生成日期列表
        today = datetime.now().date()
        dates = [(today - timedelta(days=i)) for i in range(days)]
        dates.reverse()  # 从旧到新
        
        for date in dates:
            day_start = int(datetime.combine(date, datetime.min.time()).timestamp())
            day_end = day_start + 86400 - 1
            
            # 每日会话量
            chat_count = Chat.query.filter(
                and_(
                    Chat.timestamp >= day_start,
                    Chat.timestamp <= day_end
                )
            ).filter_by(**where).count()
            
            # 每日接入量（去重）
            line_count = db.session.query(
                func.count(distinct(Chat.visitor_id))
            ).filter(
                and_(
                    Chat.timestamp >= day_start,
                    Chat.timestamp <= day_end
                )
            ).filter_by(**where).scalar() or 0
            
            # 每日评价数
            day_start_dt = datetime.fromtimestamp(day_start)
            day_end_dt = datetime.fromtimestamp(day_end)
            comment_count = Comment.query.filter(
                and_(
                    Comment.add_time >= day_start_dt,
                    Comment.add_time <= day_end_dt
                )
            ).filter_by(**where).count()
            
            result.append({
                'date': date.strftime('%m-%d'),
                'chat': chat_count,
                'line': line_count,
                'comment': comment_count
            })
        
        # 缓存1小时
        if redis_client:
            redis_client.setex(cache_key, 3600, json.dumps(result))
        
        return result
    
    @staticmethod
    def get_overview_statistics(business_id, days=7):
        """
        获取概览统计数据
        
        Args:
            business_id: 商户ID
            days: 统计天数
        
        Returns:
            dict: 统计数据
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 访客数统计
            total_visitors = Visitor.query.filter_by(business_id=business_id).count()
            new_visitors = Visitor.query.filter(
                Visitor.business_id == business_id,
                Visitor.created_at >= start_date
            ).count()
            
            # 会话数统计
            total_sessions = Queue.query.filter_by(business_id=business_id).count()
            period_sessions = Queue.query.filter(
                Queue.business_id == business_id,
                Queue.created_at >= start_date
            ).count()
            completed_sessions = Queue.query.filter(
                Queue.business_id == business_id,
                Queue.state == 'complete',
                Queue.updated_at >= start_date
            ).count()
            
            # 消息数统计
            total_messages = db.session.query(func.count(Chat.cid)).join(
                Visitor, Chat.visitor_id == Visitor.visitor_id
            ).filter(Visitor.business_id == business_id).scalar()
            
            period_messages = db.session.query(func.count(Chat.cid)).join(
                Visitor, Chat.visitor_id == Visitor.visitor_id
            ).filter(
                Visitor.business_id == business_id,
                Chat.created_at >= start_date
            ).scalar()
            
            # 客服统计
            total_services = Service.query.filter_by(business_id=business_id).count()
            online_services = Service.query.filter_by(
                business_id=business_id,
                state='online'
            ).count()
            
            # 平均响应时间（简化计算）
            avg_response_time = 0  # TODO: 需要更复杂的逻辑计算
            
            # 满意度统计
            from mod.mysql.models import CommentDetail
            comments = Comment.query.filter(
                Comment.business_id == business_id,
                Comment.add_time >= start_date
            ).all()
            
            if comments:
                # 计算平均评分（从评价详情中获取）
                scores = []
                for comment in comments:
                    details = CommentDetail.query.filter_by(comment_id=comment.id).all()
                    if details:
                        avg = sum([d.score for d in details]) / len(details)
                        scores.append(avg)
                
                if scores:
                    avg_score = sum(scores) / len(scores)
                    satisfaction_rate = len([s for s in scores if s >= 4]) / len(scores) * 100
                else:
                    avg_score = 0
                    satisfaction_rate = 0
            else:
                avg_score = 0
                satisfaction_rate = 0
            
            return {
                'code': 0,
                'data': {
                    'visitors': {
                        'total': total_visitors,
                        'new': new_visitors
                    },
                    'sessions': {
                        'total': total_sessions,
                        'period': period_sessions,
                        'completed': completed_sessions
                    },
                    'messages': {
                        'total': total_messages,
                        'period': period_messages
                    },
                    'services': {
                        'total': total_services,
                        'online': online_services
                    },
                    'performance': {
                        'avg_response_time': avg_response_time,
                        'avg_score': round(avg_score, 2),
                        'satisfaction_rate': round(satisfaction_rate, 2)
                    }
                }
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取统计数据失败: {str(e)}'}
    
    @staticmethod
    def get_trend_data(business_id, days=7):
        """
        获取趋势数据
        
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
                
                # 当天会话数
                sessions = Queue.query.filter(
                    Queue.business_id == business_id,
                    Queue.created_at >= start,
                    Queue.created_at < end
                ).count()
                
                # 当天访客数
                visitors = Visitor.query.filter(
                    Visitor.business_id == business_id,
                    Visitor.created_at >= start,
                    Visitor.created_at < end
                ).count()
                
                # 当天消息数
                messages = db.session.query(func.count(Chat.cid)).join(
                    Visitor, Chat.visitor_id == Visitor.visitor_id
                ).filter(
                    Visitor.business_id == business_id,
                    Chat.created_at >= start,
                    Chat.created_at < end
                ).scalar()
                
                trend_data.append({
                    'date': start.strftime('%Y-%m-%d'),
                    'sessions': sessions,
                    'visitors': visitors,
                    'messages': messages
                })
            
            return {
                'code': 0,
                'data': trend_data
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取趋势数据失败: {str(e)}'}
    
    @staticmethod
    def get_service_performance(business_id, days=7):
        """
        获取客服工作量统计
        
        Args:
            business_id: 商户ID
            days: 统计天数
        
        Returns:
            dict: 客服绩效数据
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            services = Service.query.filter_by(business_id=business_id).all()
            
            performance_list = []
            for service in services:
                # 会话数
                session_count = Queue.query.filter(
                    Queue.service_id == service.service_id,
                    Queue.created_at >= start_date
                ).count()
                
                # 消息数
                message_count = Chat.query.filter(
                    Chat.service_id == service.service_id,
                    Chat.created_at >= start_date
                ).count()
                
                # 评价数和平均分
                from mod.mysql.models import CommentDetail
                comments = Comment.query.filter(
                    Comment.service_id == service.service_id,
                    Comment.add_time >= start_date
                ).all()
                
                # 计算平均分（从评价详情获取）
                comment_ids = [c.id for c in comments]
                if comment_ids:
                    details = CommentDetail.query.filter(
                        CommentDetail.comment_id.in_(comment_ids)
                    ).all()
                    avg_score = sum([d.score for d in details]) / len(details) if details else 0
                else:
                    avg_score = 0
                
                performance_list.append({
                    'service_id': service.service_id,
                    'service_name': service.nick_name,
                    'session_count': session_count,
                    'message_count': message_count,
                    'comment_count': len(comments),
                    'avg_score': round(avg_score, 2)
                })
            
            # 按会话数排序
            performance_list.sort(key=lambda x: x['session_count'], reverse=True)
            
            return {
                'code': 0,
                'data': performance_list
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取客服绩效失败: {str(e)}'}
    
    @staticmethod
    def get_comment_statistics(business_id, days=7):
        """获取评价统计"""
        try:
            from mod.mysql.models import Comment, CommentDetail
            
            start_date = datetime.now() - timedelta(days=days)
            
            # 获取评价ID列表
            comment_ids = db.session.query(Comment.id).filter(
                Comment.business_id == business_id,
                Comment.add_time >= start_date
            ).all()
            
            comment_ids = [c[0] for c in comment_ids]
            
            if not comment_ids:
                return {
                    'code': 0,
                    'data': {
                        'total_count': 0,
                        'avg_score': 0,
                        'score_distribution': {
                            '5': 0, '4': 0, '3': 0, '2': 0, '1': 0
                        }
                    }
                }
            
            # 统计评分分布
            distribution = db.session.query(
                CommentDetail.score,
                func.count(CommentDetail.id)
            ).filter(
                CommentDetail.comment_id.in_(comment_ids)
            ).group_by(CommentDetail.score).all()
            
            # 转换为字典
            score_dist = {str(i): 0 for i in range(1, 6)}
            total_score = 0
            total_count = 0
            
            for score, count in distribution:
                score_dist[str(score)] = count
                total_score += score * count
                total_count += count
            
            avg_score = total_score / total_count if total_count > 0 else 0
            
            return {
                'code': 0,
                'data': {
                    'total_count': total_count,
                    'avg_score': round(avg_score, 2),
                    'score_distribution': score_dist
                }
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取评价统计失败: {str(e)}'}
    
    @staticmethod
    def get_visitor_source_stats(business_id, days=7):
        """获取访客来源统计"""
        try:
            from mod.mysql.models import Visitor
            
            start_date = datetime.now() - timedelta(days=days)
            
            visitors = Visitor.query.filter(
                Visitor.business_id == business_id,
                Visitor.created_at >= start_date
            ).all()
            
            stats = {
                'pc_web': 0,
                'mobile_web': 0,
                'app': 0,
                'miniprogram': 0,
                'other': 0
            }
            
            for visitor in visitors:
                url = (visitor.from_url or '').lower()
                
                if 'miniprogram' in url or 'wxapp' in url:
                    stats['miniprogram'] += 1
                elif 'app://' in url or '/app/' in url:
                    stats['app'] += 1
                elif any(kw in url for kw in ['m.', 'mobile', 'wap']):
                    stats['mobile_web'] += 1
                elif url.startswith('http'):
                    stats['pc_web'] += 1
                else:
                    stats['other'] += 1
            
            return {'code': 0, 'data': stats}
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取访客来源统计失败: {str(e)}'}
    
    @staticmethod  
    def get_device_stats(business_id, days=7):
        """获取设备统计"""
        try:
            from mod.mysql.models import Visitor
            
            start_date = datetime.now() - timedelta(days=days)
            
            visitors = Visitor.query.filter(
                Visitor.business_id == business_id,
                Visitor.created_at >= start_date
            ).all()
            
            stats = {'pc': 0, 'mobile': 0, 'tablet': 0}
            
            for visitor in visitors:
                url = (visitor.from_url or '').lower()
                
                if any(kw in url for kw in ['ipad', 'tablet']):
                    stats['tablet'] += 1
                elif any(kw in url for kw in ['m.', 'mobile', 'wap', 'android', 'iphone']):
                    stats['mobile'] += 1
                else:
                    stats['pc'] += 1
            
            return {'code': 0, 'data': stats}
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取设备统计失败: {str(e)}'}
    
    @staticmethod
    def get_region_stats(business_id, days=7):
        """获取访客地区分布统计"""
        try:
            from mod.mysql.models import Visitor
            from sqlalchemy import func
            
            start_date = datetime.now() - timedelta(days=days)
            
            # 按省份统计访客数
            region_stats = db.session.query(
                Visitor.province,
                func.count(Visitor.vid).label('count')
            ).filter(
                Visitor.business_id == business_id,
                Visitor.created_at >= start_date,
                Visitor.province.isnot(None),
                Visitor.province != ''
            ).group_by(Visitor.province).order_by(func.count(Visitor.vid).desc()).all()
            
            # 转换为字典格式
            if not region_stats:
                return {
                    'code': 0,
                    'data': {
                        'regions': [],
                        'counts': [],
                        'total': 0
                    }
                }
            
            # 取前10个地区
            top_regions = region_stats[:10]
            other_count = sum([r.count for r in region_stats[10:]]) if len(region_stats) > 10 else 0
            
            regions = [r.province for r in top_regions]
            counts = [r.count for r in top_regions]
            
            if other_count > 0:
                regions.append('其他')
                counts.append(other_count)
            
            total = sum(counts)
            
            return {
                'code': 0,
                'data': {
                    'regions': regions,
                    'counts': counts,
                    'total': total
                }
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'code': -1, 'msg': f'获取地区统计失败: {str(e)}'}
    
    @staticmethod
    def get_realtime_events(business_id, limit=10):
        """获取实时事件流（同一访客只显示最新动态）"""
        try:
            from mod.mysql.models import Visitor, Chat, Comment
            
            # 使用字典存储每个用户的最新事件（去重）
            user_events = {}
            
            # 最新访客（获取最近1小时的）
            one_hour_ago = datetime.now() - timedelta(hours=1)
            visitors = Visitor.query.filter(
                Visitor.business_id == business_id,
                Visitor.created_at >= one_hour_ago
            ).order_by(Visitor.created_at.desc()).limit(10).all()
            
            for v in visitors:
                # 显示完整的访客名称
                display_name = v.visitor_name if v.visitor_name else f'访客{v.visitor_id[-4:]}'
                visitor_id = v.visitor_id
                
                # 如果该访客还没有记录，或者这条记录更新，则更新
                if visitor_id not in user_events or v.created_at > user_events[visitor_id]['created_at']:
                    user_events[visitor_id] = {
                        'type': 'visit',
                        'name': '新访客',
                        'user': display_name,
                        'visitor_id': visitor_id,
                        'timestamp': v.created_at.isoformat(),
                        'created_at': v.created_at
                    }
            
            # 最新消息（获取最近1小时的）
            chats = Chat.query.filter(
                Chat.business_id == business_id,
                Chat.created_at >= one_hour_ago
            ).order_by(Chat.created_at.desc()).limit(20).all()
            
            for c in chats:
                # 获取访客名称
                visitor = Visitor.query.filter_by(
                    visitor_id=c.visitor_id,
                    business_id=business_id
                ).first()
                
                display_name = visitor.visitor_name if visitor and visitor.visitor_name else f'访客{c.visitor_id[-4:]}'
                visitor_id = c.visitor_id
                
                # 如果该访客还没有记录，或者这条消息更新，则更新
                # 消息优先级高于访客加入事件
                if visitor_id not in user_events or c.created_at > user_events[visitor_id]['created_at']:
                    user_events[visitor_id] = {
                        'type': 'message',
                        'name': '新消息',
                        'user': display_name,
                        'visitor_id': visitor_id,
                        'timestamp': c.created_at.isoformat(),
                        'created_at': c.created_at
                    }
            
            # 最新评价（获取最近24小时的）
            one_day_ago = datetime.now() - timedelta(days=1)
            comments = Comment.query.filter(
                Comment.business_id == business_id,
                Comment.add_time >= one_day_ago
            ).order_by(Comment.add_time.desc()).limit(5).all()
            
            for cm in comments:
                # 评价使用visitor_name作为key（可能没有visitor_id）
                user_key = f"comment_{cm.visitor_name or cm.id}"
                
                event = {
                    'type': 'comment',
                    'name': '新评价',
                    'user': cm.visitor_name or '匿名',
                    'timestamp': cm.add_time.isoformat(),
                    'created_at': cm.add_time
                }
                
                # 评价不与访客/消息事件去重，单独显示
                if user_key not in user_events:
                    user_events[user_key] = event
            
            # 转换为列表并按时间排序（最新的在前）
            events = list(user_events.values())
            events.sort(key=lambda x: x['created_at'], reverse=True)
            
            # 移除内部字段
            for event in events:
                del event['created_at']
                if 'visitor_id' in event:
                    del event['visitor_id']
            
            return {'code': 0, 'data': events[:limit]}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'code': -1, 'msg': f'获取实时事件失败: {str(e)}'}
    
    @staticmethod
    def _format_time_ago(time_diff):
        """格式化时间差"""
        seconds = int(time_diff.total_seconds())
        
        if seconds < 60:
            return '刚刚'
        elif seconds < 3600:
            return f'{seconds // 60}分钟前'
        elif seconds < 86400:
            return f'{seconds // 3600}小时前'
        else:
            return f'{seconds // 86400}天前'

