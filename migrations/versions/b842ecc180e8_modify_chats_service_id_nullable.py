"""modify_chats_service_id_nullable

修改chats表的service_id字段为可空，以支持机器人消息（service_id=NULL表示机器人发送）

Revision ID: b842ecc180e8
Revises: 48e5187efe58
Create Date: 2025-10-26 15:34:41.813336

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'b842ecc180e8'
down_revision = '48e5187efe58'
branch_labels = None
depends_on = None


def upgrade():
    # 修改 chats 表的 service_id 字段为可空
    # NULL 表示机器人发送的消息
    op.alter_column('chats', 'service_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True,
               comment='客服ID（NULL表示机器人）',
               existing_comment='客服ID')


def downgrade():
    # 回滚：将 service_id 改回不可空
    # 注意：回滚前需要确保没有 NULL 值，否则会失败
    op.alter_column('chats', 'service_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False,
               comment='客服ID',
               existing_comment='客服ID（NULL表示机器人）')
