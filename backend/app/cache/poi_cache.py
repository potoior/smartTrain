"""POI 缓存管理"""

from typing import Optional, List

from app.cache.redis_manager import get_redis_manager
from app.models.schemas import POIInfo
from app.config import get_settings


class POICache:
    """POI 缓存管理器"""

    def __init__(self):
        self.redis = get_redis_manager()
        self.settings = get_settings()

    def _generate_key(self, city: str, keywords: str, citylimit: bool) -> str:
        """生成缓存键"""
        return f"poi:search:{city}:{keywords}:{citylimit}"

    def get(self, city: str, keywords: str, citylimit: bool) -> Optional[List[POIInfo]]:
        """从缓存获取 POI"""
        key = self._generate_key(city, keywords, citylimit)
        cached_data = self.redis.get_json(key)

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
        """设置 POI 缓存"""
        key = self._generate_key(city, keywords, citylimit)
        ttl = ttl or self.settings.cache_poi_ttl

        try:
            data = [poi.model_dump() for poi in pois]
            success = self.redis.set_json(key, data, ttl)
            if success:
                print(f"✅ POI 已缓存 (TTL: {ttl}s)")
            return success
        except Exception as e:
            print(f"❌ POI 缓存设置失败: {str(e)}")
            return False

    def delete(self, city: str, keywords: str, citylimit: bool) -> bool:
        """删除指定 POI 缓存"""
        key = self._generate_key(city, keywords, citylimit)
        return self.redis.delete(key)

    def delete_by_city(self, city: str) -> int:
        """删除指定城市的所有 POI 缓存"""
        pattern = f"poi:search:{city}:*"
        count = self.redis.delete_pattern(pattern)
        if count > 0:
            print(f"✅ 已删除 {city} 的 {count} 条 POI 缓存")
        return count

    def clear_all(self) -> int:
        """清空所有 POI 缓存"""
        pattern = "poi:search:*"
        count = self.redis.delete_pattern(pattern)
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
        return {
            "type": "poi",
            "city": city or "all",
            "cached_queries": len(keys),
            "keys": keys[:10]  # 只返回前10个键
        }

    def get_cache_info(self, city: str, keywords: str, citylimit: bool) -> dict:
        """获取缓存信息"""
        key = self._generate_key(city, keywords, citylimit)
        return {
            "key": key,
            "exists": self.redis.exists(key),
            "ttl": self.redis.ttl(key) if self.redis.exists(key) else None
        }


# 全局 POI 缓存实例
_poi_cache: Optional[POICache] = None


def get_poi_cache() -> POICache:
    """获取 POI 缓存实例"""
    global _poi_cache
    if _poi_cache is None:
        _poi_cache = POICache()
    return _poi_cache
