from os import name
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.mcp import protocol_tool
from app.mcp.protocol_tool import MCPTool
from app.models.schemas import POIInfo, WeatherInfo, Location
from app.cache import get_poi_cache, get_weather_cache

# 全局MCP工具实例
_amap_mcp_tool = None

def get_amap_mcp_tool() -> MCPTool:
    """获取高德地图工具实例"""
    global _amap_mcp_tool
    if _amap_mcp_tool is None:
        settings = get_settings()
        if not settings.amap_api_key:
            raise ValueError("请配置缺德地图密钥")

        _amap_mcp_tool = MCPTool(
            name="amap",
            description="高德地图服务,支持POI搜索、路线规划、天气查询等功能",
            server_command=["uvx", "amap-mcp-server"],
            env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
            auto_expand=True  # 自动展开为独立工具
        )
        return _amap_mcp_tool


class AmapService:
    """高德地图服务"""

    def __init__(self):
        self.mcp_tool = get_amap_mcp_tool()

    def search_poi(self, keywords: str, city: str, citylimit: bool = True)\
            -> List[POIInfo]:
        """
        搜索POI

        Args:
            keywords: 搜索关键词
            city: 城市
            citylimit: 是否限制在城市范围内

        Returns:
            POI信息列表
        """
        try:
            # 尝试从缓存获取
            poi_cache = get_poi_cache()
            cached_pois = poi_cache.get(city, keywords, citylimit)
            if cached_pois is not None:
                return cached_pois

            # 缓存未命中，调用 API
            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": "maps_text_search",
                "arguments": {
                    "keywords": keywords,
                    "city": city,
                    "citylimit": str(citylimit).lower()
                }
            })

            import json
            import re

            poi_list = []

            if isinstance(result, str):
                result = result.strip()

                if result.startswith('['):
                    data = json.loads(result)
                    if isinstance(data, list):
                        for item in data:
                            poi = POIInfo(
                                id=str(item.get('id', '')),
                                name=item.get('name', ''),
                                type=item.get('type', ''),
                                address=item.get('address', ''),
                                location=Location(
                                    longitude=float(item.get('location', {}).get('lng', 0)),
                                    latitude=float(item.get('location', {}).get('lat', 0))
                                ),
                                tel=item.get('tel')
                            )
                            poi_list.append(poi)
                elif result.startswith('{'):
                    data = json.loads(result)
                    if 'pois' in data:
                        for item in data['pois']:
                            poi = POIInfo(
                                id=str(item.get('id', '')),
                                name=item.get('name', ''),
                                type=item.get('type', ''),
                                address=item.get('address', ''),
                                location=Location(
                                    longitude=float(item.get('location', {}).get('lng', 0)),
                                    latitude=float(item.get('location', {}).get('lat', 0))
                                ),
                                tel=item.get('tel')
                            )
                            poi_list.append(poi)
                    else:
                        poi = POIInfo(
                            id=str(data.get('id', '')),
                            name=data.get('name', ''),
                            type=data.get('type', ''),
                            address=data.get('address', ''),
                            location=Location(
                                longitude=float(data.get('location', {}).get('lng', 0)),
                                latitude=float(data.get('location', {}).get('lat', 0))
                            ),
                            tel=data.get('tel')
                        )
                        poi_list.append(poi)

            # 将结果存入缓存
            if poi_list:
                poi_cache.set(city, keywords, citylimit, poi_list)

            print(f"POI搜索完成，找到 {len(poi_list)} 个结果")
            return poi_list

        except Exception as e:
            print(f"❌ POI搜索失败: {str(e)}")
            return []

    def get_weather(self, city: str) -> List[WeatherInfo]:
        """
        查询天气

        Args:
            city: 城市名称

        Returns:
            天气信息列表
        """
        try:
            # 尝试从缓存获取
            weather_cache = get_weather_cache()
            cached_weather = weather_cache.get(city, "forecast")
            if cached_weather is not None:
                # 将缓存的字典数据转换为 WeatherInfo 对象列表
                weather_list = []
                for item in cached_weather:
                    weather = WeatherInfo(
                        date=item.get('date', ''),
                        day_weather=item.get('day_weather', ''),
                        night_weather=item.get('night_weather', ''),
                        day_temp=item.get('day_temp', 0),
                        night_temp=item.get('night_temp', 0),
                        wind_direction=item.get('wind_direction', ''),
                        wind_power=item.get('wind_power', '')
                    )
                    weather_list.append(weather)
                return weather_list

            # 缓存未命中，调用 API
            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": "maps_weather",
                "arguments": {
                    "city": city
                }
            })

            import json

            weather_list = []

            if isinstance(result, str):
                result = result.strip()

                if result.startswith('['):
                    data = json.loads(result)
                    if isinstance(data, list):
                        for item in data:
                            weather = WeatherInfo(
                                date=item.get('date', ''),
                                day_weather=item.get('dayweather', ''),
                                night_weather=item.get('nightweather', ''),
                                day_temp=item.get('daytemp', 0),
                                night_temp=item.get('nighttemp', 0),
                                wind_direction=item.get('daywind', ''),
                                wind_power=item.get('daypower', '')
                            )
                            weather_list.append(weather)
                elif result.startswith('{'):
                    data = json.loads(result)
                    if 'forecasts' in data:
                        for forecast in data['forecasts']:
                            if 'casts' in forecast:
                                for item in forecast['casts']:
                                    weather = WeatherInfo(
                                        date=item.get('date', ''),
                                        day_weather=item.get('dayweather', ''),
                                        night_weather=item.get('nightweather', ''),
                                        day_temp=item.get('daytemp', 0),
                                        night_temp=item.get('nighttemp', 0),
                                        wind_direction=item.get('daywind', ''),
                                        wind_power=item.get('daypower', '')
                                    )
                                    weather_list.append(weather)
                    else:
                        weather = WeatherInfo(
                            date=data.get('date', ''),
                            day_weather=data.get('dayweather', ''),
                            night_weather=data.get('nightweather', ''),
                            day_temp=data.get('daytemp', 0),
                            night_temp=data.get('nighttemp', 0),
                            wind_direction=data.get('daywind', ''),
                            wind_power=data.get('daypower', '')
                        )
                        weather_list.append(weather)

            # 将结果存入缓存
            if weather_list:
                weather_data = [
                    {
                        'date': w.date,
                        'day_weather': w.day_weather,
                        'night_weather': w.night_weather,
                        'day_temp': w.day_temp,
                        'night_temp': w.night_temp,
                        'wind_direction': w.wind_direction,
                        'wind_power': w.wind_power
                    }
                    for w in weather_list
                ]
                weather_cache.set(city, weather_data, "forecast")

            print(f"天气查询完成，获取 {len(weather_list)} 天数据")
            return weather_list

        except Exception as e:
            print(f"❌ 天气查询失败: {str(e)}")
            return []

    def plan_route(
            self,
            origin_address: str,
            destination_address: str,
            origin_city: Optional[str] = None,
            destination_city: Optional[str] = None,
            route_type: str = "walking"
    ) -> Dict[str, Any]:
        """
        规划路线

        Args:
            origin_address: 起点地址
            destination_address: 终点地址
            origin_city: 起点城市
            destination_city: 终点城市
            route_type: 路线类型 (walking/driving/transit)

        Returns:
            路线信息
        """
        try:
            tool_map = {
                "walking": "maps_direction_walking_by_address",
                "driving": "maps_direction_driving_by_address",
                "transit": "maps_direction_transit_integrated_by_address"
            }

            tool_name = tool_map.get(route_type, "maps_direction_walking_by_address")

            arguments = {
                "origin_address": origin_address,
                "destination_address": destination_address
            }

            if route_type == "transit":
                if origin_city:
                    arguments["origin_city"] = origin_city
                if destination_city:
                    arguments["destination_city"] = destination_city
            else:
                if origin_city:
                    arguments["origin_city"] = origin_city
                if destination_city:
                    arguments["destination_city"] = destination_city

            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": tool_name,
                "arguments": arguments
            })

            import json

            route_data = {}

            if isinstance(result, str):
                result = result.strip()

                if result.startswith('{'):
                    data = json.loads(result)

                    if 'route' in data:
                        route = data['route']
                        if 'paths' in route and len(route['paths']) > 0:
                            path = route['paths'][0]
                            route_data = {
                                "distance": path.get('distance', 0),
                                "duration": path.get('duration', 0),
                                "route_type": route_type,
                                "description": path.get('instruction', ''),
                                "steps": path.get('steps', [])
                            }
                    elif 'plan' in data:
                        plan = data['plan']
                        if 'transits' in plan and len(plan['transits']) > 0:
                            transit = plan['transits'][0]
                            route_data = {
                                "distance": transit.get('distance', 0),
                                "duration": transit.get('duration', 0),
                                "route_type": route_type,
                                "description": transit.get('segments', []),
                                "segments": transit.get('segments', [])
                            }
                    else:
                        route_data = data

            print(f"路线规划完成，距离: {route_data.get('distance', 0)}米，耗时: {route_data.get('duration', 0)}秒")
            return route_data

        except Exception as e:
            print(f"❌ 路线规划失败: {str(e)}")
            return {}

    def geocode(self, address: str, city: Optional[str] = None)\
            -> Optional[Location]:
        """
        地理编码(地址转坐标)

        Args:
            address: 地址
            city: 城市

        Returns:
            经纬度坐标
        """
        try:
            arguments = {"address": address}
            if city:
                arguments["city"] = city

            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": "maps_geo",
                "arguments": arguments
            })

            import json

            if isinstance(result, str):
                result = result.strip()

                if result.startswith('['):
                    data = json.loads(result)
                    if isinstance(data, list) and len(data) > 0:
                        item = data[0]
                        return Location(
                            longitude=float(item.get('location', {}).get('lng', 0)),
                            latitude=float(item.get('location', {}).get('lat', 0))
                        )
                elif result.startswith('{'):
                    data = json.loads(result)
                    if 'geocodes' in data:
                        geocodes = data['geocodes']
                        if len(geocodes) > 0:
                            item = geocodes[0]
                            return Location(
                                longitude=float(item.get('location', {}).get('lng', 0)),
                                latitude=float(item.get('location', {}).get('lat', 0))
                            )
                    elif 'location' in data:
                        loc = data['location']
                        return Location(
                            longitude=float(loc.get('lng', 0)),
                            latitude=float(loc.get('lat', 0))
                        )

            print(f"地理编码完成")
            return None

        except Exception as e:
            print(f"❌ 地理编码失败: {str(e)}")
            return None

    def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        """
        获取POI详情

        Args:
            poi_id: POI ID

        Returns:
            POI详情信息
        """
        try:
            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": "maps_search_detail",
                "arguments": {
                    "id": poi_id
                }
            })

            print(f"POI详情结果: {result[:200]}...")

            # 解析结果并提取图片
            import json
            import re

            # 尝试从结果中提取JSON
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data

            return {"raw": result}

        except Exception as e:
            print(f"❌ 获取POI详情失败: {str(e)}")
            return {}


def get_amap_service() -> AmapService:
    """获取高德地图服务实例"""
    global _amap_service
    if _amap_service is None:
        _amap_service = AmapService()
    return _amap_service