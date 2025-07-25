#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版微信文章搜索MCP服务
基于Playwright的高性能、稳定的微信文章搜索服务
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

# 导入我们的搜索引擎
from search.playwright_search import WeChatArticleSearcher

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 速率限制器
limiter = Limiter(key_func=get_remote_address)

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("微信文章搜索MCP服务启动中...")
    # 启动时执行
    try:
        await get_searcher()
        logger.info("搜索器预热完成")
    except Exception as e:
        logger.warning(f"搜索器预热失败: {str(e)}")
    
    yield
    
    # 关闭时执行
    logger.info("微信文章搜索MCP服务关闭中...")
    await cleanup_searcher()
    logger.info("服务已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="微信文章搜索MCP服务 Pro",
    description="基于Playwright的高性能微信文章搜索MCP服务，支持实时搜索和高级筛选",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加速率限制状态
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 全局搜索器实例（用于复用浏览器）
global_searcher: Optional[WeChatArticleSearcher] = None

# 数据模型定义
class ArticleResponse(BaseModel):
    """文章响应模型"""
    title: str = Field(description="文章标题")
    url: str = Field(description="文章链接")
    source: str = Field(description="文章来源")
    date: str = Field(description="发布日期")
    snippet: str = Field(default="", description="文章摘要")

class ArticleSearchRequest(BaseModel):
    """文章搜索请求模型"""
    query: str = Field(min_length=1, max_length=100, description="搜索关键词")
    max_results: int = Field(default=5, ge=1, le=20, description="最大结果数量")
    time_filter: Optional[str] = Field(
        default=None, 
        description="时间筛选：day/week/month/year"
    )
    use_cache: bool = Field(default=True, description="是否使用缓存")
    
    @validator('query')
    def validate_query(cls, v):
        # 移除潜在危险字符
        import re
        v = re.sub(r'[<>"\']', '', v)
        return v.strip()
    
    @validator('time_filter')
    def validate_time_filter(cls, v):
        if v and v not in ['day', 'week', 'month', 'year']:
            raise ValueError('时间筛选必须是: day, week, month, year 之一')
        return v

class ArticleSearchResponse(BaseModel):
    """文章搜索响应模型"""
    articles: List[ArticleResponse] = Field(description="文章列表")
    total_count: int = Field(description="找到的文章总数")
    search_time: float = Field(description="搜索耗时（秒）")
    query: str = Field(description="搜索关键词")
    timestamp: str = Field(description="搜索时间戳")

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(description="服务状态")
    service: str = Field(description="服务名称")
    version: str = Field(description="服务版本")
    uptime: float = Field(description="运行时间（秒）")
    browser_status: str = Field(description="浏览器状态")

# 启动时间记录
start_time = time.time()

# 简单的内存缓存
search_cache = {}
CACHE_EXPIRE_TIME = 300  # 5分钟缓存

async def get_searcher() -> WeChatArticleSearcher:
    """获取搜索器实例"""
    global global_searcher
    
    if global_searcher is None:
        try:
            global_searcher = WeChatArticleSearcher(headless=True)
            await global_searcher.init_browser()
            logger.info("搜索器初始化成功")
        except Exception as e:
            logger.error(f"搜索器初始化失败: {str(e)}")
            raise HTTPException(status_code=500, detail="搜索服务初始化失败")
    
    return global_searcher

async def cleanup_searcher():
    """清理搜索器"""
    global global_searcher
    if global_searcher:
        await global_searcher.close()
        global_searcher = None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    uptime = time.time() - start_time
    
    # 检查浏览器状态
    browser_status = "unknown"
    try:
        if global_searcher and global_searcher.browser:
            browser_status = "running"
        else:
            browser_status = "stopped"
    except:
        browser_status = "error"
    
    return HealthResponse(
        status="ok",
        service="微信文章搜索MCP Pro",
        version="2.0.0",
        uptime=uptime,
        browser_status=browser_status
    )

@app.post("/search_articles", response_model=ArticleSearchResponse)
@limiter.limit("10/minute")
async def search_articles(request: Request, search_request: ArticleSearchRequest):
    """搜索微信文章接口"""
    start_search_time = time.time()
    
    # 验证搜索关键词
    if not search_request.query or not search_request.query.strip():
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")
    
    query = search_request.query.strip()
    cache_key = f"{query}_{search_request.max_results}_{search_request.time_filter}"
    
    # 检查缓存
    if search_request.use_cache and cache_key in search_cache:
        cache_data, cache_time = search_cache[cache_key]
        if time.time() - cache_time < CACHE_EXPIRE_TIME:
            logger.info(f"使用缓存结果: {query}")
            return cache_data
    
    try:
        # 获取搜索器
        searcher = await get_searcher()
        
        # 执行搜索
        logger.info(f"开始搜索: {query}")
        articles = await searcher.search_articles(
            query=query,
            max_results=search_request.max_results,
            time_filter=search_request.time_filter
        )
        
        # 转换为响应格式
        article_responses = [
            ArticleResponse(
                title=article.get('title', ''),
                url=article.get('url', ''),
                source=article.get('source', ''),
                date=article.get('date', ''),
                snippet=article.get('snippet', '')
            )
            for article in articles
        ]
        
        search_time = time.time() - start_search_time
        
        response = ArticleSearchResponse(
            articles=article_responses,
            total_count=len(article_responses),
            search_time=round(search_time, 2),
            query=query,
            timestamp=datetime.now().isoformat()
        )
        
        # 缓存结果
        if search_request.use_cache:
            search_cache[cache_key] = (response, time.time())
        
        logger.info(f"搜索完成: {query}, 耗时: {search_time:.2f}s, 结果: {len(articles)}篇")
        
        return response
        
    except Exception as e:
        logger.error(f"搜索出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.post("/search_articles_compatible")
@limiter.limit("10/minute")
async def search_articles_compatible(request: Request, search_data: dict):
    """兼容原版API的搜索接口"""
    try:
        # 验证输入数据
        if not isinstance(search_data, dict):
            raise HTTPException(status_code=400, detail="请求数据必须是JSON对象")
        
        # 转换为新的请求格式
        search_request = ArticleSearchRequest(
            query=search_data.get('query', ''),
            max_results=min(search_data.get('top_num', 5), 20)  # 限制最大数量
        )
        
        # 调用新接口
        response = await search_articles(request, search_request)
        
        # 转换为原版格式
        return {
            "articles": [
                {
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "date": article.date
                }
                for article in response.articles
            ],
            "total_count": response.total_count
        }
        
    except Exception as e:
        logger.error(f"兼容接口搜索出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """获取服务统计信息"""
    return {
        "uptime": time.time() - start_time,
        "cache_size": len(search_cache),
        "browser_status": "running" if global_searcher and global_searcher.browser else "stopped",
        "version": "2.0.0"
    }

@app.delete("/cache")
async def clear_cache():
    """清理搜索缓存"""
    global search_cache
    cache_count = len(search_cache)
    search_cache.clear()
    logger.info(f"缓存已清理，清理了 {cache_count} 条缓存")
    return {"message": f"已清理 {cache_count} 条缓存"}

@app.post("/restart_browser")
async def restart_browser():
    """重启浏览器"""
    try:
        await cleanup_searcher()
        await get_searcher()
        return {"message": "浏览器重启成功"}
    except Exception as e:
        logger.error(f"浏览器重启失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"浏览器重启失败: {str(e)}")

@app.get("/", include_in_schema=False)
async def root():
    """返回首页HTML"""
    return FileResponse("static/index.html")

# MCP 功能已移除，因为 fastapi-mcp 包不存在
# 如需要MCP支持，请使用官方MCP Python SDK

if __name__ == "__main__":
    # 使用导入字符串格式解决reload问题
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 生产环境建议关闭reload
        log_level="info",
        access_log=True
    )