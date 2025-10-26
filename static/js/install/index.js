let currentStep = 1;
let envCheckPassed = false;
let dbConfigPassed = false;
let missingPackages = [];

// 页面加载时自动检测环境
window.onload = function() {
    checkEnvironment();
};

// 切换步骤
function nextStep(step) {
    document.getElementById(`step${currentStep}`).style.display = 'none';
    document.getElementById(`step${step}`).style.display = 'block';
    
    // 更新步骤指示器
    document.querySelectorAll('.step').forEach(s => {
        const stepNum = parseInt(s.getAttribute('data-step'));
        if (stepNum < step) {
            s.classList.add('completed');
            s.classList.remove('active');
        } else if (stepNum === step) {
            s.classList.add('active');
            s.classList.remove('completed');
        } else {
            s.classList.remove('active', 'completed');
        }
    });
    
    currentStep = step;
}

function prevStep(step) {
    nextStep(step);
}

// 检查环境
function checkEnvironment() {
    const resultsDiv = document.getElementById('envCheckResults');
    resultsDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> 正在检测...</div>';
    
    fetch('/install/check-environment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0) {
            displayEnvResults(data.data);
            
            if (data.data.all_packages_installed) {
                document.getElementById('nextStep1').disabled = false;
                envCheckPassed = true;
            } else {
                missingPackages = data.data.missing_packages;
                document.getElementById('missingPackages').style.display = 'block';
                const ul = document.getElementById('missingPackageList');
                ul.innerHTML = '';
                missingPackages.forEach(pkg => {
                    ul.innerHTML += `<li><i class="fas fa-times-circle"></i> ${pkg}</li>`;
                });
            }
        } else {
            resultsDiv.innerHTML = `<div class="error-box">检测失败: ${data.msg}</div>`;
        }
    })
    .catch(error => {
        resultsDiv.innerHTML = `<div class="error-box">检测失败: ${error}</div>`;
    });
}

// 显示环境检测结果
function displayEnvResults(data) {
    const resultsDiv = document.getElementById('envCheckResults');
    let html = '';
    
    data.checks.forEach(check => {
        const icon = check.status === 'success' ? 'fa-check-circle' : 'fa-times-circle';
        html += `
            <div class="check-item ${check.status}">
                <div class="icon">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="info">
                    <div class="name">${check.name}</div>
                    <div class="message">${check.message} - ${check.requirement}</div>
                </div>
            </div>
        `;
    });
    
    resultsDiv.innerHTML = html;
}

// 一键安装缺失的包
function installMissingPackages() {
    const progressDiv = document.getElementById('installProgress');
    const progressFill = document.getElementById('progressFill');
    progressDiv.style.display = 'block';
    progressFill.style.width = '0%';
    
    fetch('/install/install-packages', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            packages: missingPackages
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0) {
            progressFill.style.width = '100%';
            setTimeout(() => {
                modal.success('所有包安装成功！正在重新检测环境...');
                checkEnvironment();
            }, 500);
        } else {
            modal.error(`安装失败: ${data.msg}\n成功: ${data.data.success_count}/${data.data.total_count}`);
        }
    })
    .catch(error => {
        modal.error(`安装失败: ${error}`);
    });
}

// 测试数据库连接
function testDatabase() {
    const dbHost = document.getElementById('db_host').value;
    const dbPort = document.getElementById('db_port').value;
    const dbUser = document.getElementById('db_user').value;
    const dbPassword = document.getElementById('db_password').value;
    const dbName = document.getElementById('db_name').value;
    
    const resultDiv = document.getElementById('dbTestResult');
    resultDiv.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> 正在测试连接...</div>';
    
    fetch('/install/test-database', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            db_host: dbHost,
            db_port: dbPort,
            db_user: dbUser,
            db_password: dbPassword,
            db_name: dbName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0 && data.data.connected) {
            if (!data.data.db_exists) {
                resultDiv.innerHTML = `
                    <div class="warning-box">
                        <h3><i class="fas fa-exclamation-triangle"></i> 数据库不存在</h3>
                        <p>数据库 "${dbName}" 不存在，是否创建？</p>
                        <button class="btn btn-success" onclick="createDatabase()">
                            <i class="fas fa-plus"></i> 创建数据库
                        </button>
                    </div>
                `;
            } else {
                resultDiv.innerHTML = `
                    <div class="success-box">
                        <h3><i class="fas fa-check-circle"></i> 连接成功</h3>
                        <p>数据库连接正常，可以继续下一步</p>
                    </div>
                `;
                document.getElementById('nextStep2').disabled = false;
                dbConfigPassed = true;
            }
        } else {
            resultDiv.innerHTML = `
                <div class="warning-box" style="border-color: #ef4444; background: #fee2e2;">
                    <h3 style="color: #991b1b;"><i class="fas fa-times-circle"></i> 连接失败</h3>
                    <p style="color: #991b1b;">${data.data.message}</p>
                </div>
            `;
        }
    })
    .catch(error => {
        resultDiv.innerHTML = `
            <div class="warning-box" style="border-color: #ef4444; background: #fee2e2;">
                <h3 style="color: #991b1b;"><i class="fas fa-times-circle"></i> 连接失败</h3>
                <p style="color: #991b1b;">${error}</p>
            </div>
        `;
    });
}

