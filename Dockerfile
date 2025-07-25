FROM python:3.11-slim

# 创建非root用户
RUN useradd -m -u 1000 appuser

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 使用非root用户安装Playwright
USER appuser
RUN playwright install chromium
RUN playwright install-deps chromium || echo "Warning: Some system dependencies may not be installed as non-root user"

# 切换回root用户复制文件
USER root

# 复制应用代码
COPY app/ .

# 更改文件所有权
RUN chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 添加健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]