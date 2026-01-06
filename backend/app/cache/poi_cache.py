"""POI 缓存管理"""

from typing import Optional, List, Callable

from app.cache.redis_manager import get_redis_manager
from app.cache.lru_cache import MultiLevelCache
from app.models.schemas import POIInfo
from app.config import get_settings


class POICache:
    """POI 缓存管理器（多级缓存）"""

    def __init__(self):
        self.redis = get_redis_manager()
        self.settings = get_settings()
        
        # 初始化多级缓存
        self.multi_cache = MultiLevelCache(
            l1_max_size=self.settings.cache_poi_l1_max_size,
            l1_ttl=self.settings.cache_poi_l1_ttl
        )
        
        # 设置二级缓存（Redis）
        self.multi_cache.set_l2_cache(self)

    def _generate_key(self, city: str, keywords: str, citylimit: bool) -> str:
        """生成缓存键"""
        return f"poi:search:{city}:{keywords}:{citylimit}"

    def get(self, city: str, keywords: str, citylimit: bool) -> Optional[List[POIInfo]]:
        """从多级缓存获取 POI"""
        key = self._generate_key(city, keywords, citylimit)
        
        # 从多级缓存获取
        cached_data = self.multi_cache.get(key)
        
        if cached_data:
            try:
                pois = [POIInfo(**item) for item in cached_data]
                print(f"✅ 从缓存获取 POI: {len(pois)} 个")
                return pois
            except Exception as e:
                print(f"❌ POI 缓存数据解析失败: {str(e)}")
                return None

        return None

    def set(self, city: str, keywords: str, citylimit: bool,
            pois: List[POIInfo], ttl: Optional[int] = None) -> bool:
        """设置多级 POI 缓存"""
        key = self._generate_key(city, keywords, citylimit)
        l2_ttl = ttl or self.settings.cache_poi_ttl

        try:
            data = [poi.model_dump() for poi in pois]
            success = self.multi_cache.set(key, data, l2_ttl=l2_ttl)
            if success:
                print(f"✅ POI 已缓存到多级缓存 (L2 TTL: {l2_ttl}s)")
            return success
        except Exception as e:
            print(f"❌ POI 缓存设置失败: {str(e)}")
            return False

    def delete(self, city: str, keywords: str, citylimit: bool) -> bool:
        """删除指定 POI 缓存"""
        key = self._generate_key(city, keywords, citylimit)
        return self.multi_cache.delete(key)

    def delete_by_city(self, city: str) -> int:
        """删除指定城市的所有 POI 缓存"""
        pattern = f"poi:search:{city}:*"
        count = self.redis.delete_pattern(pattern)
        
        # 同时清除 L1 缓存
        self.multi_cache.l1_cache.clear()
        
        if count > 0:
            print(f"✅ 已删除 {city} 的 {count} 条 POI 缓存")
        return count

    def clear_all(self) -> int:
        """清空所有 POI 缓存"""
        pattern = "poi:search:*"
        count = self.redis.delete_pattern(pattern)
        
        # 清空多级缓存
        self.multi_cache.clear()
        
        if count > 0:
            print(f"✅ 已清空 {count} 条 POI 缓存")
        return count

    def get_stats(self, city: Optional[str] = None) -> dict:
        """获取缓存统计信息"""
        if city:
            pattern = f"poi:search:{city}:*"
        else:
            pattern = "poi:search:*"

        keys = self.redis.keys(pattern)
        
        # 获取 L1 缓存统计（避免循环引用）
        l1_stats = self.multi_cache.l1_cache.get_stats()
        
        return {
            "type": "poi",
            "city": city or "all",
            "cached_queries": len(keys),
            "keys": keys[:10],
            "multi_level_stats": {
                "l1": l1_stats,
                "l2": {
                    "type": "redis",
                    "size": len(keys)
                }
            }
        }

    def get_cache_info(self, city: str, keywords: str, citylimit: bool) -> dict:
        """获取缓存信息"""
        key = self._generate_key(city, keywords, citylimit)
        return {
            "key": key,
            "l1_exists": self.multi_cache.l1_cache.exists(key),
            "l2_exists": self.redis.exists(key),
            "l2_ttl": self.redis.ttl(key) if self.redis.exists(key) else None
        }

    def warm_up(self, queries: List[dict], fetcher: Callable) -> int:
        """预热 POI 缓存
        
        Args:
            queries: 查询列表，每个元素包含 city, keywords, citylimit
            fetcher: 数据获取函数，接收查询参数，返回 POI 列表
        
        Returns:
            成功预热的查询数量
        """
        success_count = 0
        for query in queries:
            city = query.get('city')
            keywords = query.get('keywords')
            citylimit = query.get('citylimit', True)
            
            try:
                pois = fetcher(city, keywords, citylimit)
                if pois:
                    self.set(city, keywords, citylimit, pois)
                    success_count += 1
                    print(f"✅ 预热 POI 缓存: {city} - {keywords}")
            except Exception as e:
                print(f"❌ 预热 POI 缓存失败: {city} - {keywords}, 错误: {str(e)}")
        
        print(f"✅ POI 缓存预热完成: {success_count}/{len(queries)} 条")
        return success_count


# 全局 POI 缓存实例
_poi_cache: Optional[POICache] = None


def get_poi_cache() -> POICache:
    """获取 POI 缓存实例"""
    global _poi_cache
    if _poi_cache is None:
        _poi_cache = POICache()
    return _poi_cache
