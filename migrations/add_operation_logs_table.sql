-- 添加操作日志表
-- 版本: 2025-10-06
-- 说明: 记录所有管理员和客服的操作日志，用于审计和排查问题

CREATE TABLE IF NOT EXISTS `operation_logs` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `business_id` INT(11) NOT NULL COMMENT '商户ID',
    
    -- 操作人信息
    `operator_id` INT(11) NOT NULL COMMENT '操作人ID',
    `operator_name` VARCHAR(100) NOT NULL COMMENT '操作人名称',
    `operator_type` ENUM('admin', 'service', 'system') DEFAULT 'admin' COMMENT '操作人类型',
    
    -- 操作信息
    `module` VARCHAR(50) NOT NULL COMMENT '操作模块（如：visitor, service, robot等）',
    `action` VARCHAR(50) NOT NULL COMMENT '操作动作（如：create, update, delete等）',
    `description` VARCHAR(500) NOT NULL COMMENT '操作描述',
    
    -- 请求信息
    `method` VARCHAR(10) DEFAULT '' COMMENT 'HTTP方法',
    `path` VARCHAR(255) DEFAULT '' COMMENT '请求路径',
    `ip` VARCHAR(50) DEFAULT '' COMMENT '操作IP',
    `user_agent` VARCHAR(500) DEFAULT '' COMMENT 'User-Agent',
    
    -- 操作详情
    `target_id` VARCHAR(50) DEFAULT '' COMMENT '目标对象ID',
    `target_type` VARCHAR(50) DEFAULT '' COMMENT '目标对象类型',
    `params` TEXT COMMENT '请求参数（JSON）',
    `result` ENUM('success', 'fail') DEFAULT 'success' COMMENT '操作结果',
    `error_msg` TEXT COMMENT '错误信息',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    
    PRIMARY KEY (`id`),
    INDEX `idx_business_id` (`business_id`),
    INDEX `idx_operator` (`operator_id`, `operator_type`),
    INDEX `idx_module_action` (`module`, `action`),
    INDEX `idx_result` (`result`),
    INDEX `idx_created_at` (`created_at`),
    
    CONSTRAINT `fk_operation_logs_business` 
        FOREIGN KEY (`business_id`) 
        REFERENCES `businesses` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- 添加索引优化查询性能
ALTER TABLE `operation_logs` 
    ADD INDEX `idx_business_created` (`business_id`, `created_at` DESC);

-- 示例数据（可选）
-- INSERT INTO `operation_logs` 
-- (`business_id`, `operator_id`, `operator_name`, `operator_type`, `module`, `action`, `description`, `method`, `path`, `ip`)
-- VALUES 
-- (1, 1, 'admin', 'admin', 'system', 'init', '系统初始化', 'POST', '/install', '127.0.0.1');

