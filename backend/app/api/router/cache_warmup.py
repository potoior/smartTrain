"""缓存预热管理 API 路由"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from app.cache.cache_warmup import get_warmup_manager, warm_up_default_caches

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache/warmup", tags=["缓存预热"])


class WarmupRequest(BaseModel):
    """缓存预热请求"""
    poi_queries: Optional[List[Dict[str, Any]]] = None
    weather_cities: Optional[List[str]] = None
    llm_prompts: Optional[List[tuple]] = None
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7


class WarmupResponse(BaseModel):
    """缓存预热响应"""
    poi: int
    weather: int
    llm: int
    total: int
    message: str


@router.post("/start", response_model=WarmupResponse)
async def start_warmup(request: WarmupRequest, background_tasks: BackgroundTasks):
    """启动缓存预热
    
    - **poi_queries**: POI 查询列表，每个元素包含 city, keywords, citylimit
    - **weather_cities**: 天气城市列表
    - **llm_prompts**: LLM 提示词列表，每个元素是 (prompt, response) 元组
    - **llm_model**: LLM 模型名称
    - **llm_temperature**: LLM 温度参数
    """
    try:
        manager = get_warmup_manager()
        
        # 在后台任务中执行预热
        async def warmup_task():
            results = await manager.warm_up_all(
                poi_queries=request.poi_queries,
                weather_cities=request.weather_cities,
                llm_prompts=request.llm_prompts,
                llm_model=request.llm_model,
                llm_temperature=request.llm_temperature
            )
            logger.info(f"缓存预热任务完成: {results}")
        
        background_tasks.add_task(warmup_task)
        
        return WarmupResponse(
            poi=0,
            weather=0,
            llm=0,
            total=0,
            message="缓存预热任务已启动，正在后台执行"
        )
    except Exception as e:
        logger.error(f"启动缓存预热失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动缓存预热失败: {str(e)}")


@router.post("/default", response_model=WarmupResponse)
async def warmup_default(background_tasks: BackgroundTasks):
    """使用默认数据预热所有缓存"""
    try:
        # 在后台任务中执行预热
        async def warmup_task():
            results = await warm_up_default_caches()
            logger.info(f"默认缓存预热任务完成: {results}")
        
        background_tasks.add_task(warmup_task)
        
        return WarmupResponse(
            poi=0,
            weather=0,
            llm=0,
            total=0,
            message="默认缓存预热任务已启动，正在后台执行"
        )
    except Exception as e:
        logger.error(f"启动默认缓存预热失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动默认缓存预热失败: {str(e)}")


@router.get("/stats")
async def get_warmup_stats():
    """获取缓存预热统计信息"""
    try:
        manager = get_warmup_manager()
        stats = manager.get_warmup_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取缓存预热统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取缓存预热统计失败: {str(e)}")


@router.post("/poi")
async def warmup_poi(queries: List[Dict[str, Any]], background_tasks: BackgroundTasks):
    """预热 POI 缓存
    
    - **queries**: POI 查询列表，每个元素包含 city, keywords, citylimit
    """
    try:
        manager = get_warmup_manager()
        
        async def warmup_task():
            count = await manager.warm_up_poi_cache(queries)
            logger.info(f"POI 缓存预热完成: {count}/{len(queries)} 条")
        
        background_tasks.add_task(warmup_task)
        
        return {
            "success": True,
            "message": f"POI 缓存预热任务已启动，共 {len(queries)} 条查询"
        }
    except Exception as e:
        logger.error(f"启动 POI 缓存预热失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动 POI 缓存预热失败: {str(e)}")


@router.post("/weather")
async def warmup_weather(cities: List[str], background_tasks: BackgroundTasks,
                         weather_type: str = "current"):
    """预热天气缓存
    
    - **cities**: 城市列表
    - **weather_type**: 天气类型，默认为 current
    """
    try:
        manager = get_warmup_manager()
        
        async def warmup_task():
            count = await manager.warm_up_weather_cache(cities, weather_type)
            logger.info(f"天气缓存预热完成: {count}/{len(cities)} 条")
        
        background_tasks.add_task(warmup_task)
        
        return {
            "success": True,
            "message": f"天气缓存预热任务已启动，共 {len(cities)} 个城市"
        }
    except Exception as e:
        logger.error(f"启动天气缓存预热失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动天气缓存预热失败: {str(e)}")


@router.post("/llm")
async def warmup_llm(prompts_responses: List[tuple], background_tasks: BackgroundTasks,
                     model: str = "deepseek-chat", temperature: float = 0.7, 
                     max_tokens: Optional[int] = None):
    """预热 LLM 缓存
    
    - **prompts_responses**: 提示词和响应的元组列表 [(prompt, response), ...]
    - **model**: 模型名称
    - **temperature**: 温度参数
    - **max_tokens**: 最大 token 数
    """
    try:
        manager = get_warmup_manager()
        
        async def warmup_task():
            count = await manager.warm_up_llm_cache(prompts_responses, model, temperature, max_tokens)
            logger.info(f"LLM 缓存预热完成: {count}/{len(prompts_responses)} 条")
        
        background_tasks.add_task(warmup_task)
        
        return {
            "success": True,
            "message": f"LLM 缓存预热任务已启动，共 {len(prompts_responses)} 条提示词"
        }
    except Exception as e:
        logger.error(f"启动 LLM 缓存预热失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动 LLM 缓存预热失败: {str(e)}")
