-- ============================================
-- 性能优化：添加复合索引
-- 创建时间：2025-10-26
-- 说明：根据查询模式添加复合索引以提升查询性能
-- ============================================

-- ========== Chat 表复合索引 ==========

-- 1. 访客查询历史消息（按时间倒序）
-- 使用场景：访客端加载聊天历史
CREATE INDEX IF NOT EXISTS idx_chat_visitor_timestamp 
ON chats(visitor_id, timestamp DESC);

-- 2. 客服查询未读消息
-- 使用场景：客服工作台获取未读消息数
CREATE INDEX IF NOT EXISTS idx_chat_service_state 
ON chats(service_id, state, timestamp DESC);

-- 3. 访客+客服组合查询（会话消息）
-- 使用场景：查询特定访客与特定客服的对话记录
CREATE INDEX IF NOT EXISTS idx_chat_visitor_service 
ON chats(visitor_id, service_id, timestamp DESC);

-- 4. 商户维度统计（按时间范围）
-- 使用场景：数据看板统计
CREATE INDEX IF NOT EXISTS idx_chat_business_created 
ON chats(business_id, created_at DESC);


-- ========== Queue 表复合索引 ==========

-- 1. 客服当前会话列表
-- 使用场景：客服工作台显示当前接待的访客
CREATE INDEX IF NOT EXISTS idx_queue_service_state 
ON queues(service_id, state, updated_at DESC);

-- 2. 排队中的访客列表
-- 使用场景：管理后台查看排队情况
CREATE INDEX IF NOT EXISTS idx_queue_waiting 
ON queues(business_id, assign_status, created_at ASC) 
WHERE assign_status = 'waiting';

-- 3. 访客当前会话状态
-- 使用场景：访客进入时检查是否有进行中的会话
CREATE INDEX IF NOT EXISTS idx_queue_visitor_state 
ON queues(visitor_id, state, created_at DESC);


-- ========== Visitor 表复合索引 ==========

-- 1. 在线访客列表（按最后消息时间排序）
-- 使用场景：管理后台访客管理页面
CREATE INDEX IF NOT EXISTS idx_visitor_state_msgtime 
ON visitors(business_id, state, msg_time DESC);

-- 2. 访客搜索（IP+商户）
-- 使用场景：按IP搜索访客
CREATE INDEX IF NOT EXISTS idx_visitor_ip_business 
ON visitors(ip, business_id);

-- ========== 分析和说明 ==========
-- 
-- 索引设计原则（遵循SOLID原则）：
-- 1. 最左前缀原则：索引列顺序按查询频率和过滤效率排列
-- 2. 覆盖索引：包含常用查询字段，减少回表
-- 3. 选择性原则：优先索引选择性高的列（区分度高）
-- 4. 避免冗余：不创建已有索引的子集
--
-- 性能提升预期：
-- - 访客历史消息加载：50-80% 提升
-- - 客服未读消息统计：60-90% 提升
-- - 排队列表查询：40-70% 提升
-- - 会话状态查询：50-80% 提升
--
-- 注意事项：
-- - 索引会增加写入开销（约10-15%），但读取性能提升远大于此
-- - 定期使用 ANALYZE TABLE 更新统计信息
-- - 监控索引使用情况，移除未使用的索引
-- ============================================

