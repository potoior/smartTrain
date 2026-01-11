"""LLM 响应缓存管理"""

import hashlib
import json
from typing import Optional, Any, Dict, Callable, List

from app.cache.redis_manager import get_redis_manager
from app.cache.lru_cache import MultiLevelCache
from app.config import get_settings


class RedisL2Adapter:
    """Redis L2 缓存适配器"""
    
    def __init__(self, redis_manager):
        self.redis = redis_manager

    def get(self, key: str) -> Optional[Any]:
        return self.redis.get_json(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        return self.redis.set_json(key, value, ttl)

    def delete(self, key: str) -> bool:
        return self.redis.delete(key)
        
    def clear(self):
        # Redis 清理由 LLMCache.clear_all() 通过 delete_pattern 处理
        pass


class LLMCache:
    """LLM 响应缓存管理器（多级缓存）"""

    def __init__(self):
        self.redis = get_redis_manager()
        self.settings = get_settings()
        
        # 初始化多级缓存
        self.multi_cache = MultiLevelCache(
            l1_max_size=self.settings.cache_llm_l1_max_size,
            l1_ttl=self.settings.cache_llm_l1_ttl
        )
        
        # 设置二级缓存（Redis）
        self.multi_cache.set_l2_cache(RedisL2Adapter(self.redis))

    def _generate_key(self, prompt: str, model: str, temperature: float,
                      max_tokens: Optional[int] = None) -> str:
        """生成缓存键"""
        # 使用 SHA256 哈希生成唯一键
        key_data = f"{prompt}:{model}:{temperature}:{max_tokens}"
        hash_obj = hashlib.sha256(key_data.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        return f"llm:response:{hash_hex}"

    def get(self, prompt: str, model: str, temperature: float,
            max_tokens: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """从多级缓存获取 LLM 响应"""
        key = self._generate_key(prompt, model, temperature, max_tokens)
        
        # 从多级缓存获取
        cached_data = self.multi_cache.get(key)

        if cached_data:
            print(f"✅ 从缓存获取 LLM 响应 (模型: {model})")
            return cached_data

        return None

    def set(self, prompt: str, response: str, model: str, temperature: float,
            max_tokens: Optional[int] = None, ttl: Optional[int] = None) -> bool:
        """设置多级 LLM 响应缓存"""
        key = self._generate_key(prompt, model, temperature, max_tokens)
        l2_ttl = ttl or self.settings.cache_llm_ttl

        try:
            data = {
                "response": response,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "cached_at": None  # 可以添加时间戳
            }
            success = self.multi_cache.set(key, data, l2_ttl=l2_ttl)
            if success:
                print(f"✅ LLM 响应已缓存到多级缓存 (模型: {model}, L2 TTL: {l2_ttl}s)")
            return success
        except Exception as e:
            print(f"❌ LLM 响应缓存设置失败: {str(e)}")
            return False

    def delete(self, prompt: str, model: str, temperature: float,
               max_tokens: Optional[int] = None) -> bool:
        """删除指定 LLM 响应缓存"""
        key = self._generate_key(prompt, model, temperature, max_tokens)
        return self.multi_cache.delete(key)

    def delete_by_model(self, model: str) -> int:
        """删除指定模型的所有缓存"""
        pattern = f"llm:response:*"
        keys = self.redis.keys(pattern)
        
        count = 0
        for key in keys:
            cached_data = self.redis.get_json(key)
            if cached_data and cached_data.get("model") == model:
                if self.redis.delete(key):
                    count += 1

        # 同时清除 L1 缓存
        self.multi_cache.l1_cache.clear()

        if count > 0:
            print(f"✅ 已删除模型 {model} 的 {count} 条 LLM 响应缓存")
        return count

    def clear_all(self) -> int:
        """清空所有 LLM 响应缓存"""
        pattern = "llm:response:*"
        count = self.redis.delete_pattern(pattern)
        
        # 清空多级缓存
        self.multi_cache.clear()
        
        if count > 0:
            print(f"✅ 已清空 {count} 条 LLM 响应缓存")
        return count

    def get_stats(self, model: Optional[str] = None) -> dict:
        """获取缓存统计信息"""
        pattern = "llm:response:*"
        keys = self.redis.keys(pattern)

        # 统计不同模型的缓存数量
        model_counts = {}
        total_tokens = 0

        for key in keys:
            cached_data = self.redis.get_json(key)
            if cached_data:
                m = cached_data.get("model", "unknown")
                model_counts[m] = model_counts.get(m, 0) + 1

        # 获取 L1 缓存统计（避免循环引用）
        l1_stats = self.multi_cache.l1_cache.get_stats()

        return {
            "type": "llm",
            "model": model or "all",
            "cached_responses": len(keys),
            "model_distribution": model_counts,
            "keys": keys[:10],
            "multi_level_stats": {
                "l1": l1_stats,
                "l2": {
                    "type": "redis",
                    "size": len(keys),
                    "model_distribution": model_counts
                }
            }
        }

    def get_cache_info(self, prompt: str, model: str, temperature: float,
                       max_tokens: Optional[int] = None) -> dict:
        """获取缓存信息"""
        key = self._generate_key(prompt, model, temperature, max_tokens)
        return {
            "key": key,
            "l1_exists": self.multi_cache.l1_cache.exists(key),
            "l2_exists": self.redis.exists(key),
            "l2_ttl": self.redis.ttl(key) if self.redis.exists(key) else None
        }

    def get_hit_rate(self) -> Dict[str, Any]:
        """获取缓存命中率统计"""
        # 使用 Redis 的 Hash 来跟踪统计信息
        stats_key = "llm:cache:stats"
        stats = self.redis.hgetall(stats_key)

        hits = int(stats.get("hits", 0))
        misses = int(stats.get("misses", 0))
        total = hits + misses

        hit_rate = (hits / total * 100) if total > 0 else 0.0

        return {
            "hits": hits,
            "misses": misses,
            "total": total,
            "hit_rate": round(hit_rate, 2)
        }

    def record_hit(self):
        """记录缓存命中"""
        stats_key = "llm:cache:stats"
        self.redis.hincr(stats_key, "hits", 1)

    def record_miss(self):
        """记录缓存未命中"""
        stats_key = "llm:cache:stats"
        self.redis.hincr(stats_key, "misses", 1)

    def reset_stats(self):
        """重置统计信息"""
        stats_key = "llm:cache:stats"
        self.redis.delete(stats_key)

    def warm_up(self, prompts_responses: List[tuple], model: str, temperature: float,
                max_tokens: Optional[int] = None, ttl: Optional[int] = None) -> int:
        """预热 LLM 缓存 - 批量添加常用提示词的响应
        
        Args:
            prompts_responses: 提示词和响应的元组列表 [(prompt, response), ...]
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            ttl: 缓存 TTL
        
        Returns:
            成功预热的数量
        """
        success_count = 0
        for prompt, response in prompts_responses:
            if self.set(prompt, response, model, temperature, max_tokens, ttl):
                success_count += 1
                print(f"✅ 预热 LLM 缓存: {prompt[:50]}...")
        print(f"✅ LLM 缓存预热完成: {success_count}/{len(prompts_responses)} 条")
        return success_count

    def warm_up_with_fetcher(self, prompts: List[str], model: str, temperature: float,
                             max_tokens: Optional[int] = None, fetcher: Optional[Callable] = None) -> int:
        """使用 fetcher 函数预热 LLM 缓存
        
        Args:
            prompts: 提示词列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            fetcher: 数据获取函数，接收提示词，返回响应
        
        Returns:
            成功预热的数量
        """
        success_count = 0
        
        if fetcher is None:
            print("⚠️  没有提供 fetcher 函数，无法预热缓存")
            return 0
        
        for prompt in prompts:
            try:
                response = fetcher(prompt)
                if response:
                    self.set(prompt, response, model, temperature, max_tokens)
                    success_count += 1
                    print(f"✅ 预热 LLM 缓存: {prompt[:50]}...")
            except Exception as e:
                print(f"❌ 预热 LLM 缓存失败: {prompt[:50]}..., 错误: {str(e)}")
        
        print(f"✅ LLM 缓存预热完成: {success_count}/{len(prompts)} 条")
        return success_count


# 全局 LLM 缓存实例
_llm_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """获取 LLM 缓存实例"""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache
