from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.circuit_breaker_manager import get_circuit_breaker_manager

router = APIRouter(prefix="/circuit-breaker", tags=["熔断器监控"])


@router.get(
    "/status",
    summary="获取所有熔断器状态",
    description="获取所有熔断器的当前状态信息"
)
async def get_all_breakers_status() -> Dict[str, Dict[str, Any]]:
    """
    获取所有熔断器状态

    Returns:
        所有熔断器的状态信息
    """
    try:
        manager = get_circuit_breaker_manager()
        return manager.get_all_breakers_state()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取熔断器状态失败: {str(e)}"
        )


@router.get(
    "/status/{breaker_name}",
    summary="获取指定熔断器状态",
    description="获取指定熔断器的当前状态信息"
)
async def get_breaker_status(breaker_name: str) -> Dict[str, Any]:
    """
    获取指定熔断器状态

    Args:
        breaker_name: 熔断器名称

    Returns:
        熔断器状态信息
    """
    try:
        manager = get_circuit_breaker_manager()
        return manager.get_breaker_state(breaker_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取熔断器状态失败: {str(e)}"
        )


@router.post(
    "/reset/{breaker_name}",
    summary="重置熔断器",
    description="手动重置指定熔断器，将其状态设置为关闭"
)
async def reset_breaker(breaker_name: str) -> Dict[str, str]:
    """
    重置熔断器

    Args:
        breaker_name: 熔断器名称

    Returns:
        操作结果
    """
    try:
        manager = get_circuit_breaker_manager()
        manager.reset_breaker(breaker_name)
        return {
            "message": f"熔断器 '{breaker_name}' 已重置",
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"重置熔断器失败: {str(e)}"
        )
