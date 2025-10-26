"""
IP地理位置解析服务
支持多种解析方式：在线API、GeoIP2、纯真IP数据库
"""
import requests
import os
import log

logger = log.get_logger(__name__)


class IPLocationService:
    """IP地理位置解析服务"""
    
    def __init__(self, method='online'):
        """
        初始化IP解析服务
        
        Args:
            method: 解析方式 'online', 'geoip2', 'qqwry', 'hybrid'
        """
        self.method = method
        self.geoip2_reader = None
        self.qqwry = None
        
        # 根据方法初始化对应的解析器
        if method == 'geoip2':
            self._init_geoip2()
        elif method == 'qqwry':
            self._init_qqwry()
        elif method == 'hybrid':
            self._init_geoip2()
            if not self.geoip2_reader:
                self._init_qqwry()
    
    def _init_geoip2(self):
        """初始化GeoIP2数据库"""
        try:
            import geoip2.database
            db_path = 'data/GeoLite2-City.mmdb'
            if os.path.exists(db_path):
                self.geoip2_reader = geoip2.database.Reader(db_path)
                logger.info("GeoIP2数据库初始化成功")
            else:
                logger.warning(f"GeoIP2数据库文件不存在: {db_path}")
        except ImportError:
            logger.warning("geoip2模块未安装，使用 pip install geoip2 安装")
        except Exception as e:
            logger.error(f"GeoIP2初始化失败: {e}")
    
    def _init_qqwry(self):
        """初始化纯真IP数据库"""
        try:
            from qqwry import QQwry
            db_path = 'data/qqwry.dat'
            if os.path.exists(db_path):
                self.qqwry = QQwry()
                self.qqwry.load_file(db_path)
                logger.info("纯真IP数据库初始化成功")
            else:
                logger.warning(f"纯真IP数据库文件不存在: {db_path}")
        except ImportError:
            logger.warning("qqwry模块未安装，使用 pip install qqwry-py3 安装")
        except Exception as e:
            logger.error(f"纯真IP数据库初始化失败: {e}")
    
    def get_location(self, ip_address):
        """
        获取IP地理位置（主入口，仅支持IPv4）
        
        Args:
            ip_address: IP地址字符串（IPv4格式）
            
        Returns:
            dict: {
                'country': '中国',
                'province': '广东省',
                'city': '深圳市',
                'country_code': 'CN',
                'latitude': 22.5431,
                'longitude': 114.0579,
                'formatted': '中国 广东省 深圳市'
            }
        """
        # 过滤无效IP
        if not ip_address or ip_address in ['0.0.0.0', '127.0.0.1', '-']:
            return self._get_default_location()
        
        # 移除可能的标记（如"127.0.0.1 (本地)"）
        if ' ' in ip_address:
            ip_address = ip_address.split()[0]
        
        # 检查是否为IPv6地址（包含冒号但不是IPv4映射的IPv6）
        if ':' in ip_address and '.' not in ip_address:
            logger.warning(f"检测到IPv6地址: {ip_address}，当前仅支持IPv4地址解析")
            return self._get_default_location()
        
        # 验证IPv4格式
        import re
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ipv4_pattern, ip_address):
            logger.warning(f"无效的IPv4地址格式: {ip_address}")
            return self._get_default_location()
        
        # 根据方法选择解析方式
        if self.method == 'online':
            return self._get_location_online(ip_address)
        elif self.method == 'geoip2' and self.geoip2_reader:
            return self._get_location_geoip2(ip_address)
        elif self.method == 'qqwry' and self.qqwry:
            return self._get_location_qqwry(ip_address)
        elif self.method == 'hybrid':
            # 混合模式：优先GeoIP2，降级到纯真，最后在线API
            if self.geoip2_reader:
                result = self._get_location_geoip2(ip_address)
                if result.get('country') != '未知':
                    return result
            
            if self.qqwry:
                result = self._get_location_qqwry(ip_address)
                if result.get('country') != '未知':
                    return result
            
            return self._get_location_online(ip_address)
        else:
            # 默认使用在线API
            return self._get_location_online(ip_address)
    
    def _get_location_online(self, ip_address):
        """使用在线API获取IP地理位置"""
        # 尝试多个API（提高成功率）
        apis = [
            {
                'url': f'http://ip-api.com/json/{ip_address}?lang=zh-CN',
                'parser': self._parse_ipapi
            },
            {
                'url': f'https://ipapi.co/{ip_address}/json/',
                'parser': self._parse_ipapico
            },
            {
                'url': f'http://www.geoplugin.net/json.gp?ip={ip_address}',
                'parser': self._parse_geoplugin
            }
        ]
        
        for api in apis:
            try:
                # ⚡ 优化：超时时间从3秒降到1秒（减少阻塞）
                response = requests.get(api['url'], timeout=1)
                if response.status_code == 200:
                    data = response.json()
                    result = api['parser'](data)
                    if result.get('country') != '未知':
                        logger.info(f"在线API解析成功: {ip_address} -> {result.get('formatted')}")
                        return result
            except Exception as e:
                logger.debug(f"API请求失败 {api['url']}: {e}")
                continue
        
        logger.warning(f"所有在线API都失败，IP: {ip_address}")
        return self._get_default_location()
    
    def _parse_ipapi(self, data):
        """解析ip-api.com的响应"""
        if data.get('status') == 'success':
            return {
                'country': data.get('country', '未知'),
                'province': data.get('regionName', ''),
                'city': data.get('city', ''),
                'country_code': data.get('countryCode', ''),
                'latitude': data.get('lat'),
                'longitude': data.get('lon'),
                'formatted': f"{data.get('country', '')} {data.get('regionName', '')} {data.get('city', '')}".strip()
            }
        return self._get_default_location()
    
    def _parse_ipapico(self, data):
        """解析ipapi.co的响应"""
        if 'error' not in data:
            return {
                'country': data.get('country_name', '未知'),
                'province': data.get('region', ''),
                'city': data.get('city', ''),
                'country_code': data.get('country_code', ''),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'formatted': f"{data.get('country_name', '')} {data.get('region', '')} {data.get('city', '')}".strip()
            }
        return self._get_default_location()
    
    def _parse_geoplugin(self, data):
        """解析geoplugin.net的响应"""
        return {
            'country': data.get('geoplugin_countryName', '未知'),
            'province': data.get('geoplugin_regionName', ''),
            'city': data.get('geoplugin_city', ''),
            'country_code': data.get('geoplugin_countryCode', ''),
            'latitude': data.get('geoplugin_latitude'),
            'longitude': data.get('geoplugin_longitude'),
            'formatted': f"{data.get('geoplugin_countryName', '')} {data.get('geoplugin_regionName', '')} {data.get('geoplugin_city', '')}".strip()
        }
    
    def _get_location_geoip2(self, ip_address):
        """使用GeoIP2数据库获取IP地理位置"""
        try:
            response = self.geoip2_reader.city(ip_address)
            
            # 获取国家（优先中文）
            country = response.country.names.get('zh-CN', 
                     response.country.names.get('en', '未知'))
            
            # 获取省份/州
            province = ''
            if response.subdivisions.most_specific.name:
                province = response.subdivisions.most_specific.names.get('zh-CN',
                          response.subdivisions.most_specific.names.get('en', ''))
            
            # 获取城市
            city = ''
            if response.city.name:
                city = response.city.names.get('zh-CN',
                      response.city.names.get('en', ''))
            
            return {
                'country': country,
                'province': province,
                'city': city,
                'country_code': response.country.iso_code,
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'formatted': f"{country} {province} {city}".strip()
            }
            
        except Exception as e:
            logger.error(f"GeoIP2解析失败: {ip_address}, 错误: {e}")
            return self._get_default_location()
    
    def _get_location_qqwry(self, ip_address):
        """使用纯真IP数据库获取IP地理位置"""
        try:
            result = self.qqwry.lookup(ip_address)
            # result 格式: ('国家', '地区')
            # 例如: ('中国', '广东省深圳市')
            
            if result:
                country = result[0] if result[0] else '未知'
                region = result[1] if result[1] else ''
                
                # 尝试解析省份和城市
                province = ''
                city = ''
                if region:
                    # 简单解析：广东省深圳市 -> 广东省, 深圳市
                    if '省' in region:
                        parts = region.split('省', 1)
                        province = parts[0] + '省'
                        city = parts[1] if len(parts) > 1 else ''
                    elif '市' in region:
                        city = region
                    else:
                        province = region
                
                return {
                    'country': country,
                    'province': province,
                    'city': city,
                    'country_code': 'CN' if country == '中国' else '',
                    'latitude': None,
                    'longitude': None,
                    'formatted': f"{country} {region}".strip()
                }
        except Exception as e:
            logger.error(f"纯真IP解析失败: {ip_address}, 错误: {e}")
        
        return self._get_default_location()
    
    def _get_default_location(self):
        """返回默认的未知位置"""
        return {
            'country': '未知',
            'province': '',
            'city': '',
            'country_code': '',
            'latitude': None,
            'longitude': None,
            'formatted': '未知'
        }
    
    def __del__(self):
        """关闭数据库连接"""
        if self.geoip2_reader:
            try:
                self.geoip2_reader.close()
            except:
                pass


# 创建全局实例（默认使用在线API）
ip_location_service = IPLocationService(method='online')

