-- 添加最后消息时间字段到队列表
-- 执行时间: 2025-10-08

ALTER TABLE `queues` 
ADD COLUMN `last_message_time` DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最后消息时间' AFTER `updated_at`;

-- 更新现有记录的last_message_time为updated_at
UPDATE `queues` SET `last_message_time` = `updated_at` WHERE `last_message_time` IS NULL;

