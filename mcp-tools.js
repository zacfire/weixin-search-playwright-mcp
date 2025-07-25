// 微信文章搜索 MCP 工具实现
// 基于现有 Playwright MCP 的搜索功能

/**
 * 搜索微信公众号文章
 * @param {string} query - 搜索关键词
 * @param {number} maxResults - 最大结果数量
 * @param {string} timeFilter - 时间筛选
 */
async function searchWeChatArticles(query, maxResults = 5, timeFilter = null) {
    // 构建搜索URL
    const baseUrl = 'https://weixin.sogou.com/weixin';
    const params = new URLSearchParams({
        query: query,
        type: '2', // 搜索文章
        ie: 'utf8'
    });
    
    // 添加时间筛选
    if (timeFilter) {
        const timeMap = {
            'day': '1',
            'week': '7', 
            'month': '30',
            'year': '365'
        };
        if (timeMap[timeFilter]) {
            params.set('tsn', timeMap[timeFilter]);
        }
    }
    
    const searchUrl = `${baseUrl}?${params.toString()}`;
    
    // 使用 Playwright MCP 访问页面
    await page.goto(searchUrl, { waitUntil: 'networkidle' });
    
    // 等待搜索结果加载
    try {
        await page.waitForSelector('ul li', { timeout: 10000 });
    } catch (error) {
        console.log('等待搜索结果超时，尝试解析现有内容');
    }
    
    // 提取文章信息
    const articles = await page.evaluate((maxResults) => {
        const results = [];
        
        // 查找文章列表项
        const listItems = document.querySelectorAll('ul li');
        
        for (let i = 0; i < Math.min(listItems.length, maxResults); i++) {
            const item = listItems[i];
            
            // 查找标题链接
            const titleLink = item.querySelector('h3 a') || 
                             item.querySelector('a[href*="/link"]');
            
            if (titleLink) {
                const title = titleLink.textContent.trim();
                const url = titleLink.href;
                
                // 查找描述段落
                const descParagraph = item.querySelector('p');
                const description = descParagraph ? 
                    descParagraph.textContent.trim().substring(0, 200) : '';
                
                // 查找元信息（来源和时间）
                const metaElements = item.querySelectorAll('div');
                let source = '微信公众号';
                let publishTime = '最近';
                
                metaElements.forEach(meta => {
                    const text = meta.textContent.trim();
                    if (text.includes('前') || text.includes('小时') || text.includes('分钟')) {
                        publishTime = text;
                    } else if (text.length > 0 && text.length < 30 && 
                              !text.includes('http') && !text.includes('前')) {
                        source = text;
                    }
                });
                
                if (title && url && title.length > 3) {
                    results.push({
                        title: title.replace(/\s+/g, ' ').trim(),
                        url: url,
                        source: source,
                        date: publishTime,
                        snippet: description.replace(/\s+/g, ' ').trim()
                    });
                }
            }
        }
        
        return results;
    }, maxResults);
    
    return {
        query: query,
        total_count: articles.length,
        articles: articles,
        search_time: new Date().toISOString(),
        source: 'sogou-weixin-search'
    };
}

// 导出工具函数
module.exports = {
    searchWeChatArticles
};