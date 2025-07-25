# 微信文章搜索 MCP

基于 Playwright 的微信文章搜索工具，专为 Claude MCP 设计，替代不稳定的第三方库。

## ✨ 特性

- **稳定可靠**: 直接访问搜狗微信搜索，避免第三方库限流
- **MCP 集成**: 专为 Claude MCP 优化，无缝集成
- **智能解析**: 多重选择器策略，提高解析成功率

## 🚀 Claude MCP 配置

### 1. 安装依赖
```bash
cd /Users/zac/weixin-search-playwright-mcp
pip install -r requirements.txt
playwright install chromium
```

### 2. MCP 已自动配置
Claude Desktop 配置文件已更新，使用完整 Python 路径避免环境问题。

### 3. 使用方式
```
搜索微信文章：人工智能
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

## 🐛 故障排除

1. **MCP 连接失败**: 重启 Claude Desktop
2. **Python 路径错误**: 确保配置使用完整路径如 `/Users/zac/miniconda3/bin/python`
3. **搜索无结果**: 检查网络连接和关键词

---

基于 Playwright 的稳定搜索方案，替代不可靠的第三方库。