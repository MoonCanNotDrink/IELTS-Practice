# 使用官方轻量级 Python 3.12 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装必要的系统库 (供 Python 包编译使用及音频处理)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖清单并安装
# 设置缓存目录避免重复下载，加速重新构建
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制代码资源（包含前端和后端）
# 保持原有的相对目录结构，因为 main.py 强依赖于 ../frontend 静态文件路径
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# 设置后端为工作目录，FastAPI 从这里启动
WORKDIR /app/backend

# 创建数据存储目录，存放 SQLite 数据库和音频录音文件
RUN mkdir -p data/recordings

# 暴露 FastAPI 运行端口
EXPOSE 8000

# 启动命令 (使用 Cloud Run 动态注入的 $PORT 环境变量，默认为 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
