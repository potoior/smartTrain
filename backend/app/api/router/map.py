

from fastapi import APIRouter,Query,HTTPException

from backend.app.models.schemas import POISearchResponse
from backend.app.services.amap_service import get_amap_service

router = APIRouter(prefix="/map", tags=["地图服务"])

@router.get(
    path="/poi",
    summary="POI搜索",
    description="搜索指定城市的POI信息",
    response_model=POISearchResponse
)
async def search_poi(
        keywords: str = Query(..., description="搜索关键词", examples=["故宫"]),
        city: str = Query(..., description="城市", examples=["北京"]),
        cityLimit: bool = Query(True, description="是否限制在城市范围内")
)->POISearchResponse:
    """

    :param keywords: 搜索关键词
    :param city: 搜索城市
    :param cityLimit: 所限制的城市范围
    :return: 返回搜索结果
    """
    try:
        # 获取服务实例
        service = get_amap_service()
        # 开始搜索poi
        pois = service.search_poi(keywords, city, cityLimit)

        return POISearchResponse(
            success=True,
            data = pois,
            message="POI搜索成功"
        )

    except Exception as e:
        print("搜索出了问题,问题是:")
        print(e)
        raise HTTPException(
            status_code=500,
            detail=f"POI搜索失败了{str(e)}"
        )

