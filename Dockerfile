# 使用官方轻量级 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 1. 安装依赖
# 复制 requirements.txt 到容器中
COPY requirements.txt .
# 安装依赖，--no-cache-dir 减小镜像体积
RUN pip install --no-cache-dir -r requirements.txt

# 2. 复制项目代码
# 将当前目录下的所有文件复制到容器的 /app 目录
COPY . .

# 3. 设置环境变量
# 确保 Python 输出直接打印到控制台 (对 Cloud Run 日志很重要)
ENV PYTHONUNBUFFERED=1
# 告诉 settings.py 证书在哪里 (容器内路径)
ENV SSL_CERT_FILE=/usr/local/lib/python3.11/site-packages/certifi/cacert.pem
ENV REQUESTS_CA_BUNDLE=/usr/local/lib/python3.11/site-packages/certifi/cacert.pem

# 4. 启动命令
# Cloud Run 会自动注入 $PORT 环境变量 (通常是 8080)
# 我们使用 gunicorn 管理 uvicorn worker
# 格式: gunicorn -w [workers] -k [worker_class] [module_path]:[app_variable]
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 src.services.product_catalog:app -k uvicorn.workers.UvicornWorker
