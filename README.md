# 微信文章搜索 MCP

基于 Playwright 的微信文章搜索工具，专为 Claude MCP 设计，替代不稳定的第三方库。

## ✨ 特性

- **稳定可靠**: 直接访问搜狗微信搜索，避免第三方库限流
- **MCP 集成**: 专为 Claude MCP 优化，无缝集成
- **智能解析**: 多重选择器策略，提高解析成功率

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/zacfire/weixin-search-playwright-mcp.git
cd weixin-search-playwright-mcp
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. 配置 Claude MCP
将以下配置添加到 Claude Desktop 配置文件：
```json
{
  "mcpServers": {
    "wechat-search": {
      "command": "/path/to/your/python",
      "args": ["/path/to/weixin-search-playwright-mcp/mcp_server.py"],
      "description": "微信文章搜索服务",
      "cwd": "/path/to/weixin-search-playwright-mcp"
    }
  }
}
```

### 4. 重启 Claude Desktop

### 5. 开始使用
```
搜索微信文章：人工智能
搜索最新10篇关于"机器学习"的微信文章
搜索本周关于"ChatGPT"的微信文章
```

## 📊 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| query | string | 必填 | 搜索关键词 |
| max_results | integer | 5 | 结果数量 (1-20) |
| time_filter | string | null | 时间筛选: day/week/month/year |

## 🧪 测试

```bash
python test_search.py --search
```

## ✅ 功能特色

- **实时搜索**: 获取最新的微信公众号文章
- **智能筛选**: 支持按时间范围筛选（日/周/月/年）
- **丰富信息**: 包含标题、来源、发布时间、摘要和链接
- **稳定可靠**: 直接访问搜狗搜索，避免第三方API限制

## 🐛 故障排除

1. **MCP 连接失败**: 重启 Claude Desktop
2. **Python 路径错误**: 使用 `which python` 获取完整路径
3. **搜索无结果**: 检查网络连接和关键词
4. **ZodError**: 确保使用最新版本的 mcp_server.py

## 📝 更新日志

- ✅ 完全符合 MCP 协议，无 ZodError
- ✅ 支持完整的微信文章搜索功能
- ✅ 智能解析文章标题、来源、时间等信息
- ✅ 已在 Claude Desktop 中验证可用

---

🎯 **目标达成**: 稳定的微信文章搜索 MCP 服务，完美替代不可靠的第三方库。