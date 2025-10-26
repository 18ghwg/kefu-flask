-- 修复队列表 service_id 字段允许NULL
-- 日期: 2025-10-25
-- 说明: 允许 service_id 为 NULL，表示访客未分配客服的状态

-- 1. 修改 service_id 字段为可空
ALTER TABLE `queues` 
MODIFY COLUMN `service_id` INT(11) NULL COMMENT '客服ID (NULL=未分配)';

-- 2. 验证修改
SELECT 
    COLUMN_NAME,
    IS_NULLABLE,
    DATA_TYPE,
    COLUMN_COMMENT
FROM 
    INFORMATION_SCHEMA.COLUMNS
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'queues'
    AND COLUMN_NAME = 'service_id';

