#!/usr/bin/env python3
"""
测试网络访问API的脚本
"""
import requests
import json
import sys
import time
from urllib.parse import urlparse

def test_api_endpoint(base_url, endpoint="/health"):
    """测试API端点"""
    url = f"{base_url}{endpoint}"
    
    print(f"\n{'='*50}")
    print(f"测试URL: {url}")
    print(f"{'='*50}")
    
    try:
        # 添加跨域头，模拟浏览器请求
        headers = {
            'Origin': 'http://10.113.82.229:9173',  # 模拟React应用的Origin
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print("发送请求...")
        start_time = time.time()
        
        response = requests.get(url, headers=headers, timeout=10)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"⏱️  响应时间: {response_time:.2f}ms")
        print(f"📝 响应头:")
        
        for header, value in response.headers.items():
            if header.lower().startswith('access-control') or header.lower() in ['server', 'content-type']:
                print(f"   {header}: {value}")
        
        print(f"📦 响应内容:")
        try:
            json_data = response.json()
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
        except:
            print(response.text[:200] + ("..." if len(response.text) > 200 else ""))
            
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"⏰ 超时错误: {e}")
        return False
    except Exception as e:
        print(f"🚫 其他错误: {e}")
        return False

def main():
    """主函数"""
    print("🔍 API网络访问测试")
    print(f"⏰ 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试不同的API基础URL
    test_urls = [
        "http://localhost:9000",
        "http://127.0.0.1:9000", 
        "http://10.113.82.229:9000"
    ]
    
    results = {}
    
    for base_url in test_urls:
        print(f"\n🎯 测试基础URL: {base_url}")
        
        # 测试健康检查端点
        success = test_api_endpoint(base_url, "/health")
        results[base_url] = success
        
        if success:
            print("✅ 基础连接正常，测试API端点...")
            # 测试pieces端点
            test_api_endpoint(base_url, "/api/pieces")
    
    # 总结
    print(f"\n{'='*60}")
    print("📊 测试总结:")
    print(f"{'='*60}")
    
    for url, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{url:<30} {status}")
    
    # 网络诊断建议
    print(f"\n💡 故障排除建议:")
    print("1. 确保API服务器正在运行: ps aux | grep fastapi")
    print("2. 检查端口监听: netstat -tlnp | grep :9000")
    print("3. 检查防火墙: sudo ufw status")
    print("4. 从其他设备测试: curl http://10.113.82.229:9000/health")
    print("5. 检查路由器端口转发和DMZ设置")

if __name__ == "__main__":
    main()
