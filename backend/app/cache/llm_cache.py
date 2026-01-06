"""LLM 响应缓存管理"""

import hashlib
import json
from typing import Optional, Any, Dict

from app.cache.redis_manager import get_redis_manager
from app.config import get_settings


class LLMCache:
    """LLM 响应缓存管理器"""

    def __init__(self):
        self.redis = get_redis_manager()
        self.settings = get_settings()

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
        """从缓存获取 LLM 响应"""
        key = self._generate_key(prompt, model, temperature, max_tokens)
        cached_data = self.redis.get_json(key)

        if cached_data:
            print(f"✅ 从缓存获取 LLM 响应 (模型: {model})")
            return cached_data

        return None

    def set(self, prompt: str, response: str, model: str, temperature: float,
            max_tokens: Optional[int] = None, ttl: Optional[int] = None) -> bool:
        """设置 LLM 响应缓存"""
        key = self._generate_key(prompt, model, temperature, max_tokens)
        ttl = ttl or self.settings.cache_llm_ttl

        try:
            data = {
                "response": response,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "cached_at": None  # 可以添加时间戳
            }
            success = self.redis.set_json(key, data, ttl)
            if success:
                print(f"✅ LLM 响应已缓存 (模型: {model}, TTL: {ttl}s)")
            return success
        except Exception as e:
            print(f"❌ LLM 响应缓存设置失败: {str(e)}")
            return False

    def delete(self, prompt: str, model: str, temperature: float,
               max_tokens: Optional[int] = None) -> bool:
        """删除指定 LLM 响应缓存"""
        key = self._generate_key(prompt, model, temperature, max_tokens)
        return self.redis.delete(key)

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

        if count > 0:
            print(f"✅ 已删除模型 {model} 的 {count} 条 LLM 响应缓存")
        return count

    def clear_all(self) -> int:
        """清空所有 LLM 响应缓存"""
        pattern = "llm:response:*"
        count = self.redis.delete_pattern(pattern)
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

        return {
            "type": "llm",
            "model": model or "all",
            "cached_responses": len(keys),
            "model_distribution": model_counts,
            "keys": keys[:10]  # 只返回前10个键
        }

    def get_cache_info(self, prompt: str, model: str, temperature: float,
                       max_tokens: Optional[int] = None) -> dict:
        """获取缓存信息"""
        key = self._generate_key(prompt, model, temperature, max_tokens)
        return {
            "key": key,
            "exists": self.redis.exists(key),
            "ttl": self.redis.ttl(key) if self.redis.exists(key) else None
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

    def warm_up(self, prompts_responses: list, model: str, temperature: float,
                max_tokens: Optional[int] = None, ttl: Optional[int] = None) -> int:
        """预热缓存 - 批量添加常用提示词的响应"""
        success_count = 0
        for prompt, response in prompts_responses:
            if self.set(prompt, response, model, temperature, max_tokens, ttl):
                success_count += 1
        print(f"✅ 缓存预热完成: {success_count}/{len(prompts_responses)} 条")
        return success_count


# 全局 LLM 缓存实例
_llm_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """获取 LLM 缓存实例"""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache
