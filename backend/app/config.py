import os
from typing import List, Optional

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
# 加载当前的env变量
load_dotenv()
class Settings(BaseSettings):
    """配置类"""
    # 配置项
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    app_name : str = "智能旅行助手"
    debug : bool = True
    app_version :str  = "0.1.0"
    # CORS配置 - 使用字符串,在代码中分割
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # 高德地图API配置
    amap_api_key: str = os.getenv("AMAP_API_KEY") or "b8xxx"

    # Unsplash API配置
    unsplash_access_key: str = os.getenv("UNSPLASH_ACCESS_KEY") or "wmLuHxxx"
    unsplash_secret_key: str = os.getenv("UNSPLASH_SECRET_KEY") or "kMFi_eiAxxx"

    # LLM配置 (从环境变量读取)
    openai_api_key: str = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "sk-7fbde6579xxxxx"
    openai_base_url: str = os.getenv("LLM_BASE_URL") or "https://api.deepseek.com/v1"
    openai_model: str = os.getenv("LLM_MODEL") or "deepseek-chat"

    # Redis配置
    redis_host: str = os.getenv("REDIS_HOST") or "localhost"
    redis_port: int = int(os.getenv("REDIS_PORT") or "6379")
    redis_db: int = int(os.getenv("REDIS_DB") or "0")
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
    redis_max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS") or "10")
    redis_enabled: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"

    # 缓存配置
    cache_poi_ttl: int = int(os.getenv("CACHE_POI_TTL") or "3600000")
    cache_weather_ttl: int = int(os.getenv("CACHE_WEATHER_TTL") or "1800000")
    cache_llm_ttl: int = int(os.getenv("CACHE_LLM_TTL") or "7200000")

    # 日志配置
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量

    def get_cors_origins_list(self) -> List[str]:
        """获取CORS origins列表"""
        return [origin.strip() for origin in self.cors_origins.split(',')]


# 创建全局配置实例
settings = Settings()



def get_settings() -> Settings:
    """获取配置实例"""
    return settings

# 验证必要的配置
def validate_config():
    """验证配置是否完整"""
    errors = []
    warnings = []

    if not settings.amap_api_key:
        errors.append("AMAP_API_KEY未配置")

    # 会自动从LLM_API_KEY读取,不强制要求OPENAI_API_KEY
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not llm_api_key:
        warnings.append("LLM_API_KEY或OPENAI_API_KEY未配置,LLM功能可能无法使用")

    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    if warnings:
        print("\n⚠️  配置警告:")
        for w in warnings:
            print(f"  - {w}")

    return True


# 打印配置信息(用于调试)
def print_config():
    """打印当前配置(隐藏敏感信息)"""
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.app_version}")
    print(f"服务器: {settings.host}:{settings.port}")
    print(f"高德地图API Key: {'已配置' if settings.amap_api_key else '未配置'}")

    # 检查LLM配置
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL") or settings.openai_base_url
    llm_model = os.getenv("LLM_MODEL_ID") or settings.openai_model

    print(f"LLM API Key: {'已配置' if llm_api_key else '未配置'}")
    print(f"LLM Base URL: {llm_base_url}")
    print(f"LLM Model: {llm_model}")
    print(f"日志级别: {settings.log_level}")

    # Redis配置
    print(f"Redis: {'已启用' if settings.redis_enabled else '未启用'}")
    if settings.redis_enabled:
        print(f"  - 主机: {settings.redis_host}:{settings.redis_port}")
        print(f"  - 数据库: {settings.redis_db}")
        print(f"  - 密码: {'已设置' if settings.redis_password else '未设置'}")
        print(f"  - 最大连接数: {settings.redis_max_connections}")

    # 缓存配置
    print(f"缓存 TTL: POI={settings.cache_poi_ttl}s, 天气={settings.cache_weather_ttl}s, LLM={settings.cache_llm_ttl}s")



"""配置管理"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel


class Config(BaseModel):
    """LpyAgents配置类"""

    # LLM配置
    default_model: str = "Qwen/Qwen2.5-72B-Instruct"
    default_provider: str = "siliconflow"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # 系统配置
    debug: bool = False
    log_level: str = "INFO"

    # 其他配置
    max_history_length: int = 100

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()
