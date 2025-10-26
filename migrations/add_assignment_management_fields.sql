-- 智能客服分配与会话管理系统 - 数据库扩展
-- 执行日期: 2025-10-09

-- 1. 扩展 services 表 - 添加接待能力配置
ALTER TABLE services 
ADD COLUMN IF NOT EXISTS max_concurrent_chats INT DEFAULT 5 COMMENT '最大并发接待数',
ADD COLUMN IF NOT EXISTS current_chat_count INT DEFAULT 0 COMMENT '当前接待数',
ADD COLUMN IF NOT EXISTS last_assign_time DATETIME COMMENT '最后分配时间',
ADD COLUMN IF NOT EXISTS auto_accept TINYINT(1) DEFAULT 1 COMMENT '是否自动接待';

-- 添加索引优化查询
CREATE INDEX IF NOT EXISTS idx_service_capacity ON services(state, current_chat_count, max_concurrent_chats);
CREATE INDEX IF NOT EXISTS idx_service_business ON services(business_id, state);

-- 2. 扩展 chats 表 - 添加会话管理字段
ALTER TABLE chats
ADD COLUMN IF NOT EXISTS exclusive_service_id INT COMMENT '专属客服ID',
ADD COLUMN IF NOT EXISTS assign_type ENUM('auto', 'exclusive', 'manual') DEFAULT 'auto' COMMENT '分配类型',
ADD COLUMN IF NOT EXISTS is_exclusive TINYINT(1) DEFAULT 0 COMMENT '是否专属会话';

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_chat_service ON chats(service_id, visitor_id);
CREATE INDEX IF NOT EXISTS idx_chat_exclusive ON chats(exclusive_service_id, is_exclusive);

-- 3. 扩展 queues 表 - 添加排队管理字段  
ALTER TABLE queues
ADD COLUMN IF NOT EXISTS wait_position INT COMMENT '排队位置',
ADD COLUMN IF NOT EXISTS estimated_wait_time INT COMMENT '预估等待时间（秒）',
ADD COLUMN IF NOT EXISTS priority INT DEFAULT 0 COMMENT '优先级 0=普通 1=VIP 2=紧急',
ADD COLUMN IF NOT EXISTS exclusive_service_id INT COMMENT '专属客服ID',
ADD COLUMN IF NOT EXISTS is_exclusive TINYINT(1) DEFAULT 0 COMMENT '是否专属会话',
ADD COLUMN IF NOT EXISTS assign_status ENUM('waiting', 'assigned', 'timeout') DEFAULT 'waiting' COMMENT '分配状态';

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_queue_waiting ON queues(business_id, service_id, state, assign_status);
CREATE INDEX IF NOT EXISTS idx_queue_exclusive ON queues(exclusive_service_id, is_exclusive);
CREATE INDEX IF NOT EXISTS idx_queue_priority ON queues(priority DESC, created_at ASC);

-- 4. 扩展 visitors 表 - 添加会话信息
ALTER TABLE visitors
ADD COLUMN IF NOT EXISTS current_service_id INT COMMENT '当前接待客服ID',
ADD COLUMN IF NOT EXISTS exclusive_service_id INT COMMENT '专属客服ID',
ADD COLUMN IF NOT EXISTS last_session_at DATETIME COMMENT '最后会话时间';

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_visitor_service ON visitors(current_service_id);
CREATE INDEX IF NOT EXISTS idx_visitor_exclusive ON visitors(exclusive_service_id);

-- 5. 创建系统配置表（如果不存在）
CREATE TABLE IF NOT EXISTS system_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    business_id INT NOT NULL DEFAULT 1 COMMENT '商户ID',
    config_key VARCHAR(100) NOT NULL COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_type ENUM('string', 'int', 'json', 'bool') DEFAULT 'string' COMMENT '配置类型',
    description VARCHAR(500) COMMENT '描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_business_key (business_id, config_key),
    INDEX idx_business (business_id)
) COMMENT '系统配置表';

