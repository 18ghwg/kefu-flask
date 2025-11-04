import logging
import os
from logging import handlers
import time
import colorlog  # 彩色日志输出支持

# 全局logger缓存，避免重复创建
_logger_cache = {}

# 全局日志计数器（用于触发定期检查）
_log_count = 0
_check_interval = 500  # 每500条日志检查一次
_max_folder_size_mb = 500  # 最大文件夹大小（MB）
_target_folder_size_mb = 400  # 清理后的目标大小（MB）


class LogCleanupFilter(logging.Filter):
    """
    自定义日志过滤器，用于计数日志条目并定期触发清理检查
    """
    def __init__(self, logs_path):
        super().__init__()
        self.logs_path = logs_path
    
    def filter(self, record):
        """
        每条日志都会经过此方法，用于计数和触发检查
        
        Args:
            record: 日志记录对象
            
        Returns:
            bool: True表示允许日志通过
        """
        global _log_count
        _log_count += 1
        
        # 每500条日志检查一次
        if _log_count % _check_interval == 0:
            Logger.check_and_cleanup_if_needed(self.logs_path)
        
        return True  # 允许日志继续传递


class Logger(object):
    file_name = '/logs/' + time.strftime('%Y%m%d', time.localtime(time.time())) + '.log'
    # 获取当前的文件路径
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }  # 日志级别关系映射

    def __init__(self, level='debug', when='D', backCount=3,
                 fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'):

        # print('日志的存储路径：' + self.log_path + self.file_name)
        self.logger = logging.getLogger(name=self.file_name)
        # 日志重复打印 [ 判断是否已经有这个对象，有的话，就再重新添加]
        if not self.logger.handlers:
            # 自动创建日志文件夹（如果不存在）
            logs_dir = self.log_path + '/logs'
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
                print(f'已自动创建日志文件夹：{logs_dir}')

            # 控制台彩色输出格式（使用 colorlog）
            color_fmt = '%(log_color)s%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
            color_formatter = colorlog.ColoredFormatter(
                color_fmt,
                log_colors={
                    'DEBUG': 'cyan',         # 调试信息 - 青色
                    'INFO': 'green',         # 一般信息 - 绿色
                    'WARNING': 'yellow',     # 警告信息 - 黄色
                    'ERROR': 'red',          # 错误信息 - 红色
                    'CRITICAL': 'bold_red'   # 严重错误 - 粗体红色
                }
            )
            
            # 文件普通输出格式（不带颜色）
            file_formatter = logging.Formatter(fmt)
            
            self.logger.setLevel(self.level_relations.get(level))  # 设置日志级别
            
            # 控制台处理器（彩色输出）
            sh = logging.StreamHandler()
            sh.setFormatter(color_formatter)  # 使用彩色格式
            
            # 文件处理器（普通格式）
            th = handlers.TimedRotatingFileHandler(
                filename=self.log_path + self.file_name, 
                when=when,
                backupCount=backCount,
                encoding='utf-8'
            )
            th.setFormatter(file_formatter)  # 文件使用普通格式
            
            self.logger.addHandler(sh)  # 添加控制台处理器
            self.logger.addHandler(th)  # 添加文件处理器
            
            # 添加日志清理过滤器（用于计数和定期检查）
            cleanup_filter = LogCleanupFilter(logs_dir)
            self.logger.addFilter(cleanup_filter)
    
    @staticmethod
    def _get_logs_folder_size(logs_path):
        """
        计算logs文件夹的总大小（MB）
        
        Args:
            logs_path: logs文件夹路径
            
        Returns:
            float: 文件夹总大小（MB）
        """
        total_size = 0
        try:
            if os.path.exists(logs_path):
                for filename in os.listdir(logs_path):
                    file_path = os.path.join(logs_path, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
            return total_size / (1024 * 1024)  # 转换为MB
        except Exception as e:
            print(f'计算日志文件夹大小时出错：{e}')
            return 0
    
    @staticmethod
    def _cleanup_logs(logs_path, target_size_mb):
        """
        清理logs文件夹，删除最旧的文件直到文件夹大小降至目标大小
        
        Args:
            logs_path: logs文件夹路径
            target_size_mb: 目标大小（MB）
        """
        try:
            if not os.path.exists(logs_path):
                return
            
            # 获取所有日志文件及其修改时间
            files = []
            for filename in os.listdir(logs_path):
                file_path = os.path.join(logs_path, filename)
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    size = os.path.getsize(file_path)
                    files.append((file_path, mtime, size))
            
            # 按修改时间排序（最旧的在前）
            files.sort(key=lambda x: x[1])
            
            # 计算当前总大小
            current_size_mb = sum(f[2] for f in files) / (1024 * 1024)
            
            # 删除最旧的文件直到达到目标大小
            deleted_count = 0
            for file_path, _, size in files:
                if current_size_mb <= target_size_mb:
                    break
                try:
                    os.remove(file_path)
                    current_size_mb -= size / (1024 * 1024)
                    deleted_count += 1
                    print(f'已删除旧日志文件：{os.path.basename(file_path)}')
                except Exception as e:
                    print(f'删除文件 {file_path} 时出错：{e}')
            
            if deleted_count > 0:
                print(f'日志清理完成：删除了 {deleted_count} 个文件，当前文件夹大小：{current_size_mb:.2f}MB')
        except Exception as e:
            print(f'清理日志文件夹时出错：{e}')
    
    @staticmethod
    def check_and_cleanup_if_needed(logs_path):
        """
        检查logs文件夹大小，必要时进行清理
        
        Args:
            logs_path: logs文件夹路径
        """
        folder_size = Logger._get_logs_folder_size(logs_path)
        if folder_size > _max_folder_size_mb:
            print(f'日志文件夹大小（{folder_size:.2f}MB）超过限制（{_max_folder_size_mb}MB），开始清理...')
            Logger._cleanup_logs(logs_path, _target_folder_size_mb)


def get_logger(name=None, level='info'):
    """
    获取logger实例的便捷函数
    
    Args:
        name: logger名称，通常传入__name__
        level: 日志级别，默认'info'
    
    Returns:
        logging.Logger: 配置好的logger实例
    """
    # 使用缓存避免重复创建
    cache_key = f"{name}_{level}"
    if cache_key not in _logger_cache:
        logger_instance = Logger(level=level)
        _logger_cache[cache_key] = logger_instance.logger
    
    return _logger_cache[cache_key]


if __name__ == '__main__':
    # 测试Logger类
    log = Logger()
    log.logger.debug('debug')
    log.logger.info('info')
    log.logger.warning('警告')
    log.logger.error('报错')
    log.logger.critical('严重')
    
    # 测试get_logger函数
    print("\n测试 get_logger 函数：")
    test_logger = get_logger(__name__)
    test_logger.debug('get_logger - debug')
    test_logger.info('get_logger - info')
    test_logger.warning('get_logger - 警告')
    test_logger.error('get_logger - 报错')
    test_logger.critical('get_logger - 严重')
