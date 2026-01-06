"""天气缓存管理"""

from typing import Optional, Dict, Any, Callable, List

from app.cache.redis_manager import get_redis_manager
from app.cache.lru_cache import MultiLevelCache
from app.config import get_settings


class WeatherCache:
    """天气缓存管理器（多级缓存）"""

    def __init__(self):
        self.redis = get_redis_manager()
        self.settings = get_settings()
        
        # 初始化多级缓存
        self.multi_cache = MultiLevelCache(
            l1_max_size=self.settings.cache_weather_l1_max_size,
            l1_ttl=self.settings.cache_weather_l1_ttl
        )
        
        # 设置二级缓存（Redis）
        self.multi_cache.set_l2_cache(self)

    def _generate_key(self, city: str, weather_type: str = "current") -> str:
        """生成缓存键"""
        return f"weather:{weather_type}:{city}"

    def get(self, city: str, weather_type: str = "current") -> Optional[Dict[str, Any]]:
        """从多级缓存获取天气数据"""
        key = self._generate_key(city, weather_type)
        
        # 从多级缓存获取
        cached_data = self.multi_cache.get(key)

        if cached_data:
            print(f"✅ 从缓存获取天气数据: {city} ({weather_type})")
            return cached_data

        return None

    def set(self, city: str, weather_data: Dict[str, Any],
            weather_type: str = "current", ttl: Optional[int] = None) -> bool:
        """设置多级天气缓存"""
        key = self._generate_key(city, weather_type)
        l2_ttl = ttl or self.settings.cache_weather_ttl

        try:
            success = self.multi_cache.set(key, weather_data, l2_ttl=l2_ttl)
            if success:
                print(f"✅ 天气数据已缓存到多级缓存: {city} ({weather_type}, L2 TTL: {l2_ttl}s)")
            return success
        except Exception as e:
            print(f"❌ 天气缓存设置失败: {str(e)}")
            return False

    def delete(self, city: str, weather_type: str = "current") -> bool:
        """删除指定天气缓存"""
        key = self._generate_key(city, weather_type)
        return self.multi_cache.delete(key)

    def delete_by_city(self, city: str) -> int:
        """删除指定城市的所有天气缓存"""
        pattern = f"weather:*:{city}"
        count = self.redis.delete_pattern(pattern)
        
        # 同时清除 L1 缓存
        self.multi_cache.l1_cache.clear()
        
        if count > 0:
            print(f"✅ 已删除 {city} 的 {count} 条天气缓存")
        return count

    def clear_all(self) -> int:
        """清空所有天气缓存"""
        pattern = "weather:*"
        count = self.redis.delete_pattern(pattern)
        
        # 清空多级缓存
        self.multi_cache.clear()
        
        if count > 0:
            print(f"✅ 已清空 {count} 条天气缓存")
        return count

    def get_stats(self, city: Optional[str] = None) -> dict:
        """获取缓存统计信息"""
        if city:
            pattern = f"weather:*:{city}"
        else:
            pattern = "weather:*"

        keys = self.redis.keys(pattern)
        
        # 统计不同类型的天气数据
        type_counts = {}
        for key in keys:
            parts = key.split(':')
            if len(parts) >= 2:
                w_type = parts[1]
                type_counts[w_type] = type_counts.get(w_type, 0) + 1

        # 获取 L1 缓存统计（避免循环引用）
        l1_stats = self.multi_cache.l1_cache.get_stats()

        return {
            "type": "weather",
            "city": city or "all",
            "cached_queries": len(keys),
            "type_distribution": type_counts,
            "keys": keys[:10],
            "multi_level_stats": {
                "l1": l1_stats,
                "l2": {
                    "type": "redis",
                    "size": len(keys),
                    "type_distribution": type_counts
                }
            }
        }

    def get_cache_info(self, city: str, weather_type: str = "current") -> dict:
        """获取缓存信息"""
        key = self._generate_key(city, weather_type)
        return {
            "key": key,
            "l1_exists": self.multi_cache.l1_cache.exists(key),
            "l2_exists": self.redis.exists(key),
            "l2_ttl": self.redis.ttl(key) if self.redis.exists(key) else None
        }

    def get_multiple_cities(self, cities: list, weather_type: str = "current") -> Dict[str, Optional[Dict[str, Any]]]:
        """批量获取多个城市的天气数据"""
        result = {}
        for city in cities:
            result[city] = self.get(city, weather_type)
        return result

    def set_multiple_cities(self, weather_data_map: Dict[str, Dict[str, Any]],
                            weather_type: str = "current", ttl: Optional[int] = None) -> int:
        """批量设置多个城市的天气数据"""
        success_count = 0
        for city, data in weather_data_map.items():
            if self.set(city, data, weather_type, ttl):
                success_count += 1
        return success_count

    def warm_up(self, cities: List[str], weather_type: str = "current", fetcher: Optional[Callable] = None) -> int:
        """预热天气缓存
        
        Args:
            cities: 城市列表
            weather_type: 天气类型
            fetcher: 数据获取函数，接收城市和天气类型，返回天气数据
        
        Returns:
            成功预热的城市数量
        """
        success_count = 0
        for city in cities:
            try:
                if fetcher:
                    weather_data = fetcher(city, weather_type)
                else:
                    # 如果没有提供 fetcher，跳过
                    continue
                
                if weather_data:
                    self.set(city, weather_data, weather_type)
                    success_count += 1
                    print(f"✅ 预热天气缓存: {city} ({weather_type})")
            except Exception as e:
                print(f"❌ 预热天气缓存失败: {city}, 错误: {str(e)}")
        
        print(f"✅ 天气缓存预热完成: {success_count}/{len(cities)} 条")
        return success_count


# 全局天气缓存实例
_weather_cache: Optional[WeatherCache] = None


def get_weather_cache() -> WeatherCache:
    """获取天气缓存实例"""
    global _weather_cache
    if _weather_cache is None:
        _weather_cache = WeatherCache()
    return _weather_cache