-- 插入默认配置
INSERT INTO system_config (business_id, config_key, config_value, config_type, description) VALUES
(1, 'default_max_concurrent_chats', '5', 'int', '默认最大并发接待数'),
(1, 'enable_auto_assignment', 'true', 'bool', '启用自动分配'),
(1, 'queue_timeout', '1800', 'int', '排队超时时间（秒）'),
(1, 'enable_queue_notification', 'true', 'bool', '启用排队通知'),
(1, 'assignment_algorithm', 'min_load', 'string', '分配算法：min_load(最小负载) | round_robin(轮询)'),
(1, 'show_queue_position', 'true', 'bool', '显示排队位置'),
(1, 'allow_admin_takeover', 'true', 'bool', '允许管理员接管会话')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);

-- 6. 创建会话快照表（用于审计和统计）
CREATE TABLE IF NOT EXISTS session_snapshots (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(50) NOT NULL COMMENT '会话ID',
    visitor_id VARCHAR(200) NOT NULL COMMENT '访客ID',
    service_id INT NOT NULL COMMENT '客服ID',
    business_id INT NOT NULL COMMENT '商户ID',
    exclusive_service_id INT COMMENT '专属客服ID',
    is_exclusive TINYINT(1) DEFAULT 0 COMMENT '是否专属',
    assign_type ENUM('auto', 'exclusive', 'manual', 'queue') DEFAULT 'auto' COMMENT '分配方式',
    wait_time INT COMMENT '等待时间（秒）',
    queue_position INT COMMENT '排队位置',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration INT COMMENT '会话时长（秒）',
    message_count INT DEFAULT 0 COMMENT '消息数量',
    status ENUM('active', 'completed', 'timeout', 'transferred') DEFAULT 'active' COMMENT '会话状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_visitor (visitor_id),
    INDEX idx_service (service_id),
    INDEX idx_business (business_id, created_at),
    INDEX idx_status (status, created_at)
) COMMENT '会话快照表';

-- 7. 更新现有数据的默认值
UPDATE services SET max_concurrent_chats = 5 WHERE max_concurrent_chats IS NULL;
UPDATE services SET current_chat_count = 0 WHERE current_chat_count IS NULL;
UPDATE services SET auto_accept = 1 WHERE auto_accept IS NULL;

UPDATE queues SET priority = 0 WHERE priority IS NULL;
UPDATE queues SET is_exclusive = 0 WHERE is_exclusive IS NULL;
UPDATE queues SET assign_status = 'assigned' WHERE service_id > 0 AND assign_status IS NULL;
UPDATE queues SET assign_status = 'waiting' WHERE service_id = 0 AND assign_status IS NULL;

-- 8. 创建触发器 - 自动更新客服接待数
DELIMITER //

CREATE TRIGGER IF NOT EXISTS trg_queue_insert_update_count
AFTER INSERT ON queues
FOR EACH ROW
BEGIN
    IF NEW.service_id > 0 AND NEW.state = 'normal' THEN
        UPDATE services 
        SET current_chat_count = current_chat_count + 1,
            last_assign_time = NOW()
        WHERE service_id = NEW.service_id;
    END IF;
END//

CREATE TRIGGER IF NOT EXISTS trg_queue_update_count
AFTER UPDATE ON queues
FOR EACH ROW
BEGIN
    -- 当分配客服时，增加计数
    IF NEW.service_id > 0 AND OLD.service_id = 0 AND NEW.state = 'normal' THEN
        UPDATE services 
        SET current_chat_count = current_chat_count + 1,
            last_assign_time = NOW()
        WHERE service_id = NEW.service_id;
    END IF;
    
    -- 当会话结束时，减少计数
    IF OLD.state = 'normal' AND NEW.state != 'normal' AND OLD.service_id > 0 THEN
        UPDATE services 
        SET current_chat_count = GREATEST(0, current_chat_count - 1)
        WHERE service_id = OLD.service_id;
    END IF;
    
    -- 当转接客服时，更新双方计数
    IF NEW.service_id != OLD.service_id AND NEW.service_id > 0 AND OLD.service_id > 0 THEN
        UPDATE services 
        SET current_chat_count = GREATEST(0, current_chat_count - 1)
        WHERE service_id = OLD.service_id;
        
        UPDATE services 
        SET current_chat_count = current_chat_count + 1,
            last_assign_time = NOW()
        WHERE service_id = NEW.service_id;
    END IF;
