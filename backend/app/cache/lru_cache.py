"""LRU 内存缓存管理"""

import time
from collections import OrderedDict
from typing import Optional, Any, Dict, List, Callable
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """LRU 缓存实现"""

    def __init__(self, max_size: int = 1000, ttl: Optional[int] = None):
        self.max_size = max_size
        self.ttl = ttl  # 默认 TTL（秒）
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.lock = Lock()
        self.hits = 0
        self.misses = 0

    def _is_expired(self, key: str) -> bool:
        """检查缓存是否过期"""
        if self.ttl is None:
            return False
        if key not in self.timestamps:
            return False
        return time.time() - self.timestamps[key] > self.ttl

    def _evict_expired(self):
        """清理过期缓存"""
        expired_keys = [k for k in self.cache.keys() if self._is_expired(k)]
        for key in expired_keys:
            del self.cache[key]
            del self.timestamps[key]
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存项")

    def _evict_lru(self):
        """淘汰最近最少使用的缓存项"""
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
            logger.debug(f"淘汰 LRU 缓存项: {oldest_key}")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            self._evict_expired()

            if key not in self.cache:
                self.misses += 1
                return None

            if self._is_expired(key):
                del self.cache[key]
                del self.timestamps[key]
                self.misses += 1
                return None

            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self.lock:
            self._evict_expired()
            self._evict_lru()

            if key in self.cache:
                self.cache.pop(key)

            self.cache[key] = value
            self.timestamps[key] = time.time()

            if ttl is not None:
                self.timestamps[key] = time.time() - self.ttl + ttl

            return True

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
                return True
            return False

    def clear(self):
        """清空所有缓存"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(hit_rate, 2),
                "ttl": self.ttl
            }

    def get_keys(self) -> List[str]:
        """获取所有缓存键"""
        with self.lock:
            return list(self.cache.keys())

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self.lock:
            return key in self.cache and not self._is_expired(key)


class MultiLevelCache:
    """多级缓存管理器"""

    def __init__(self, l1_max_size: int = 1000, l1_ttl: Optional[int] = None):
        self.l1_cache = LRUCache(max_size=l1_max_size, ttl=l1_ttl)
        self.l2_cache = None  # 将在初始化时设置（Redis 缓存）
        self.l3_fetcher = None  # 数据获取函数

    def set_l2_cache(self, l2_cache: Any):
        """设置二级缓存（Redis）"""
        self.l2_cache = l2_cache

    def set_l3_fetcher(self, fetcher: Callable):
        """设置三级数据获取函数"""
        self.l3_fetcher = fetcher

    def get(self, key: str, use_l1: bool = True, use_l2: bool = True) -> Optional[Any]:
        """从多级缓存获取数据"""
        if use_l1:
            value = self.l1_cache.get(key)
            if value is not None:
                logger.debug(f"L1 缓存命中: {key}")
                return value

        if use_l2 and self.l2_cache:
            value = self.l2_cache.get(key)
            if value is not None:
                logger.debug(f"L2 缓存命中: {key}")
                self.l1_cache.set(key, value)
                return value

        if self.l3_fetcher:
            logger.debug(f"L3 数据获取: {key}")
            value = self.l3_fetcher(key)
            if value is not None:
                self.l1_cache.set(key, value)
                if self.l2_cache:
                    self.l2_cache.set(key, value)
            return value

        return None

    def set(self, key: str, value: Any, l1_ttl: Optional[int] = None, l2_ttl: Optional[int] = None) -> bool:
        """设置多级缓存"""
        success = True
        self.l1_cache.set(key, value, ttl=l1_ttl)

        if self.l2_cache:
            if not self.l2_cache.set(key, value, ttl=l2_ttl):
                success = False

        return success

    def delete(self, key: str) -> bool:
        """删除多级缓存"""
        success = True
        self.l1_cache.delete(key)

        if self.l2_cache:
            if not self.l2_cache.delete(key):
                success = False

        return success

    def clear(self, clear_l1: bool = True, clear_l2: bool = True):
        """清空多级缓存"""
        if clear_l1:
            self.l1_cache.clear()

        if clear_l2 and self.l2_cache:
            self.l2_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取多级缓存统计信息"""
        stats = {
            "l1": self.l1_cache.get_stats(),
            "l2": {}
        }

        if self.l2_cache and hasattr(self.l2_cache, 'get_stats'):
            stats["l2"] = self.l2_cache.get_stats()

        return stats

    def warm_up(self, keys: List[str], fetcher: Optional[Callable] = None) -> int:
        """预热缓存"""
        success_count = 0
        actual_fetcher = fetcher or self.l3_fetcher

        if actual_fetcher is None:
            logger.warning("没有可用的数据获取函数，无法预热缓存")
            return 0

        for key in keys:
            value = actual_fetcher(key)
            if value is not None:
                self.set(key, value)
                success_count += 1
                logger.debug(f"预热缓存: {key}")

        logger.info(f"缓存预热完成: {success_count}/{len(keys)} 条")
        return success_count
