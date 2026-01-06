"""缓存预热管理"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from app.cache import get_poi_cache, get_weather_cache, get_llm_cache
from app.services.amap_service import AmapService

logger = logging.getLogger(__name__)


class CacheWarmupManager:
    """缓存预热管理器"""

    def __init__(self):
        self.poi_cache = get_poi_cache()
        self.weather_cache = get_weather_cache()
        self.llm_cache = get_llm_cache()
        self.amap_service = None

    async def initialize_amap_service(self):
        """初始化高德地图服务"""
        if self.amap_service is None:
            self.amap_service = AmapService()
            logger.info("高德地图服务初始化完成")

    async def warm_up_poi_cache(self, queries: List[Dict[str, Any]]) -> int:
        """预热 POI 缓存
        
        Args:
            queries: 查询列表，每个元素包含 city, keywords, citylimit
        
        Returns:
            成功预热的查询数量
        """
        await self.initialize_amap_service()
        
        success_count = 0
        for query in queries:
            city = query.get('city')
            keywords = query.get('keywords')
            citylimit = query.get('citylimit', True)
            
            try:
                pois = await self.amap_service.search_poi(keywords, city, citylimit)
                if pois:
                    self.poi_cache.set(city, keywords, citylimit, pois)
                    success_count += 1
                    logger.info(f"预热 POI 缓存: {city} - {keywords}")
            except Exception as e:
                logger.error(f"预热 POI 缓存失败: {city} - {keywords}, 错误: {str(e)}")
        
        logger.info(f"POI 缓存预热完成: {success_count}/{len(queries)} 条")
        return success_count

    async def warm_up_weather_cache(self, cities: List[str], weather_type: str = "current") -> int:
        """预热天气缓存
        
        Args:
            cities: 城市列表
            weather_type: 天气类型
        
        Returns:
            成功预热的城市数量
        """
        await self.initialize_amap_service()
        
        success_count = 0
        for city in cities:
            try:
                weather_data = await self.amap_service.get_weather(city)
                if weather_data:
                    self.weather_cache.set(city, weather_data, weather_type)
                    success_count += 1
                    logger.info(f"预热天气缓存: {city} ({weather_type})")
            except Exception as e:
                logger.error(f"预热天气缓存失败: {city}, 错误: {str(e)}")
        
        logger.info(f"天气缓存预热完成: {success_count}/{len(cities)} 条")
        return success_count

    async def warm_up_llm_cache(self, prompts_responses: List[tuple], model: str, 
                                temperature: float = 0.7, max_tokens: Optional[int] = None) -> int:
        """预热 LLM 缓存
        
        Args:
            prompts_responses: 提示词和响应的元组列表 [(prompt, response), ...]
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
        
        Returns:
            成功预热的数量
        """
        success_count = 0
        for prompt, response in prompts_responses:
            try:
                self.llm_cache.set(prompt, response, model, temperature, max_tokens)
                success_count += 1
                logger.info(f"预热 LLM 缓存: {prompt[:50]}...")
            except Exception as e:
                logger.error(f"预热 LLM 缓存失败: {prompt[:50]}..., 错误: {str(e)}")
        
        logger.info(f"LLM 缓存预热完成: {success_count}/{len(prompts_responses)} 条")
        return success_count

    async def warm_up_all(self, 
                         poi_queries: Optional[List[Dict[str, Any]]] = None,
                         weather_cities: Optional[List[str]] = None,
                         llm_prompts: Optional[List[tuple]] = None,
                         llm_model: str = "deepseek-chat",
                         llm_temperature: float = 0.7) -> Dict[str, int]:
        """预热所有缓存
        
        Args:
            poi_queries: POI 查询列表
            weather_cities: 天气城市列表
            llm_prompts: LLM 提示词列表
            llm_model: LLM 模型名称
            llm_temperature: LLM 温度参数
        
        Returns:
            预热结果统计
        """
        results = {
            "poi": 0,
            "weather": 0,
            "llm": 0,
            "total": 0
        }

        tasks = []

        if poi_queries:
            tasks.append(self.warm_up_poi_cache(poi_queries))

        if weather_cities:
            tasks.append(self.warm_up_weather_cache(weather_cities))

        if llm_prompts:
            tasks.append(self.warm_up_llm_cache(llm_prompts, llm_model, llm_temperature))

        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            if poi_queries:
                results["poi"] = task_results[0] if not isinstance(task_results[0], Exception) else 0
            
            if weather_cities:
                idx = 1 if poi_queries else 0
                results["weather"] = task_results[idx] if not isinstance(task_results[idx], Exception) else 0
            
            if llm_prompts:
                idx = 2 if poi_queries and weather_cities else (1 if poi_queries or weather_cities else 0)
                results["llm"] = task_results[idx] if not isinstance(task_results[idx], Exception) else 0

            results["total"] = results["poi"] + results["weather"] + results["llm"]

        logger.info(f"所有缓存预热完成: {results}")
        return results

    def get_warmup_stats(self) -> Dict[str, Any]:
        """获取缓存预热统计信息"""
        return {
            "poi_cache": self.poi_cache.get_stats(),
            "weather_cache": self.weather_cache.get_stats(),
            "llm_cache": self.llm_cache.get_stats()
        }


# 全局缓存预热管理器实例
_warmup_manager: Optional[CacheWarmupManager] = None


def get_warmup_manager() -> CacheWarmupManager:
    """获取缓存预热管理器实例"""
    global _warmup_manager
    if _warmup_manager is None:
        _warmup_manager = CacheWarmupManager()
    return _warmup_manager


# 预定义的预热数据
DEFAULT_POI_QUERIES = [
    {"city": "北京", "keywords": "故宫", "citylimit": True},
    {"city": "北京", "keywords": "天安门", "citylimit": True},
    {"city": "北京", "keywords": "长城", "citylimit": True},
    {"city": "上海", "keywords": "外滩", "citylimit": True},
    {"city": "上海", "keywords": "东方明珠", "citylimit": True},
    {"city": "广州", "keywords": "广州塔", "citylimit": True},
    {"city": "深圳", "keywords": "世界之窗", "citylimit": True},
    {"city": "杭州", "keywords": "西湖", "citylimit": True},
    {"city": "成都", "keywords": "宽窄巷子", "citylimit": True},
    {"city": "西安", "keywords": "兵马俑", "citylimit": True},
]

DEFAULT_WEATHER_CITIES = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "成都",
    "西安",
    "南京",
    "武汉",
    "重庆",
]

DEFAULT_LLM_PROMPTS = [
    ("北京有哪些著名的旅游景点？", "北京有许多著名的旅游景点，包括故宫、天安门广场、长城（八达岭、慕田峪等）、颐和园、天坛、北海公园、雍和宫、南锣鼓巷、798艺术区等。每个景点都有其独特的历史文化价值和景观特色。"),
    ("上海有什么好玩的地方？", "上海有许多值得一游的地方，包括外滩、东方明珠塔、上海中心大厦、豫园、南京路步行街、田子坊、新天地、迪士尼乐园等。这些地方既有现代化的都市景观，也有传统文化街区。"),
    ("推荐一些广州的美食", "广州的美食非常丰富，推荐尝试：早茶点心（虾饺、烧卖、肠粉）、煲仔饭、云吞面、白切鸡、烧鹅、艇仔粥、双皮奶、姜撞奶等。广州被誉为'食在广州'，美食文化源远流长。"),
]


async def warm_up_default_caches() -> Dict[str, int]:
    """使用默认数据预热所有缓存"""
    manager = get_warmup_manager()
    return await manager.warm_up_all(
        poi_queries=DEFAULT_POI_QUERIES,
        weather_cities=DEFAULT_WEATHER_CITIES,
        llm_prompts=DEFAULT_LLM_PROMPTS,
        llm_model="deepseek-chat",
        llm_temperature=0.7
    )
