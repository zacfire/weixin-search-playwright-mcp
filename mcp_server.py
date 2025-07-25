#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信文章搜索 MCP 服务器
"""

import asyncio
import sys
import os
import json
from typing import Any, Dict, List

# 添加 app 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from search.playwright_search import WeChatArticleSearcher


class WeChatMCPServer:
    """微信文章搜索 MCP 服务器"""
    
    def __init__(self):
        self.searcher = None
        
    async def start(self):
        """启动服务器"""
        self.searcher = WeChatArticleSearcher()
        await self.searcher.__aenter__()
        
    async def stop(self):
        """停止服务器"""
        if self.searcher:
            await self.searcher.__aexit__(None, None, None)
            
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用"""
        if tool_name == "search_wechat_articles":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            time_filter = arguments.get("time_filter")
            
            if not query:
                return {"error": "缺少搜索关键词"}
                
            try:
                articles = await self.searcher.search_articles(
                    query=query,
                    max_results=max_results,
                    time_filter=time_filter
                )
                
                return {
                    "query": query,
                    "total_count": len(articles),
                    "articles": articles,
                    "success": True
                }
                
            except Exception as e:
                return {
                    "error": f"搜索失败: {str(e)}",
                    "success": False
                }
        else:
            return {"error": f"未知工具: {tool_name}"}


async def main():
    """MCP 服务器主函数"""
    server = WeChatMCPServer()
    
    try:
        await server.start()
        print("微信文章搜索 MCP 服务器已启动", file=sys.stderr)
        
        # 读取 stdin 的 MCP 协议消息
        while True:
            try:
                line = input()
                if not line:
                    break
                    
                message = json.loads(line)
                
                # 处理工具调用
                if message.get("method") == "tools/call":
                    params = message.get("params", {})
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    result = await server.handle_tool_call(tool_name, arguments)
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                                }
                            ]
                        }
                    }
                    
                    print(json.dumps(response, ensure_ascii=False))
                    
            except EOFError:
                break
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"处理消息错误: {e}", file=sys.stderr)
                
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()
        print("MCP 服务器已停止", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())