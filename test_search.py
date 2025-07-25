#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的搜索测试脚本
用于验证搜索功能是否正常工作
"""

import asyncio
import sys
import os

# 将app目录添加到路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from search.playwright_search import WeChatArticleSearcher


async def test_basic_search():
    """测试基本搜索功能"""
    print("开始测试基本搜索功能...")
    
    async with WeChatArticleSearcher(headless=True) as searcher:
        # 测试关键词
        test_queries = ["人工智能", "机器学习", "Python编程"]
        
        for query in test_queries:
            print(f"\n正在搜索: {query}")
            try:
                results = await searcher.search_articles(query, max_results=3)
                
                if results:
                    print(f"✅ 成功找到 {len(results)} 篇文章:")
                    for i, article in enumerate(results, 1):
                        print(f"  {i}. {article['title'][:50]}...")
                        print(f"     来源: {article['source']}")
                        print(f"     时间: {article['date']}")
                        print(f"     链接: {article['url'][:60]}...")
                        print()
                else:
                    print(f"❌ 未找到相关文章")
                    
            except Exception as e:
                print(f"❌ 搜索失败: {str(e)}")
    
    print("测试完成!")


async def test_api_server():
    """测试API服务器"""
    import aiohttp
    
    print("测试API服务器...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 测试健康检查
            async with session.get('http://localhost:8000/health') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 健康检查通过: {data['status']}")
                else:
                    print(f"❌ 健康检查失败: {response.status}")
                    return
            
            # 测试搜索API
            search_data = {
                "query": "人工智能",
                "max_results": 3,
                "use_cache": False
            }
            
            async with session.post('http://localhost:8000/search_articles', 
                                  json=search_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 搜索API正常: 找到 {data['total_count']} 篇文章")
                    print(f"   搜索耗时: {data['search_time']}s")
                else:
                    print(f"❌ 搜索API失败: {response.status}")
                    error_text = await response.text()
                    print(f"   错误信息: {error_text}")
                    
    except Exception as e:
        print(f"❌ API测试失败: {str(e)}")
        print("请确保服务已启动 (python app/main.py)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="微信文章搜索测试脚本")
    parser.add_argument("--api", action="store_true", help="测试API服务器")
    parser.add_argument("--search", action="store_true", help="测试搜索功能")
    
    args = parser.parse_args()
    
    if not args.api and not args.search:
        # 默认运行搜索测试
        args.search = True
    
    if args.search:
        asyncio.run(test_basic_search())
    
    if args.api:
        asyncio.run(test_api_server())