END//

DELIMITER ;

-- 9. 创建视图 - 客服工作负载视图
CREATE OR REPLACE VIEW v_service_workload AS
SELECT 
    s.service_id,
    s.nick_name,
    s.state AS online_status,
    s.max_concurrent_chats,
    s.current_chat_count,
    s.last_assign_time,
    CASE 
        WHEN s.state = 'offline' THEN 'offline'
        WHEN s.current_chat_count >= s.max_concurrent_chats THEN 'full'
        WHEN s.current_chat_count > 0 THEN 'busy'
        ELSE 'idle'
    END AS work_status,
    CASE 
        WHEN s.max_concurrent_chats > 0 
        THEN ROUND(s.current_chat_count / s.max_concurrent_chats * 100, 2)
        ELSE 0
    END AS utilization_rate,
    (s.max_concurrent_chats - s.current_chat_count) AS available_slots
FROM services s;

-- 10. 创建存储过程 - 智能分配客服
DELIMITER //

CREATE PROCEDURE IF NOT EXISTS sp_assign_service(
    IN p_visitor_id VARCHAR(200),
    IN p_business_id INT,
    IN p_exclusive_service_id INT,
    OUT p_service_id INT,
    OUT p_action VARCHAR(20),
    OUT p_message VARCHAR(200)
)
BEGIN
    DECLARE v_count INT;
    DECLARE v_service_online TINYINT;
    
    -- 1. 如果指定了专属客服
    IF p_exclusive_service_id IS NOT NULL AND p_exclusive_service_id > 0 THEN
        -- 检查专属客服是否存在
        SELECT COUNT(*), MAX(state = 'online')
        INTO v_count, v_service_online
        FROM services 
        WHERE service_id = p_exclusive_service_id AND business_id = p_business_id;
        
        IF v_count > 0 THEN
            SET p_service_id = p_exclusive_service_id;
            SET p_action = 'assigned';
            IF v_service_online = 1 THEN
                SET p_message = '已为您分配专属客服';
            ELSE
                SET p_message = '专属客服暂时离线，上线后会立即回复您';
            END IF;
            LEAVE BEGIN;
        ELSE
            SET p_service_id = NULL;
            SET p_action = 'error';
            SET p_message = '指定的专属客服不存在';
            LEAVE BEGIN;
        END IF;
    END IF;
    
    -- 2. 智能分配：查找负载最低的在线客服
    SELECT service_id INTO p_service_id
    FROM services
    WHERE business_id = p_business_id
      AND state = 'online'
      AND current_chat_count < max_concurrent_chats
      AND auto_accept = 1
    ORDER BY current_chat_count ASC, last_assign_time ASC
    LIMIT 1;
    
    -- 3. 如果找到了可用客服
    IF p_service_id IS NOT NULL THEN
        SET p_action = 'assigned';
        SET p_message = '已为您分配客服';
    ELSE
        -- 4. 没有可用客服，需要排队
        SET p_service_id = NULL;
        SET p_action = 'queued';
        
        -- 计算排队位置
        SELECT COUNT(*) + 1 INTO v_count
        FROM queues
        WHERE business_id = p_business_id
          AND service_id = 0
          AND state = 'normal';
        
        SET p_message = CONCAT('客服繁忙，您前面还有 ', v_count - 1, ' 位访客在等待');
    END IF;
END//

DELIMITER ;

-- 完成
SELECT '智能客服分配与会话管理系统 - 数据库扩展完成' AS message;

