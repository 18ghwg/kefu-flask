-- 创建客服评价表
-- 执行时间: 2025-10-10

CREATE TABLE IF NOT EXISTS `service_ratings` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `visitor_id` varchar(200) NOT NULL COMMENT '访客ID',
  `service_id` int(11) NOT NULL COMMENT '客服ID',
  `business_id` int(11) NOT NULL COMMENT '商户ID',
  `queue_id` int(11) DEFAULT NULL COMMENT '会话队列ID',
  `rating` smallint(6) NOT NULL COMMENT '评分 1-5星',
  `comment` text COMMENT '评价内容',
  `tags` varchar(500) DEFAULT NULL COMMENT '评价标签，逗号分隔',
  `visitor_name` varchar(100) DEFAULT NULL COMMENT '访客昵称',
  `visitor_ip` varchar(50) DEFAULT NULL COMMENT '访客IP',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '评价时间',
  PRIMARY KEY (`id`),
  KEY `idx_visitor_id` (`visitor_id`),
  KEY `idx_service_id` (`service_id`),
  KEY `idx_business_id` (`business_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客服评价表';


