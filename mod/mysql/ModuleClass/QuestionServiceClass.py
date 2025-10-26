"""
常见问题服务类
处理FAQ相关业务逻辑
"""
import log
from exts import db
from mod.mysql.models import Question
from sqlalchemy import func

logger = log.get_logger(__name__)


class QuestionService:
    """常见问题服务类"""
    
    @staticmethod
    def get_random_questions(business_id, limit=3):
        """
        获取随机的常见问题（用于机器人回复）
        
        Args:
            business_id: 商户ID
            limit: 返回数量，默认3条
            
        Returns:
            str: 格式化的常见问题文本（HTML格式）
        """
        try:
            questions = Question.query.filter_by(
                business_id=business_id,
                status=1  # 只获取启用的问题
            ).order_by(func.random()).limit(limit).all()
            
            if not questions:
                return "抱歉，暂时无法回答您的问题，请稍后联系客服。"
            
            # 构建HTML格式的回复
            reply = '<div class="robot-faq-reply">'
            reply += '<p style="font-weight: bold; margin-bottom: 10px;">💡 您可以参考以下常见问题：</p>'
            
            for idx, q in enumerate(questions, 1):
                reply += f'<div style="margin-bottom: 15px; padding: 10px; background: #f3f4f6; border-radius: 8px;">'
                reply += f'<div style="font-weight: 600; margin-bottom: 5px;">Q{idx}: {q.question}</div>'
                reply += f'<div style="color: #6b7280;">{q.answer_text or q.answer}</div>'
                reply += '</div>'
            
            reply += '</div>'
            
            logger.info(f"为商户{business_id}返回了{len(questions)}条常见问题")
            return reply
            
        except Exception as e:
            logger.error(f"获取随机常见问题失败: {e}")
            return "抱歉，系统出错了，请稍后再试。"
    
    @staticmethod
    def search_questions(business_id, keyword):
        """
        根据关键词搜索常见问题
        
        Args:
            business_id: 商户ID
            keyword: 搜索关键词
            
        Returns:
            list: 匹配的问题列表
        """
        try:
            questions = Question.query.filter(
                Question.business_id == business_id,
                Question.status == 1,
                db.or_(
                    Question.question.like(f'%{keyword}%'),
                    Question.keyword.like(f'%{keyword}%'),
                    Question.answer_text.like(f'%{keyword}%')
                )
            ).limit(5).all()
            
            return questions
            
        except Exception as e:
            logger.error(f"搜索常见问题失败: {e}")
            return []
    
    @staticmethod
    def get_all_questions(business_id):
        """
        获取所有常见问题
        
        Args:
            business_id: 商户ID
            
        Returns:
            list: 问题列表
        """
        try:
            questions = Question.query.filter_by(
                business_id=business_id
            ).order_by(Question.sort.desc(), Question.qid.desc()).all()
            
            return questions
            
        except Exception as e:
            logger.error(f"获取常见问题列表失败: {e}")
            return []
    
    @staticmethod
    def create_question(business_id, question, answer, keyword='', answer_text='', sort=0):
        """
        创建常见问题
        
        Args:
            business_id: 商户ID
            question: 问题
            answer: 答案（HTML）
            keyword: 关键词
            answer_text: 纯文本答案
            sort: 排序
            
        Returns:
            Question: 创建的问题对象
        """
        try:
            new_question = Question(
                business_id=business_id,
                question=question,
                answer=answer,
                keyword=keyword,
                answer_text=answer_text or answer,  # 如果没有纯文本，使用HTML
                sort=sort,
                status=1
            )
            
            db.session.add(new_question)
            db.session.commit()
            
            logger.info(f"创建常见问题成功: {question}")
            return new_question
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建常见问题失败: {e}")
            return None
    
    @staticmethod
    def update_question(qid, question=None, answer=None, keyword=None, answer_text=None, sort=None, status=None):
        """
        更新常见问题
        
        Args:
            qid: 问题ID
            question: 问题
            answer: 答案（HTML）
            keyword: 关键词
            answer_text: 纯文本答案
            sort: 排序
            status: 状态
            
        Returns:
            bool: 是否成功
        """
        try:
            q = Question.query.get(qid)
            if not q:
                return False
            
            if question is not None:
                q.question = question
            if answer is not None:
                q.answer = answer
            if keyword is not None:
                q.keyword = keyword
            if answer_text is not None:
                q.answer_text = answer_text
            if sort is not None:
                q.sort = sort
            if status is not None:
                q.status = status
            
            db.session.commit()
            
            logger.info(f"更新常见问题成功: {qid}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新常见问题失败: {e}")
            return False
    
    @staticmethod
    def delete_question(qid):
        """
        删除常见问题
        
        Args:
            qid: 问题ID
            
        Returns:
            bool: 是否成功
        """
        try:
            q = Question.query.get(qid)
            if not q:
                return False
            
            db.session.delete(q)
            db.session.commit()
            
            logger.info(f"删除常见问题成功: {qid}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"删除常见问题失败: {e}")
            return False


# 创建单例
question_service = QuestionService()