// 创建数据库
function createDatabase() {
    const dbHost = document.getElementById('db_host').value;
    const dbPort = document.getElementById('db_port').value;
    const dbUser = document.getElementById('db_user').value;
    const dbPassword = document.getElementById('db_password').value;
    const dbName = document.getElementById('db_name').value;
    
    fetch('/install/create-database', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            db_host: dbHost,
            db_port: dbPort,
            db_user: dbUser,
            db_password: dbPassword,
            db_name: dbName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0) {
            modal.success(data.msg);
            testDatabase();  // 重新测试连接
        } else {
            modal.error(`创建失败: ${data.msg}`);
        }
    })
    .catch(error => {
        modal.error(`创建失败: ${error}`);
    });
}

// 开始安装
function startInstall() {
    const adminUsername = document.getElementById('admin_username').value;
    const adminPassword = document.getElementById('admin_password').value;
    const adminPasswordConfirm = document.getElementById('admin_password_confirm').value;
    const adminEmail = document.getElementById('admin_email').value;
    
    // 验证表单
    if (!adminUsername || !adminPassword || !adminEmail) {
        modal.warning('请填写完整的管理员信息');
        return;
    }
    
    if (adminPassword !== adminPasswordConfirm) {
        modal.warning('两次输入的密码不一致');
        return;
    }
    
    if (adminPassword.length < 6) {
        modal.warning('密码长度至少为6位');
        return;
    }
    
    // 切换到安装步骤
    nextStep(4);
    
    const logsDiv = document.getElementById('installLogs');
    
    function addLog(message, type = 'info') {
        const log = document.createElement('div');
        log.className = `log-item ${type}`;
        log.innerHTML = `<i class="fas fa-chevron-right"></i> ${message}`;
        logsDiv.appendChild(log);
        logsDiv.scrollTop = logsDiv.scrollHeight;
    }
    
    addLog('开始安装系统...', 'info');
    addLog('正在初始化数据库...', 'info');
    
    // 获取数据库配置
    const dbHost = document.getElementById('db_host').value;
    const dbPort = document.getElementById('db_port').value;
    const dbUser = document.getElementById('db_user').value;
    const dbPassword = document.getElementById('db_password').value;
    const dbName = document.getElementById('db_name').value;
    
    // 初始化数据库
    fetch('/install/initialize-database', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            db_host: dbHost,
            db_port: dbPort,
            db_user: dbUser,
            db_password: dbPassword,
            db_name: dbName,
            admin_username: adminUsername,
            admin_password: adminPassword,
            admin_email: adminEmail
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0) {
            addLog('数据库初始化成功', 'success');
            addLog('正在创建管理员账号...', 'info');
            addLog(`管理员账号创建成功: ${adminUsername}`, 'success');
            addLog('正在完成安装...', 'info');
            
            // 完成安装
            return fetch('/install/complete-install', {
                method: 'POST'
            });
        } else {
            addLog(`安装失败: ${data.msg}`, 'error');
            throw new Error(data.msg);
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 0) {
            addLog('安装完成！', 'success');
            
            // 显示完成信息
            document.getElementById('finalUsername').textContent = adminUsername;
            document.getElementById('finalPassword').textContent = adminPassword;
            document.getElementById('installComplete').style.display = 'block';
        } else {
            addLog(`完成安装失败: ${data.msg}`, 'error');
        }
    })
    .catch(error => {
        addLog(`安装失败: ${error}`, 'error');
    });
}
