"""
测试重试机制的脚本
验证 LLM 和 Amap API 调用中的重试功能是否正常工作
"""

import asyncio
from unittest.mock import Mock, patch
from tenacity import RetryError

async def test_llm_retry():
    """测试 LLM 重试机制"""
    print("=" * 60)
    print("测试 LLM 重试机制")
    print("=" * 60)
    
    try:
        from app.LLM.llm import LpyAgentsLLM
        
        # 创建 LLM 实例
        llm = LpyAgentsLLM()
        
        print(f"✅ LLM 实例创建成功")
        print(f"   重试配置: max_attempts={llm._retry_max_attempts}, wait_min={llm._retry_wait_min}, wait_max={llm._retry_wait_max}")
        
        # 测试重试装饰器是否正确应用
        if hasattr(llm, '_invoke_with_retry'):
            print(f"✅ _invoke_with_retry 方法存在")
            
            # 检查装饰器是否正确应用
            retry_decorator = getattr(llm._invoke_with_retry, '__wrapped__', None)
            if retry_decorator:
                print(f"✅ 重试装饰器已应用")
            else:
                print(f"⚠️  重试装饰器可能未正确应用")
        else:
            print(f"❌ _invoke_with_retry 方法不存在")
        
        if hasattr(llm, '_think_with_retry'):
            print(f"✅ _think_with_retry 方法存在")
        else:
            print(f"❌ _think_with_retry 方法不存在")
            
    except Exception as e:
        print(f"❌ LLM 重试机制测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_amap_retry():
    """测试 Amap API 重试机制"""
    print("\n" + "=" * 60)
    print("测试 Amap API 重试机制")
    print("=" * 60)
    
    try:
        from app.services.amap_service import AmapService
        
        # 创建 AmapService 实例
        amap_service = AmapService()
        
        print(f"✅ AmapService 实例创建成功")
        print(f"   重试配置: max_attempts={amap_service._retry_max_attempts}, wait_min={amap_service._retry_wait_min}, wait_max={amap_service._retry_wait_max}")
        
        # 测试重试方法是否正确应用
        retry_methods = [
            '_search_poi_with_retry',
            '_get_weather_with_retry',
            '_plan_route_with_retry'
        ]
        
        for method_name in retry_methods:
            if hasattr(amap_service, method_name):
                print(f"✅ {method_name} 方法存在")
                
                # 检查装饰器是否正确应用
                method = getattr(amap_service, method_name)
                retry_decorator = getattr(method, '__wrapped__', None)
                if retry_decorator:
                    print(f"   ✅ 重试装饰器已应用")
                else:
                    print(f"   ⚠️  重试装饰器可能未正确应用")
            else:
                print(f"❌ {method_name} 方法不存在")
                
    except Exception as e:
        print(f"❌ Amap API 重试机制测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_retry_config():
    """测试重试配置"""
    print("\n" + "=" * 60)
    print("测试重试配置")
    print("=" * 60)
    
    try:
        from app.config import get_settings
        
        settings = get_settings()
        
        # 检查 LLM 重试配置
        if hasattr(settings, 'llm_retry_max_attempts'):
            print(f"✅ LLM 重试配置存在")
            print(f"   max_attempts: {settings.llm_retry_max_attempts}")
            print(f"   wait_min: {settings.llm_retry_wait_min}")
            print(f"   wait_max: {settings.llm_retry_wait_max}")
            print(f"   multiplier: {settings.llm_retry_multiplier}")
        else:
            print(f"❌ LLM 重试配置不存在")
        
        # 检查 Amap 重试配置
        if hasattr(settings, 'amap_retry_max_attempts'):
            print(f"✅ Amap 重试配置存在")
            print(f"   max_attempts: {settings.amap_retry_max_attempts}")
            print(f"   wait_min: {settings.amap_retry_wait_min}")
            print(f"   wait_max: {settings.amap_retry_wait_max}")
            print(f"   multiplier: {settings.amap_retry_multiplier}")
        else:
            print(f"❌ Amap 重试配置不存在")
            
    except Exception as e:
        print(f"❌ 重试配置测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_retry_behavior():
    """测试重试行为"""
    print("\n" + "=" * 60)
    print("测试重试行为（模拟失败场景）")
    print("=" * 60)
    
    try:
        from app.services.amap_service import AmapService
        from unittest.mock import Mock, patch
        
        # 创建 AmapService 实例
        amap_service = AmapService()
        
        # 检查 mcp_tool 是否存在
        if not hasattr(amap_service, 'mcp_tool') or amap_service.mcp_tool is None:
            print("⚠️  mcp_tool 不存在或为 None，跳过重试行为测试")
            return
        
        # Mock mcp_tool.run 方法，使其前两次失败，第三次成功
        call_count = [0]
        
        def mock_run(*args, **kwargs):
            call_count[0] += 1
            print(f"   模拟 API 调用（第 {call_count[0]} 次）")
            if call_count[0] < 3:
                raise Exception("模拟 API 失败")
            return '{"pois": []}'
        
        with patch.object(amap_service.mcp_tool, 'run', side_effect=mock_run):
            print("测试 POI 搜索重试...")
            try:
                result = amap_service.search_poi("test", "北京")
                print(f"✅ 重试成功，共调用 {call_count[0]} 次")
                print(f"   结果: {result}")
            except Exception as e:
                print(f"❌ 重试失败: {str(e)}")
                print(f"   共调用 {call_count[0]} 次")
                
    except Exception as e:
        print(f"❌ 重试行为测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("开始测试重试机制")
    print("=" * 60 + "\n")
    
    # 测试配置
    test_retry_config()
    
    # 测试 LLM 重试机制
    await test_llm_retry()
    
    # 测试 Amap API 重试机制
    test_amap_retry()
    
    # 测试重试行为
    await test_retry_behavior()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
