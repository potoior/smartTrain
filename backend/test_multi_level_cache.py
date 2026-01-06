"""测试多级缓存和缓存预热功能"""

import asyncio
import time
from typing import Optional, Dict, Any


async def test_lru_cache():
    """测试 LRU 缓存"""
    print("\n" + "=" * 60)
    print("测试 LRU 缓存")
    print("=" * 60)
    
    try:
        from app.cache.lru_cache import LRUCache
        
        # 创建 LRU 缓存
        lru_cache = LRUCache(max_size=5, ttl=10)
        
        # 测试设置和获取
        print("测试基本操作...")
        lru_cache.set("key1", "value1")
        lru_cache.set("key2", "value2")
        lru_cache.set("key3", "value3")
        
        assert lru_cache.get("key1") == "value1", "获取 key1 失败"
        assert lru_cache.get("key2") == "value2", "获取 key2 失败"
        assert lru_cache.get("key3") == "value3", "获取 key3 失败"
        print("✅ 基本操作测试通过")
        
        # 测试 LRU 淘汰
        print("\n测试 LRU 淘汰...")
        lru_cache.set("key4", "value4")
        lru_cache.set("key5", "value5")
        lru_cache.set("key6", "value6")  # 应该淘汰 key1
        
        assert lru_cache.get("key1") is None, "key1 应该被淘汰"
        assert lru_cache.get("key6") == "value6", "获取 key6 失败"
        print("✅ LRU 淘汰测试通过")
        
        # 测试 TTL 过期
        print("\n测试 TTL 过期...")
        lru_cache.set("temp_key", "temp_value", ttl=1)
        assert lru_cache.get("temp_key") == "temp_value", "获取 temp_key 失败"
        time.sleep(2)
        assert lru_cache.get("temp_key") is None, "temp_key 应该过期"
        print("✅ TTL 过期测试通过")
        
        # 测试统计信息
        print("\n测试统计信息...")
        stats = lru_cache.get_stats()
        print(f"   缓存统计: {stats}")
        assert stats["size"] > 0, "缓存大小应该大于 0"
        assert stats["max_size"] == 5, "最大缓存大小应该是 5"
        print("✅ 统计信息测试通过")
        
        print("\n✅ LRU 缓存测试全部通过")
        return True
        
    except Exception as e:
        print(f"\n❌ LRU 缓存测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_level_cache():
    """测试多级缓存"""
    print("\n" + "=" * 60)
    print("测试多级缓存")
    print("=" * 60)
    
    try:
        from app.cache.lru_cache import MultiLevelCache, LRUCache
        
        # 创建多级缓存
        multi_cache = MultiLevelCache(l1_max_size=10, l1_ttl=300)
        
        # 创建模拟的 L2 缓存
        class MockL2Cache:
            def __init__(self):
                self.cache = {}
            
            def get(self, key):
                return self.cache.get(key)
            
            def set(self, key, value, ttl=None):
                self.cache[key] = value
                return True
            
            def delete(self, key):
                if key in self.cache:
                    del self.cache[key]
                    return True
                return False
            
            def clear(self):
                self.cache.clear()
            
            def get_stats(self):
                return {"size": len(self.cache)}
        
        l2_cache = MockL2Cache()
        multi_cache.set_l2_cache(l2_cache)
        
        # 测试 L1 缓存命中
        print("测试 L1 缓存命中...")
        multi_cache.set("key1", "value1")
        value = multi_cache.get("key1")
        assert value == "value1", "L1 缓存获取失败"
        print("✅ L1 缓存命中测试通过")
        
        # 测试 L2 缓存命中
        print("\n测试 L2 缓存命中...")
        multi_cache.l1_cache.clear()  # 清空 L1 缓存
        value = multi_cache.get("key1")
        assert value == "value1", "L2 缓存获取失败"
        # 检查是否回填到 L1
        assert multi_cache.l1_cache.get("key1") == "value1", "应该回填到 L1 缓存"
        print("✅ L2 缓存命中测试通过")
        
        # 测试 L3 数据获取
        print("\n测试 L3 数据获取...")
        def fetcher(key):
            return f"fetched_{key}"
        
        multi_cache.set_l3_fetcher(fetcher)
        multi_cache.l1_cache.clear()
        l2_cache.cache.clear()
        
        value = multi_cache.get("key2")
        assert value == "fetched_key2", "L3 数据获取失败"
        # 检查是否缓存到 L1 和 L2
        assert multi_cache.l1_cache.get("key2") == "fetched_key2", "应该缓存到 L1"
        assert l2_cache.get("key2") == "fetched_key2", "应该缓存到 L2"
        print("✅ L3 数据获取测试通过")
        
        # 测试缓存预热
        print("\n测试缓存预热...")
        multi_cache.l1_cache.clear()
        l2_cache.cache.clear()
        
        keys = ["key3", "key4", "key5"]
        count = multi_cache.warm_up(keys, fetcher)
        assert count == 3, f"应该预热 3 个键，实际预热了 {count} 个"
        
        # 验证缓存
        for key in keys:
            assert multi_cache.l1_cache.get(key) == f"fetched_{key}", f"{key} 应该在 L1 缓存中"
            assert l2_cache.get(key) == f"fetched_{key}", f"{key} 应该在 L2 缓存中"
        print("✅ 缓存预热测试通过")
        
        # 测试多级缓存统计
        print("\n测试多级缓存统计...")
        stats = multi_cache.get_stats()
        print(f"   多级缓存统计: {stats}")
        assert "l1" in stats, "应该包含 L1 统计"
        assert "l2" in stats, "应该包含 L2 统计"
        print("✅ 多级缓存统计测试通过")
        
        print("\n✅ 多级缓存测试全部通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 多级缓存测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_poi_cache_multi_level():
    """测试 POI 多级缓存"""
    print("\n" + "=" * 60)
    print("测试 POI 多级缓存")
    print("=" * 60)
    
    try:
        from app.cache import get_poi_cache
        from app.models.schemas import POIInfo
        
        poi_cache = get_poi_cache()
        
        # 测试多级缓存设置和获取
        print("测试多级缓存设置和获取...")
        pois = [
            POIInfo(id="1", name="测试景点1", type="景点", address="测试地址1", location={"longitude": 116.40, "latitude": 39.90}),
            POIInfo(id="2", name="测试景点2", type="景点", address="测试地址2", location={"longitude": 116.41, "latitude": 39.91})
        ]
        
        poi_cache.set("北京", "故宫", True, pois)
        cached_pois = poi_cache.get("北京", "故宫", True)
        
        assert cached_pois is not None, "缓存获取失败"
        assert len(cached_pois) == 2, f"应该有 2 个 POI，实际有 {len(cached_pois)} 个"
        print("✅ 多级缓存设置和获取测试通过")
        
        # 测试缓存信息
        print("\n测试缓存信息...")
        cache_info = poi_cache.get_cache_info("北京", "故宫", True)
        print(f"   缓存信息: {cache_info}")
        assert "l1_exists" in cache_info, "应该包含 L1 存在信息"
        assert "l2_exists" in cache_info, "应该包含 L2 存在信息"
        print("✅ 缓存信息测试通过")
        
        # 测试统计信息
        print("\n测试统计信息...")
        stats = poi_cache.get_stats()
        print(f"   POI 缓存统计: {stats}")
        assert "multi_level_stats" in stats, "应该包含多级缓存统计"
        print("✅ 统计信息测试通过")
        
        print("\n✅ POI 多级缓存测试全部通过")
        return True
        
    except Exception as e:
        print(f"\n❌ POI 多级缓存测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_weather_cache_multi_level():
    """测试天气多级缓存"""
    print("\n" + "=" * 60)
    print("测试天气多级缓存")
    print("=" * 60)
    
    try:
        from app.cache import get_weather_cache
        
        weather_cache = get_weather_cache()
        
        # 测试多级缓存设置和获取
        print("测试多级缓存设置和获取...")
        weather_data = {
            "city": "北京",
            "temperature": "25°C",
            "weather": "晴",
            "humidity": "60%"
        }
        
        weather_cache.set("北京", weather_data)
        cached_weather = weather_cache.get("北京")
        
        assert cached_weather is not None, "缓存获取失败"
        assert cached_weather["city"] == "北京", "城市应该匹配"
        print("✅ 多级缓存设置和获取测试通过")
        
        # 测试缓存信息
        print("\n测试缓存信息...")
        cache_info = weather_cache.get_cache_info("北京")
        print(f"   缓存信息: {cache_info}")
        assert "l1_exists" in cache_info, "应该包含 L1 存在信息"
        assert "l2_exists" in cache_info, "应该包含 L2 存在信息"
        print("✅ 缓存信息测试通过")
        
        # 测试统计信息
        print("\n测试统计信息...")
        stats = weather_cache.get_stats()
        print(f"   天气缓存统计: {stats}")
        assert "multi_level_stats" in stats, "应该包含多级缓存统计"
        print("✅ 统计信息测试通过")
        
        print("\n✅ 天气多级缓存测试全部通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 天气多级缓存测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_llm_cache_multi_level():
    """测试 LLM 多级缓存"""
    print("\n" + "=" * 60)
    print("测试 LLM 多级缓存")
    print("=" * 60)
    
    try:
        from app.cache import get_llm_cache
        
        llm_cache = get_llm_cache()
        
        # 测试多级缓存设置和获取
        print("测试多级缓存设置和获取...")
        prompt = "北京有哪些著名的旅游景点？"
        response = "北京有许多著名的旅游景点，包括故宫、天安门广场、长城等。"
        model = "deepseek-chat"
        
        llm_cache.set(prompt, response, model, 0.7)
        cached_response = llm_cache.get(prompt, model, 0.7)
        
        assert cached_response is not None, "缓存获取失败"
        assert cached_response["response"] == response, "响应应该匹配"
        print("✅ 多级缓存设置和获取测试通过")
        
        # 测试缓存信息
        print("\n测试缓存信息...")
        cache_info = llm_cache.get_cache_info(prompt, model, 0.7)
        print(f"   缓存信息: {cache_info}")
        assert "l1_exists" in cache_info, "应该包含 L1 存在信息"
        assert "l2_exists" in cache_info, "应该包含 L2 存在信息"
        print("✅ 缓存信息测试通过")
        
        # 测试统计信息
        print("\n测试统计信息...")
        stats = llm_cache.get_stats()
        print(f"   LLM 缓存统计: {stats}")
        assert "multi_level_stats" in stats, "应该包含多级缓存统计"
        print("✅ 统计信息测试通过")
        
        print("\n✅ LLM 多级缓存测试全部通过")
        return True
        
    except Exception as e:
        print(f"\n❌ LLM 多级缓存测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_warmup():
    """测试缓存预热"""
    print("\n" + "=" * 60)
    print("测试缓存预热")
    print("=" * 60)
    
    try:
        from app.cache.cache_warmup import get_warmup_manager, DEFAULT_POI_QUERIES
        
        warmup_manager = get_warmup_manager()
        
        # 测试获取预热统计
        print("测试获取预热统计...")
        stats = warmup_manager.get_warmup_stats()
        print(f"   预热统计: {stats}")
        assert "poi_cache" in stats, "应该包含 POI 缓存统计"
        assert "weather_cache" in stats, "应该包含天气缓存统计"
        assert "llm_cache" in stats, "应该包含 LLM 缓存统计"
        print("✅ 预热统计测试通过")
        
        # 测试默认预热数据
        print("\n测试默认预热数据...")
        print(f"   默认 POI 查询数量: {len(DEFAULT_POI_QUERIES)}")
        assert len(DEFAULT_POI_QUERIES) > 0, "应该有默认的 POI 查询"
        print("✅ 默认预热数据测试通过")
        
        print("\n✅ 缓存预热测试全部通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 缓存预热测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_configuration():
    """测试缓存配置"""
    print("\n" + "=" * 60)
    print("测试缓存配置")
    print("=" * 60)
    
    try:
        from app.config import get_settings
        
        settings = get_settings()
        
        # 测试 L1 缓存配置
        print("测试 L1 缓存配置...")
        assert hasattr(settings, 'cache_poi_l1_max_size'), "应该有 POI L1 最大缓存大小配置"
        assert hasattr(settings, 'cache_poi_l1_ttl'), "应该有 POI L1 TTL 配置"
        assert hasattr(settings, 'cache_weather_l1_max_size'), "应该有天气 L1 最大缓存大小配置"
        assert hasattr(settings, 'cache_weather_l1_ttl'), "应该有天气 L1 TTL 配置"
        assert hasattr(settings, 'cache_llm_l1_max_size'), "应该有 LLM L1 最大缓存大小配置"
        assert hasattr(settings, 'cache_llm_l1_ttl'), "应该有 LLM L1 TTL 配置"
        
        print(f"   POI L1 缓存: max_size={settings.cache_poi_l1_max_size}, ttl={settings.cache_poi_l1_ttl}s")
        print(f"   天气 L1 缓存: max_size={settings.cache_weather_l1_max_size}, ttl={settings.cache_weather_l1_ttl}s")
        print(f"   LLM L1 缓存: max_size={settings.cache_llm_l1_max_size}, ttl={settings.cache_llm_l1_ttl}s")
        print("✅ L1 缓存配置测试通过")
        
        # 测试 L2 缓存配置
        print("\n测试 L2 缓存配置...")
        assert hasattr(settings, 'cache_poi_ttl'), "应该有 POI L2 TTL 配置"
        assert hasattr(settings, 'cache_weather_ttl'), "应该有天气 L2 TTL 配置"
        assert hasattr(settings, 'cache_llm_ttl'), "应该有 LLM L2 TTL 配置"
        
        print(f"   POI L2 缓存: ttl={settings.cache_poi_ttl}s")
        print(f"   天气 L2 缓存: ttl={settings.cache_weather_ttl}s")
        print(f"   LLM L2 缓存: ttl={settings.cache_llm_ttl}s")
        print("✅ L2 缓存配置测试通过")
        
        print("\n✅ 缓存配置测试全部通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 缓存配置测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("开始测试多级缓存和缓存预热功能")
    print("=" * 60)
    
    results = {}
    
    # 运行所有测试
    results["LRU 缓存"] = await test_lru_cache()
    results["多级缓存"] = await test_multi_level_cache()
    results["POI 多级缓存"] = await test_poi_cache_multi_level()
    results["天气多级缓存"] = await test_weather_cache_multi_level()
    results["LLM 多级缓存"] = await test_llm_cache_multi_level()
    results["缓存预热"] = await test_cache_warmup()
    results["缓存配置"] = await test_cache_configuration()
    
    # 打印测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} 个测试失败")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
