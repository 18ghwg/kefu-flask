import logging
import os
from logging import handlers
import time
import colorlog  # 彩色日志输出支持

# 全局logger缓存，避免重复创建
_logger_cache = {}


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
