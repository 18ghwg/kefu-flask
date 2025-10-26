/**
 * 知识库管理页面 - Script
 */

let currentPage = 1;
        let totalPages = 1;
        let searchKeyword = '';
        let quillEditor = null;  // Quill富文本编辑器实例

        // 加载知识库列表
        async function loadKnowledge(page = 1) {
            try {
                const response = await fetch(`/api/robot/list?page=${page}&keyword=${searchKeyword}`);
                const result = await response.json();

                if (result.code === 0) {
                    const { list, total, pages } = result.data;
                    currentPage = page;
                    totalPages = pages;

                    renderKnowledgeList(list);
                    updatePagination();
                    updateStats();
                }
            } catch (error) {
                modal.error('加载失败：' + error.message);
            }
        }

        // 渲染列表
        function renderKnowledgeList(list) {
            const tbody = document.getElementById('knowledgeList');
            
            if (list.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" class="empty-state">
                            <i class="fas fa-inbox"></i>
                            <p>暂无知识库数据</p>
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = list.map(item => {
                // 提取纯文本预览（移除HTML标签）
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = item.reply || '';
                const textPreview = tempDiv.textContent || tempDiv.innerText || '';
                const preview = textPreview.substring(0, 100) + (textPreview.length > 100 ? '...' : '');
                
                return `
                <tr>
                    <td>${item.id}</td>
                    <td><strong>${item.keyword}</strong></td>
                    <td>
                        <div class="reply-preview">${item.reply || preview}</div>
                    </td>
                    <td>${item.sort}</td>
                    <td>
                        <button class="status-toggle ${item.status === 1 ? 'active' : 'inactive'}" 
                                onclick="toggleStatus(${item.id}, ${item.status})">
                            <i class="fas ${item.status === 1 ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                            <span>${item.status === 1 ? '已启用' : '已禁用'}</span>
                        </button>
                    </td>
                    <td class="actions">
                        <button class="btn btn-primary" onclick="editKnowledge(${item.id})">
                            <i class="fas fa-edit"></i> 编辑
                        </button>
                        <button class="btn btn-danger" onclick="deleteKnowledge(${item.id})">
                            <i class="fas fa-trash"></i> 删除
                        </button>
                    </td>
                </tr>
                `;
            }).join('');
        }

        // 更新分页
        function updatePagination() {
            document.getElementById('pageInfo').textContent = `第 ${currentPage} / ${totalPages} 页`;
            document.getElementById('prevBtn').disabled = currentPage === 1;
            document.getElementById('nextBtn').disabled = currentPage === totalPages || totalPages === 0;
        }

        // 更新统计
        async function updateStats() {
            try {
                // 获取所有知识（不分页）
                const response = await fetch('/api/robot/list?per_page=9999');
                const result = await response.json();
                
                if (result.code === 0) {
                    const allKnowledge = result.data.list;
                    const total = allKnowledge.length;
                    const active = allKnowledge.filter(item => item.status === 1).length;
                    const inactive = total - active;
                    
                    document.getElementById('totalCount').textContent = total;
                    document.getElementById('activeCount').textContent = active;
                    document.getElementById('inactiveCount').textContent = inactive;
                } else {
                    console.error('获取统计数据失败');
                }
            } catch (error) {
                console.error('更新统计失败:', error);
            }
        }

        // 翻页
        function changePage(delta) {
            const newPage = currentPage + delta;
            if (newPage >= 1 && newPage <= totalPages) {
                loadKnowledge(newPage);
            }
        }

        // 搜索
        function searchKnowledge() {
            searchKeyword = document.getElementById('searchInput').value;
            loadKnowledge(1);
        }

        // 重置搜索
        function resetSearch() {
            document.getElementById('searchInput').value = '';
            searchKeyword = '';
            loadKnowledge(1);
        }

        // 切换状态
        async function toggleStatus(id, currentStatus) {
            const newStatus = currentStatus === 1 ? 0 : 1;
            const statusText = newStatus === 1 ? '启用' : '禁用';
            
            modal.confirm(`确定要${statusText}这条知识吗？`, async () => {
                await performToggleStatus(id, newStatus);
            });
        }
        
        async function performToggleStatus(id, newStatus) {
            
            try {
                const response = await fetch(`/api/robot/update/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                
                const result = await response.json();
                if (result.code === 0) {
                    modal.success('操作成功');
                    loadKnowledge(currentPage);
                } else {
                    modal.error('操作失败：' + result.msg);
                }
            } catch (error) {
                modal.error('操作失败：' + error.message);
            }
        }

        // 显示添加模态框
        function showAddModal() {
            document.getElementById('modalTitle').textContent = '添加知识';
            document.getElementById('editForm').reset();
            document.getElementById('editId').value = '';
            
            // 清空Quill编辑器内容
            if (quillEditor) {
                quillEditor.root.innerHTML = '';
            }
            
            document.getElementById('editModal').style.display = 'block';
        }

        // 编辑知识
        async function editKnowledge(id) {
            try {
                const response = await fetch(`/api/robot/get/${id}`);
                const result = await response.json();

                if (result.code === 0) {
                    const data = result.data;
                    document.getElementById('modalTitle').textContent = '编辑知识';
                    document.getElementById('editId').value = data.id;
                    document.getElementById('keyword').value = data.keyword;
                    
                    // 设置Quill编辑器内容
                    if (quillEditor) {
                        quillEditor.root.innerHTML = data.reply || '';
                    }
                    
                    document.getElementById('sort').value = data.sort;
                    document.getElementById('status').checked = data.status === 1;
                    document.getElementById('editModal').style.display = 'block';
                }
            } catch (error) {
                modal.error('加载失败：' + error.message);
            }
        }

        // 关闭模态框
        function closeModal() {
            document.getElementById('editModal').style.display = 'none';
        }

        // 保存表单
        document.getElementById('editForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const id = document.getElementById('editId').value;
            
            // 从Quill编辑器获取内容
            const replyHtml = quillEditor ? quillEditor.root.innerHTML : '';
            const replyText = quillEditor ? quillEditor.getText().trim() : '';
            
            // 验证内容
            if (!replyText) {
                modal.warning('请输入回复内容');
                return;
            }
            
            const data = {
                keyword: document.getElementById('keyword').value,
                reply: replyHtml,  // HTML格式
                sort: parseInt(document.getElementById('sort').value),
                status: document.getElementById('status').checked ? 1 : 0
            };

            try {
                let response;
                if (id) {
                    // 更新
                    response = await fetch(`/api/robot/update/${id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                } else {
                    // 添加
                    response = await fetch('/api/robot/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                }

                const result = await response.json();
                if (result.code === 0) {
                    modal.success('保存成功！');
                    closeModal();
                    loadKnowledge(currentPage);
                } else {
                    modal.error('保存失败：' + result.msg);
                }
            } catch (error) {
                modal.error('保存失败：' + error.message);
            }
        });

        // 删除知识
        async function deleteKnowledge(id) {
            modal.confirm('确定要删除这条知识吗？', async () => {
                await performDelete(id);
            });
        }
        
        async function performDelete(id) {

            try {
                const response = await fetch(`/api/robot/delete/${id}`, {
                    method: 'DELETE'
                });
                const result = await response.json();

                if (result.code === 0) {
                    modal.success('删除成功！');
                    loadKnowledge(currentPage);
                } else {
                    modal.error('删除失败：' + result.msg);
                }
            } catch (error) {
                modal.error('删除失败：' + error.message);
            }
        }

        // 显示导入模态框
        function showImportModal() {
            document.getElementById('importModal').style.display = 'block';
        }

        // 关闭导入模态框
        function closeImportModal() {
            document.getElementById('importModal').style.display = 'none';
        }

        // 批量导入
        async function importKnowledge() {
            const dataText = document.getElementById('importData').value;
            
            try {
                const data = JSON.parse(dataText);
                
                const response = await fetch('/api/robot/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ data })
                });
                
                const result = await response.json();
                if (result.code === 0) {
                    modal.success(`导入成功：${result.data.count} 条`);
                    closeImportModal();
                    loadKnowledge(1);
                } else {
                    modal.error('导入失败：' + result.msg);
                }
            } catch (error) {
                modal.error('导入失败：' + error.message);
            }
        }

        // 初始化Quill富文本编辑器
        function initQuillEditor() {
            quillEditor = new Quill('#replyEditor', {
                theme: 'snow',
                modules: {
                    toolbar: [
                        ['bold', 'italic', 'underline', 'strike'],        // 基础样式
                        ['blockquote', 'code-block'],                      // 引用/代码
                        [{ 'header': 1 }, { 'header': 2 }],               // 标题
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],     // 列表
                        [{ 'color': [] }, { 'background': [] }],          // 颜色
                        [{ 'align': [] }],                                // 对齐
                        ['link', 'image'],                                // 链接/图片
                        ['clean']                                         // 清除格式
                    ]
                },
                placeholder: '请输入回复内容，支持富文本格式...'
            });
        }

        // 页面加载时初始化
        window.addEventListener('DOMContentLoaded', () => {
            // 初始化Quill编辑器
            initQuillEditor();
            
            // 加载知识库列表
            loadKnowledge(1);
        });