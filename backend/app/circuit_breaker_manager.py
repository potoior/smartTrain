import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from pybreaker import CircuitBreaker, CircuitBreakerError

from app.config import get_settings


class CircuitBreakerManager:
    """熔断器管理器"""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self.settings = get_settings()

    def get_breaker(self, name: str) -> CircuitBreaker:
        """
        获取或创建熔断器

        Args:
            name: 熔断器名称

        Returns:
            CircuitBreaker 实例
        """
        if name not in self._breakers:
            self._breakers[name] = self._create_breaker(name)
        return self._breakers[name]

    def _create_breaker(self, name: str) -> CircuitBreaker:
        """
        创建熔断器

        Args:
            name: 熔断器名称

        Returns:
            CircuitBreaker 实例
        """
        if name == "amap_poi":
            return CircuitBreaker(
                fail_max=self.settings.amap_circuit_failure_threshold,
                reset_timeout=self.settings.amap_circuit_recovery_timeout,
                name=name
            )
        elif name == "amap_weather":
            return CircuitBreaker(
                fail_max=self.settings.amap_circuit_failure_threshold,
                reset_timeout=self.settings.amap_circuit_recovery_timeout,
                name=name
            )
        elif name == "amap_route":
            return CircuitBreaker(
                fail_max=self.settings.amap_circuit_failure_threshold,
                reset_timeout=self.settings.amap_circuit_recovery_timeout,
                name=name
            )
        else:
            return CircuitBreaker(
                fail_max=5,
                reset_timeout=60,
                name=name
            )

    def get_breaker_state(self, name: str) -> Dict[str, Any]:
        """
        获取熔断器状态

        Args:
            name: 熔断器名称

        Returns:
            熔断器状态信息
        """
        breaker = self.get_breaker(name)
        return {
            "name": name,
            "state": self._get_state_name(breaker),
            "failure_count": breaker.fail_counter,
            "success_count": breaker.success_counter,
        }

    def _get_state_name(self, breaker: CircuitBreaker) -> str:
        """
        获取熔断器状态名称

        Args:
            breaker: CircuitBreaker 实例

        Returns:
            状态名称: closed, open, half_open
        """
        if breaker.open:
            return "open"
        elif breaker.half_open:
            return "half_open"
        else:
            return "closed"

    def get_all_breakers_state(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有熔断器状态

        Returns:
            所有熔断器状态信息
        """
        return {
            name: self.get_breaker_state(name)
            for name in self._breakers.keys()
        }

    def reset_breaker(self, name: str):
        """
        重置熔断器

        Args:
            name: 熔断器名称
        """
        if name in self._breakers:
            self._breakers[name].close()
            self._breakers[name].reset()


# 全局熔断器管理器实例
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """
    获取熔断器管理器实例

    Returns:
        CircuitBreakerManager 实例
    """
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager


def circuit_breaker(breaker_name: str):
    """
    熔断器装饰器

    Args:
        breaker_name: 熔断器名称

    Returns:
        装饰器函数
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            breaker = manager.get_breaker(breaker_name)

            try:
                result = breaker.call(func, *args, **kwargs)
                return result
            except CircuitBreakerError as e:
                print(f"🔴 熔断器 '{breaker_name}' 已打开，请求被拒绝: {str(e)}")
                raise CircuitBreakerError(f"服务 '{breaker_name}' 熔断中，请稍后重试")
            except Exception as e:
                print(f"❌ 函数 '{func.__name__}' 执行失败: {str(e)}")
                raise

        return wrapper
    return decorator
