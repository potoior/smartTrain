"""Redis 连接管理"""

import json
from typing import Optional, Any, List
from contextlib import contextmanager

import redis
from redis.connection import ConnectionPool

from app.config import get_settings


class RedisManager:
    """Redis 连接管理器"""

    _instance: Optional['RedisManager'] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        """初始化连接池"""
        settings = get_settings()

        if not settings.redis_enabled:
            print("⚠️  Redis 未启用，将使用内存缓存")
            return

        try:
            self._pool = ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                max_connections=settings.redis_max_connections,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self._client = redis.Redis(connection_pool=self._pool)
            
            # 测试连接
            self._client.ping()
            print(f"✅ Redis 连接成功: {settings.redis_host}:{settings.redis_port}")

        except Exception as e:
            print(f"❌ Redis 连接失败: {str(e)}")
            print("⚠️  将使用内存缓存")
            self._pool = None
            self._client = None

    @property
    def client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端"""
        return self._client

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        if not self.is_connected:
            return None
        try:
            return self._client.get(key)
        except Exception as e:
            print(f"❌ Redis GET 失败: {str(e)}")
            return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.is_connected:
            return False
        try:
            if ttl:
                return self._client.setex(key, ttl, value)
            else:
                return self._client.set(key, value)
        except Exception as e:
            print(f"❌ Redis SET 失败: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.is_connected:
            return False
        try:
            return bool(self._client.delete(key))
        except Exception as e:
            print(f"❌ Redis DELETE 失败: {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键"""
        if not self.is_connected:
            return 0
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            print(f"❌ Redis DELETE_PATTERN 失败: {str(e)}")
            return 0

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.is_connected:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            print(f"❌ Redis EXISTS 失败: {str(e)}")
            return False

    def keys(self, pattern: str) -> List[str]:
        """获取匹配模式的所有键"""
        if not self.is_connected:
            return []
        try:
            return self._client.keys(pattern)
        except Exception as e:
            print(f"❌ Redis KEYS 失败: {str(e)}")
            return []

    def get_json(self, key: str) -> Optional[Any]:
        """获取 JSON 数据"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析失败: {str(e)}")
                return None
        return None

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置 JSON 数据"""
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            return self.set(key, json_value, ttl)
        except Exception as e:
            print(f"❌ JSON 序列化失败: {str(e)}")
            return False

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取 Hash 字段"""
        if not self.is_connected:
            return None
        try:
            return self._client.hget(name, key)
        except Exception as e:
            print(f"❌ Redis HGET 失败: {str(e)}")
            return None

    def hset(self, name: str, key: str, value: str) -> bool:
        """设置 Hash 字段"""
        if not self.is_connected:
            return False
        try:
            return self._client.hset(name, key, value)
        except Exception as e:
            print(f"❌ Redis HSET 失败: {str(e)}")
            return False

    def hgetall(self, name: str) -> dict:
        """获取所有 Hash 字段"""
        if not self.is_connected:
            return {}
        try:
            return self._client.hgetall(name)
        except Exception as e:
            print(f"❌ Redis HGETALL 失败: {str(e)}")
            return {}

    def hdel(self, name: str, *keys: str) -> int:
        """删除 Hash 字段"""
        if not self.is_connected:
            return 0
        try:
            return self._client.hdel(name, *keys)
        except Exception as e:
            print(f"❌ Redis HDEL 失败: {str(e)}")
            return 0

    def hincr(self, name: str, key: str, amount: int = 1) -> Optional[int]:
        """递增 Hash 字段值"""
        if not self.is_connected:
            return None
        try:
            return self._client.hincrby(name, key, amount)
        except Exception as e:
            print(f"❌ Redis HINCR 失败: {str(e)}")
            return None

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增计数器"""
        if not self.is_connected:
            return None
        try:
            return self._client.incr(key, amount)
        except Exception as e:
            print(f"❌ Redis INCR 失败: {str(e)}")
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        if not self.is_connected:
            return False
        try:
            return self._client.expire(key, ttl)
        except Exception as e:
            print(f"❌ Redis EXPIRE 失败: {str(e)}")
            return False

    def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        if not self.is_connected:
            return -1
        try:
            return self._client.ttl(key)
        except Exception as e:
            print(f"❌ Redis TTL 失败: {str(e)}")
            return -1

    def flushdb(self) -> bool:
        """清空当前数据库"""
        if not self.is_connected:
            return False
        try:
            return self._client.flushdb()
        except Exception as e:
            print(f"❌ Redis FLUSHDB 失败: {str(e)}")
            return False

    def close(self):
        """关闭连接"""
        if self._pool:
            self._pool.disconnect()
            self._pool = None
            self._client = None
            print("Redis 连接已关闭")

    @contextmanager
    def pipeline(self):
        """管道上下文管理器"""
        if not self.is_connected:
            yield None
            return
        try:
            pipe = self._client.pipeline()
            yield pipe
            pipe.execute()
        except Exception as e:
            print(f"❌ Redis Pipeline 失败: {str(e)}")
            raise


# 全局 Redis 管理器实例
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """获取 Redis 管理器实例"""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


def close_redis():
    """关闭 Redis 连接"""
    global _redis_manager
    if _redis_manager:
        _redis_manager.close()
        _redis_manager = None
