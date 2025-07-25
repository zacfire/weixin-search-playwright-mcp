#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信文章搜索 MCP 服务器
符合标准 MCP 协议
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List

# 添加 app 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from search.playwright_search import WeChatArticleSearcher


class MCPServer:
    """标准 MCP 服务器实现"""
    
    def __init__(self):
        self.searcher = None
        self.request_id = 0
        
    async def start(self):
        """启动服务器"""
        self.searcher = WeChatArticleSearcher()
        await self.searcher.__aenter__()
        print("微信文章搜索 MCP 服务器已启动", file=sys.stderr)
        
    async def stop(self):
        """停止服务器"""
        if self.searcher:
            await self.searcher.__aexit__(None, None, None)
            
    def send_response(self, request_id: int, result: Any = None, error: Any = None):
        """发送响应"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        
        if error:
            response["error"] = error
        else:
            response["result"] = result
            
        print(json.dumps(response, ensure_ascii=False))
        sys.stdout.flush()
        
    async def handle_initialize(self, request_id: int, params: Dict[str, Any]):
        """处理初始化请求"""
        result = {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {
                    "listChanged": False
                },
                "resources": {
                    "subscribe": False,
                    "listChanged": False
                },
                "prompts": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "wechat-article-search",
                "version": "1.0.0"
            }
        }
        self.send_response(request_id, result)
        
    async def handle_list_tools(self, request_id: int, params: Dict[str, Any]):
        """处理工具列表请求"""
        tools = [{
            "name": "search_wechat_articles",
            "description": "搜索微信公众号文章",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "max_results": {
                        "type": "integer", 
                        "description": "最大结果数量",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    },
                    "time_filter": {
                        "type": "string",
                        "description": "时间筛选",
                        "enum": ["day", "week", "month", "year"]
                    }
                },
                "required": ["query"]
            }
        }]
        
        self.send_response(request_id, {"tools": tools})
        
    async def handle_call_tool(self, request_id: int, params: Dict[str, Any]):
        """处理工具调用"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "search_wechat_articles":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            time_filter = arguments.get("time_filter")
            
            if not query:
                self.send_response(request_id, None, {
                    "code": -32602,
                    "message": "缺少搜索关键词"
                })
                return
                
            try:
                articles = await self.searcher.search_articles(
                    query=query,
                    max_results=max_results,
                    time_filter=time_filter
                )
                
                # 格式化结果
                result_text = f"找到 {len(articles)} 篇关于「{query}」的微信文章：\n\n"
                
                for i, article in enumerate(articles, 1):
                    result_text += f"{i}. **{article['title']}**\n"
                    result_text += f"   来源：{article['source']}\n"
                    result_text += f"   时间：{article['date']}\n"
                    result_text += f"   摘要：{article['snippet'][:100]}...\n"
                    result_text += f"   链接：{article['url']}\n\n"
                
                self.send_response(request_id, {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                })
                
            except Exception as e:
                print(f"搜索错误: {str(e)}", file=sys.stderr)
                self.send_response(request_id, None, {
                    "code": -32603,
                    "message": f"搜索失败: {str(e)}"
                })
        else:
            self.send_response(request_id, None, {
                "code": -32601,
                "message": f"未知工具: {tool_name}"
            })
            
    async def handle_list_resources(self, request_id: int, params: Dict[str, Any]):
        """处理资源列表请求"""
        self.send_response(request_id, {"resources": []})
        
    async def handle_list_prompts(self, request_id: int, params: Dict[str, Any]):
        """处理提示词列表请求"""
        self.send_response(request_id, {"prompts": []})
        
    async def handle_notifications_initialized(self):
        """处理初始化完成通知"""
        # 不需要响应，这是通知消息
        pass
            
    async def handle_request(self, message: Dict[str, Any]):
        """处理请求"""
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params", {})
        
        # 处理通知消息（无需响应）
        if method == "notifications/initialized":
            await self.handle_notifications_initialized()
            return
        elif method and method.startswith("notifications/"):
            # 忽略其他通知消息
            return
            
        # 处理请求消息（需要响应）
        if method == "initialize":
            await self.handle_initialize(request_id, params)
        elif method == "tools/list":
            await self.handle_list_tools(request_id, params)
        elif method == "tools/call":
            await self.handle_call_tool(request_id, params)
        elif method == "resources/list":
            await self.handle_list_resources(request_id, params)
        elif method == "prompts/list":
            await self.handle_list_prompts(request_id, params)
        else:
            # 对于未知方法，只有在有 request_id 时才响应
            if request_id is not None:
                self.send_response(request_id, None, {
                    "code": -32601,
                    "message": f"未知方法: {method}"
                })


async def main():
    """主函数"""
    server = MCPServer()
    
    try:
        await server.start()
        
        # 处理 stdin 输入
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    message = json.loads(line)
                    await server.handle_request(message)
                except json.JSONDecodeError as e:
                    print(f"JSON 解析错误: {e}", file=sys.stderr)
                    
            except EOFError:
                break
            except Exception as e:
                print(f"处理请求错误: {e}", file=sys.stderr)
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"服务器错误: {e}", file=sys.stderr)
    finally:
        await server.stop()
        print("MCP 服务器已停止", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())