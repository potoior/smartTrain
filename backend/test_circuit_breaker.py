from pybreaker import CircuitBreaker, CircuitBreakerError

def test_function():
    print("执行测试函数")
    return "成功"

def failing_function():
    print("执行失败函数")
    raise Exception("测试失败")

breaker = CircuitBreaker(fail_max=3, reset_timeout=5, name="test_breaker")

print("初始状态:")
print(f"open: {breaker.open}")
print(f"half_open: {breaker.half_open}")
print(f"fail_counter: {breaker.fail_counter}")
print(f"success_counter: {breaker.success_counter}")

print("\n测试成功调用:")
for i in range(5):
    try:
        result = breaker.call(test_function)
        print(f"调用 {i+1}: {result}")
    except CircuitBreakerError as e:
        print(f"调用 {i+1}: 熔断器已打开 - {e}")
    print(f"  状态 - open: {breaker.open}, half_open: {breaker.half_open}, fail_counter: {breaker.fail_counter}, success_counter: {breaker.success_counter}")

print("\n测试失败调用:")
for i in range(5):
    try:
        result = breaker.call(failing_function)
        print(f"调用 {i+1}: {result}")
    except CircuitBreakerError as e:
        print(f"调用 {i+1}: 熔断器已打开 - {e}")
    except Exception as e:
        print(f"调用 {i+1}: 函数执行失败 - {e}")
    print(f"  状态 - open: {breaker.open}, half_open: {breaker.half_open}, fail_counter: {breaker.fail_counter}, success_counter: {breaker.success_counter}")

print("\n等待5秒后重试:")
import time
time.sleep(5)

for i in range(3):
    try:
        result = breaker.call(test_function)
        print(f"调用 {i+1}: {result}")
    except CircuitBreakerError as e:
        print(f"调用 {i+1}: 熔断器已打开 - {e}")
    print(f"  状态 - open: {breaker.open}, half_open: {breaker.half_open}, fail_counter: {breaker.fail_counter}, success_counter: {breaker.success_counter}")
