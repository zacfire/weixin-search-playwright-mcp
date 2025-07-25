# 微信文章搜索 MCP Pro

基于 Playwright 的高性能微信文章搜索服务，替代不稳定的第三方库，提供真正可用的搜索功能。

## 🚀 主要特性

- **稳定可靠**: 使用 Playwright 直接访问搜狗微信搜索，避免第三方库限流问题
- **高性能**: 优化的浏览器配置，禁用不必要资源加载
- **现代化API**: FastAPI 构建的 RESTful API，支持 OpenAPI 文档
- **安全加固**: 输入验证、速率限制、CORS 配置
- **容器化部署**: Docker 和 docker-compose 支持
- **友好界面**: 内置现代化 Web 界面
- **向后兼容**: 保持与原 miku_ai 接口兼容

## 📋 快速开始

### 方法1: Docker 部署 (推荐)

```bash
# 克隆项目
git clone <repository-url>
cd weixin-search-playwright-mcp

# 使用 docker-compose 启动
docker-compose up -d

# 查看日志
docker-compose logs -f weixin-search
```

### 方法2: 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 启动服务
cd app
python main.py
```

服务启动后访问:
- API 文档: http://localhost:8000/docs
- Web 界面: http://localhost:8000
- 健康检查: http://localhost:8000/health

## 🔧 API 使用

### 搜索文章 (新版API)

```bash
curl -X POST "http://localhost:8000/search_articles" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能",
    "max_results": 10,
    "time_filter": "month",
    "use_cache": true
  }'
```

### 兼容接口 (原版格式)

```bash
curl -X POST "http://localhost:8000/search_articles_compatible" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "机器学习",
    "top_num": 5
  }'
```

### Python 调用示例

```python
import asyncio
from search.playwright_search import WeChatArticleSearcher

async def search_example():
    async with WeChatArticleSearcher() as searcher:
        articles = await searcher.search_articles("AI技术", max_results=5)
        for article in articles:
            print(f"标题: {article['title']}")
            print(f"来源: {article['source']}")
            print(f"链接: {article['url']}")
            print("-" * 50)

# 运行搜索
asyncio.run(search_example())
```

## 🧪 测试验证

```bash
# 测试搜索功能
python test_search.py --search

# 测试API服务 (需先启动服务)
python test_search.py --api
```

## 📊 API 参数说明

### ArticleSearchRequest

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| query | string | 必填 | 搜索关键词 (1-100字符) |
| max_results | integer | 5 | 最大结果数量 (1-20) |
| time_filter | string | null | 时间筛选: day/week/month/year |
| use_cache | boolean | true | 是否使用缓存 |

### ArticleResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 文章标题 |
| url | string | 文章链接 |
| source | string | 文章来源 |
| date | string | 发布日期 |
| snippet | string | 文章摘要 |

## 🔒 安全特性

- **速率限制**: 每分钟最多 10 次请求
- **输入验证**: 自动清理危险字符
- **CORS 配置**: 跨域访问控制
- **非 root 运行**: Docker 容器使用普通用户
- **健康检查**: 自动监控服务状态

## 🛠️ 配置选项

### 环境变量

- `PYTHONUNBUFFERED=1`: Python 输出不缓冲
- `PLAYWRIGHT_BROWSERS_PATH`: Playwright 浏览器路径

### Docker 资源限制

- 内存限制: 1GB
- CPU 限制: 1 核心
- 内存预留: 512MB

## 📈 性能优化

1. **浏览器优化**:
   - 禁用图片、CSS、JavaScript 加载
   - 使用轻量级 Chromium
   - 请求拦截机制

2. **缓存策略**:
   - 内存缓存搜索结果 (5分钟)
   - Docker 卷持久化浏览器缓存

3. **并发控制**:
   - 全局浏览器实例复用
   - 异步操作优化

## 🐛 故障排除

### 常见问题

1. **搜索返回空结果**
   - 检查网络连接
   - 验证搜狗微信搜索是否可访问
   - 查看日志中的错误信息

2. **Docker 启动失败**
   - 确保端口 8000 未被占用
   - 检查 Docker 和 docker-compose 版本
   - 查看容器日志: `docker logs weixin-search-mcp`

3. **Playwright 安装问题**
   - 手动安装: `playwright install chromium`
   - 检查系统依赖: `playwright install-deps chromium`

### 日志查看

```bash
# Docker 日志
docker-compose logs -f

# 本地运行日志
tail -f app.log
```

## 🔄 从原版迁移

如果你之前使用 miku_ai 库，只需要替换导入：

```python
# 原版
from miku_ai import get_wexin_article

# 新版
from search.playwright_search import get_wexin_article
```

API 调用方式保持不变，完全向后兼容。

## 📝 更新日志

### v2.0.0
- ✅ 移除 miku_ai 依赖，使用 Playwright 实现
- ✅ 修复浏览器资源管理问题
- ✅ 添加输入验证和安全加固
- ✅ 优化选择器，提高解析成功率
- ✅ 新增速率限制和错误处理
- ✅ Docker 安全配置改进

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 提交 Pull Request

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 💡 技术支持

如遇问题，请通过以下方式获取支持：

1. 查看本文档的故障排除部分
2. 检查 GitHub Issues
3. 提交新的 Issue 并提供详细错误信息

---

**注意**: 本项目仅用于学习和研究目的，请遵守相关网站的使用条款和法律法规。