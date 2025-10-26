#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
客服管理业务逻辑
负责客服的增删改查等操作
"""
from datetime import datetime
from exts import db
from mod.mysql.models import Service, Queue


class ServiceManagement:
    """客服管理服务"""
    
    @staticmethod
    def get_service_list(business_id, state=None, page=1, per_page=20):
        """
        获取客服列表（排除机器人）
        
        Args:
            business_id: 商户ID
            state: 状态筛选（online/offline/busy）
            page: 页码
            per_page: 每页数量
        
        Returns:
            dict: 客服列表
        """
        try:
            # ⚡ 排除机器人客服（service_id=0 或 user_name='robot'）
            query = Service.query.filter(
                Service.business_id == business_id,
                Service.service_id != 0,
                Service.user_name != 'robot'
            )
            
            if state:
                query = query.filter_by(state=state)
            
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            service_list = []
            for service in pagination.items:
                # 获取当前接待数
                current_sessions = Queue.query.filter_by(
                    service_id=service.service_id,
                    state='chatting'
                ).count()
                
                service_list.append({
                    'service_id': service.service_id,
                    'user_name': service.user_name,
                    'nick_name': service.nick_name,
                    'avatar': service.avatar,
                    'level': service.level,
                    'state': service.state,
                    'current_sessions': current_sessions,
                    'max_sessions': getattr(service, 'max_sessions', 5),
                    'created_at': service.timestamp.isoformat() if service.timestamp else None
                })
            
            return {
                'code': 0,
                'data': {
                    'list': service_list,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'page': page
                }
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取客服列表失败: {str(e)}'}
    
    @staticmethod
    def get_all_services(business_id):
        """
        获取所有客服（不分页，排除机器人）
        
        Args:
            business_id: 商户ID
        
        Returns:
            dict: 客服列表
        """
        try:
            # ⚡ 排除机器人客服（service_id=0 或 user_name='robot'）
            pagination = Service.query.filter(
                Service.business_id == business_id,
                Service.service_id != 0,
                Service.user_name != 'robot'
            ).paginate(page=1, per_page=999, error_out=False)
            
            services = [s.to_dict() for s in pagination.items]
            
            return {
                'code': 0,
                'data': {
                    'services': services,
                    'total': pagination.total
                }
            }
            
        except Exception as e:
            return {'code': -1, 'msg': f'获取客服列表失败: {str(e)}'}
    
    @staticmethod
    def add_service(business_id, user_name, nick_name, password, 
                   level='service', group_id='0', phone='', email=''):
        """
        添加客服
        
        Args:
            business_id: 商户ID
            user_name: 用户名
            nick_name: 昵称
            password: 密码
            level: 权限级别
            group_id: 分组ID
            phone: 电话
            email: 邮箱
        
        Returns:
            dict: 创建结果
        """
        try:
            # 检查用户名是否已存在
            if Service.query.filter_by(user_name=user_name).first():
                return {'code': -1, 'msg': '用户名已存在'}
            
            # 创建客服
            service = Service(
                user_name=user_name,
                nick_name=nick_name,
                business_id=business_id,
                level=level,
                group_id=group_id,
                phone=phone,
                email=email
            )
            service.password = password
            
            db.session.add(service)
            db.session.commit()
            
            return {
                'code': 0,
                'msg': '添加成功',
                'data': service.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'添加客服失败: {str(e)}'}
    
    @staticmethod
    def update_service_state(service_id, state):
        """
        更新客服在线状态
        
        Args:
            service_id: 客服ID
            state: 状态（online/offline/busy）
        
        Returns:
            dict: 更新结果
        """
        try:
            if state not in ['online', 'offline', 'busy']:
                return {'code': -1, 'msg': '状态参数无效'}
            
            service = Service.query.filter_by(service_id=service_id).first()
            if not service:
                return {'code': -1, 'msg': '客服不存在'}
            
            service.state = state
            db.session.commit()
            
            return {'code': 0, 'msg': '状态更新成功'}
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'更新状态失败: {str(e)}'}
    
    @staticmethod
    def update_service(service_id, **kwargs):
        """
        更新客服信息
        
        Args:
            service_id: 客服ID
            **kwargs: 要更新的字段
        
        Returns:
            dict: 更新结果
        """
        try:
            service = Service.query.filter_by(service_id=service_id).first()
            if not service:
                return {'code': -1, 'msg': '客服不存在'}
            
            # ⚡ 防止修改机器人客服
            if service.service_id == 0 or service.user_name == 'robot':
                return {'code': -1, 'msg': '机器人客服不可修改'}
            
            # 更新允许的字段
            allowed_fields = ['nick_name', 'phone', 'email', 'level', 'group_id', 'avatar']
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    setattr(service, field, value)
            
            db.session.commit()
            
            return {
                'code': 0,
                'msg': '更新成功',
                'data': service.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'更新客服信息失败: {str(e)}'}
    
    @staticmethod
    def delete_service(service_id):
        """
        删除客服
        
        Args:
            service_id: 客服ID
        
        Returns:
            dict: 删除结果
        """
        try:
            service = Service.query.filter_by(service_id=service_id).first()
            if not service:
                return {'code': -1, 'msg': '客服不存在'}
            
            # ⚡ 防止删除机器人客服
            if service.service_id == 0 or service.user_name == 'robot':
                return {'code': -1, 'msg': '机器人客服不可删除'}
            
            # 检查是否有进行中的会话
            active_sessions = Queue.query.filter_by(
                service_id=service_id,
                state='chatting'
            ).count()
            
            if active_sessions > 0:
                return {'code': -1, 'msg': f'该客服还有{active_sessions}个进行中的会话，无法删除'}
            
            db.session.delete(service)
            db.session.commit()
            
            return {'code': 0, 'msg': '删除成功'}
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'删除客服失败: {str(e)}'}
    
    @staticmethod
    def authenticate(username, password, business_id):
        """
        验证客服登录
        
        Args:
            username: 用户名
            password: 密码
            business_id: 商户ID
        
        Returns:
            dict: 验证结果
        """
        try:
            # 查询客服
            service = Service.query.filter_by(
                user_name=username,
                business_id=business_id
            ).first()
            
            if not service or not service.verify_password(password):
                return {'code': -1, 'msg': '用户名或密码错误', 'data': None}
            
            # 更新在线状态
            service.state = 'online'
            db.session.commit()
            
            return {
                'code': 0,
                'msg': '登录成功',
                'data': service
            }
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'登录失败: {str(e)}', 'data': None}
    
    @staticmethod
    def logout_service(service_id):
        """
        客服登出
        
        Args:
            service_id: 客服ID
        
        Returns:
            dict: 登出结果
        """
        try:
            service = Service.query.filter_by(service_id=service_id).first()
            if not service:
                return {'code': -1, 'msg': '客服不存在'}
            
            # 更新离线状态
            service.state = 'offline'
            db.session.commit()
            
            return {'code': 0, 'msg': '登出成功'}
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'登出失败: {str(e)}'}
    
    @staticmethod
    def change_password(service_id, old_password, new_password):
        """
        修改密码
        
        Args:
            service_id: 客服ID
            old_password: 旧密码
            new_password: 新密码
        
        Returns:
            dict: 修改结果
        """
        try:
            service = Service.query.filter_by(service_id=service_id).first()
            if not service:
                return {'code': -1, 'msg': '客服不存在'}
            
            # 验证旧密码
            if not service.verify_password(old_password):
                return {'code': -1, 'msg': '旧密码不正确'}
            
            # 设置新密码
            service.password = new_password
            db.session.commit()
            
            return {'code': 0, 'msg': '密码修改成功'}
            
        except Exception as e:
            db.session.rollback()
            return {'code': -1, 'msg': f'密码修改失败: {str(e)}'}


# 创建单例实例
service_management = ServiceManagement()

