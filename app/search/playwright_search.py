#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信文章搜索引擎 - Playwright版本
基于搜狗微信搜索的高性能文章搜索服务
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlencode, urlparse, quote
from playwright.async_api import async_playwright, Browser, Page, TimeoutError
import aiohttp


class WeChatArticleSearcher:
    """微信文章搜索器"""
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.base_url = "https://weixin.sogou.com"
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        
        # 更新的用户代理池
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def init_browser(self):
        """初始化浏览器"""
        try:
            if self.playwright is None:
                self.playwright = await async_playwright().start()
            
            # 如果浏览器已经存在且连接正常，直接返回
            if self.browser and self.browser.is_connected():
                return
            
            # 浏览器启动配置
            browser_config = {
                "headless": self.headless,
                "args": [
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",  # 禁用图片加载以提高速度
                    "--disable-javascript",  # 可选：禁用JS以提高速度
                    "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                ]
            }
            
            if self.proxy:
                browser_config["proxy"] = {"server": self.proxy}
            
            self.browser = await self.playwright.chromium.launch(**browser_config)
            
            # 创建页面上下文
            context = await self.browser.new_context(
                user_agent=self.user_agents[0],
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,  # 忽略HTTPS错误
                java_script_enabled=False  # 禁用JavaScript以避免反爬检测
            )
            
            self.page = await context.new_page()
            
            # 设置页面加载超时
            self.page.set_default_timeout(30000)
            
            # 设置请求拦截，移除不必要的资源
            await self.page.route("**/*", self._intercept_request)
            
            self.logger.info("浏览器初始化成功")
            
        except Exception as e:
            self.logger.error(f"浏览器初始化失败: {str(e)}")
            await self._cleanup_browser_resources()
            raise
    
    async def _intercept_request(self, route):
        """拦截请求，只允许必要的资源"""
        resource_type = route.request.resource_type
        if resource_type in ["image", "media", "font", "stylesheet", "script"]:
            await route.abort()
        else:
            await route.continue_()
    
    async def _cleanup_browser_resources(self):
        """清理浏览器资源"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.browser:
                await self.browser.close()
                self.browser = None
        except Exception as e:
            self.logger.warning(f"清理浏览器资源时出现警告: {str(e)}")
    
    async def close(self):
        """关闭浏览器"""
        try:
            await self._cleanup_browser_resources()
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            self.logger.info("浏览器已关闭")
        except Exception as e:
            self.logger.error(f"关闭浏览器时出错: {str(e)}")
    
    async def search_articles(self, 
                            query: str, 
                            max_results: int = 10,
                            time_filter: Optional[str] = None) -> List[Dict]:
        """
        搜索微信文章
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数量
            time_filter: 时间筛选 (可选: "day", "week", "month", "year")
            
        Returns:
            包含文章信息的字典列表
        """
        # 输入验证
        if not query or not query.strip():
            self.logger.warning("搜索关键词为空")
            return []
        
        query = self._sanitize_query(query.strip())
        max_results = max(1, min(max_results, 50))  # 限制范围
        
        try:
            if not self.page or not self.browser or not self.browser.is_connected():
                await self.init_browser()
            
            self.logger.info(f"开始搜索: {query}")
            
            # 构建搜索URL
            search_url = f"{self.base_url}/weixin"
            params = {
                "query": query,
                "type": "2",  # 搜索文章
                "ie": "utf8"
            }
            
            if time_filter:
                time_code = self._get_time_filter_code(time_filter)
                if time_code:
                    params["tsn"] = time_code
            
            full_url = f"{search_url}?{urlencode(params)}"
            self.logger.debug(f"搜索URL: {full_url}")
            
            # 访问搜索页面，添加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.page.goto(full_url, wait_until="domcontentloaded", timeout=20000)
                    break
                except TimeoutError:
                    if attempt == max_retries - 1:
                        raise
                    self.logger.warning(f"页面加载超时，重试 {attempt + 1}/{max_retries}")
                    await asyncio.sleep(2)
            
            # 等待搜索结果加载，尝试多个可能的选择器
            result_selectors = [
                ".results",
                ".news-list", 
                "[data-key='search_result']",
                ".result-item",
                "li[id]"  # 通用的列表项选择器
            ]
            
            page_loaded = False
            for selector in result_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    self.logger.debug(f"找到选择器: {selector}")
                    page_loaded = True
                    break
                except TimeoutError:
                    continue
            
            if not page_loaded:
                self.logger.warning("未找到搜索结果容器，尝试解析页面内容")
            
            # 解析搜索结果
            articles = await self._parse_search_results(max_results)
            
            self.logger.info(f"搜索完成，找到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            self.logger.error(f"搜索过程中出错: {str(e)}")
            # 尝试重新初始化浏览器
            try:
                await self._cleanup_browser_resources()
                await self.init_browser()
            except:
                pass
            return []
    
    def _sanitize_query(self, query: str) -> str:
        """清理搜索查询，移除潜在危险字符"""
        # 移除HTML标签和特殊字符
        query = re.sub(r'[<>"\']', '', query)
        # 限制长度
        query = query[:100]
        return query.strip()
    
    async def _parse_search_results(self, max_results: int) -> List[Dict]:
        """解析搜索结果页面"""
        articles = []
        
        try:
            # 尝试多种选择器策略
            article_selectors = [
                ".results h3",  # 原始选择器
                ".news-box h3", # 新闻盒子标题
                ".result-item h3", # 结果项标题
                "li h3",  # 通用列表项标题
                "h3 a[href*='mp.weixin.qq.com']"  # 直接查找微信链接
            ]
            
            article_elements = []
            for selector in article_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        article_elements = elements
                        self.logger.debug(f"使用选择器找到文章: {selector}, 数量: {len(elements)}")
                        break
                except Exception as e:
                    self.logger.debug(f"选择器 {selector} 失败: {str(e)}")
                    continue
            
            if not article_elements:
                self.logger.warning("未找到文章元素，尝试备用解析方法")
                return await self._fallback_parse()
            
            for i, element in enumerate(article_elements[:max_results]):
                try:
                    article = await self._extract_article_info(element, i)
                    if article and article.get('title') and article.get('url'):
                        articles.append(article)
                        
                except Exception as e:
                    self.logger.warning(f"解析第 {i+1} 篇文章时出错: {str(e)}")
                    continue
            
        except Exception as e:
            self.logger.error(f"解析搜索结果时出错: {str(e)}")
        
        return articles
    
    async def _extract_article_info(self, element, index: int) -> Optional[Dict]:
        """从元素中提取文章信息"""
        try:
            # 获取文章标题和链接
            title_element = await element.query_selector("a")
            if not title_element:
                return None
            
            title = await title_element.inner_text()
            link = await title_element.get_attribute("href")
            
            if not title or not link:
                return None
            
            # 查找父容器获取更多信息
            parent_selectors = ["li", ".result-item", ".news-box", "div"]
            article_container = None
            
            for selector in parent_selectors:
                try:
                    container = await element.evaluate(f"el => el.closest('{selector}')")
                    if container:
                        article_container = await self.page.query_selector(f"xpath=//li[{index + 1}]")
                        break
                except:
                    continue
            
            # 获取文章描述
            description = ""
            if article_container:
                desc_selectors = ["p", ".txt-info", ".content-info", "span"]
                for desc_sel in desc_selectors:
                    try:
                        desc_element = await article_container.query_selector(desc_sel)
                        if desc_element:
                            desc_text = await desc_element.inner_text()
                            if desc_text and len(desc_text.strip()) > 10:
                                description = desc_text
                                break
                    except:
                        continue
            
            # 获取来源和时间信息
            source = ""
            publish_time = ""
            
            if article_container:
                meta_selectors = [".s-p", ".time", ".source", ".meta-info"]
                for meta_sel in meta_selectors:
                    try:
                        meta_element = await article_container.query_selector(meta_sel)
                        if meta_element:
                            meta_text = await meta_element.inner_text()
                            if meta_text:
                                source, publish_time = self._parse_meta_info(meta_text)
                                break
                    except:
                        continue
            
            # 清理和标准化数据
            article = {
                "title": self._clean_text(title),
                "url": self._resolve_url(link),
                "source": self._clean_text(source) or "微信公众号",
                "date": publish_time or datetime.now().strftime("%Y-%m-%d"),
                "snippet": self._clean_text(description)[:200] + "..." if len(description) > 200 else self._clean_text(description)
            }
            
            return article
            
        except Exception as e:
            self.logger.debug(f"提取文章信息失败: {str(e)}")
            return None
    
    async def _fallback_parse(self) -> List[Dict]:
        """备用解析方法，直接查找页面中的链接"""
        articles = []
        try:
            # 查找所有微信文章链接
            links = await self.page.query_selector_all("a[href*='mp.weixin.qq.com']")
            
            for i, link in enumerate(links[:10]):  # 限制数量
                try:
                    title = await link.inner_text()
                    url = await link.get_attribute("href")
                    
                    if title and url:
                        articles.append({
                            "title": self._clean_text(title),
                            "url": self._resolve_url(url),
                            "source": "微信公众号",
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "snippet": ""
                        })
                except:
                    continue
                    
        except Exception as e:
            self.logger.error(f"备用解析失败: {str(e)}")
        
        return articles
    
    def _parse_meta_info(self, meta_text: str) -> tuple:
        """解析元信息，提取来源和时间"""
        if not meta_text:
            return "", ""
        
        # 尝试多种格式解析
        patterns = [
            r'(.+?)\s+(\d{4}-\d{2}-\d{2})',  # 来源 日期
            r'(.+?)\s+(\d+天前|\d+小时前|\d+分钟前)',  # 来源 相对时间
            r'(.+?)\s+(.+)',  # 通用格式
        ]
        
        for pattern in patterns:
            match = re.match(pattern, meta_text.strip())
            if match:
                return match.group(1).strip(), match.group(2).strip()
        
        # 如果没有匹配，返回原文本作为来源
        return meta_text.strip(), ""
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除多余空格和特殊字符"""
        if not text:
            return ""
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除多余空格和换行
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空格
        text = text.strip()
        
        return text
    
    def _resolve_url(self, url: str) -> str:
        """解析URL，处理相对路径"""
        if not url:
            return ""
        
        if url.startswith("http"):
            return url
        elif url.startswith("/"):
            return f"{self.base_url}{url}"
        else:
            return url
    
    def _get_time_filter_code(self, time_filter: str) -> str:
        """获取时间筛选代码"""
        filters = {
            "day": "1",
            "week": "7", 
            "month": "30",
            "year": "365"
        }
        return filters.get(time_filter.lower(), "")


# 兼容性接口，与原miku_ai保持一致
async def get_wexin_article(query: str, top_num: int = 5) -> List[Dict]:
    """
    兼容原miku_ai接口的搜索函数
    
    Args:
        query: 搜索关键词
        top_num: 返回文章数量
        
    Returns:
        文章列表
    """
    async with WeChatArticleSearcher() as searcher:
        articles = await searcher.search_articles(query, top_num)
        
        # 转换为兼容格式
        compatible_articles = []
        for article in articles:
            compatible_articles.append({
                "title": article["title"],
                "url": article["url"],
                "source": article["source"],
                "date": article["date"],
                "snippet": article.get("snippet", "")
            })
        
        return compatible_articles


# 测试函数
async def test_search():
    """测试搜索功能"""
    async with WeChatArticleSearcher() as searcher:
        results = await searcher.search_articles("人工智能", 5)
        
        print(f"找到 {len(results)} 篇文章：")
        for i, article in enumerate(results, 1):
            print(f"\n{i}. {article['title']}")
            print(f"   来源: {article['source']}")
            print(f"   时间: {article['date']}")
            print(f"   链接: {article['url']}")
            if article['snippet']:
                print(f"   摘要: {article['snippet'][:100]}...")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_search())