FROM python:3.10-slim-bookworm

# 设置工作目录
WORKDIR /app

# 阿里云源 + 基础工具
RUN rm -f /etc/apt/sources.list.d/debian.sources && \
    echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git curl wget bash ca-certificates xz-utils && \
    rm -rf /var/lib/apt/lists/*

# Node.js 20
RUN curl -L -o /tmp/node.tar.xz "https://nodejs.org/dist/v20.11.1/node-v20.11.1-linux-x64.tar.xz" && \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && \
    rm /tmp/node.tar.xz && \
    node --version && npm --version

# 复制项目文件
COPY . .

# pip 安装依赖（无 mamba）
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

RUN mkdir -p uploads

# 暴露 8004 端口（与 main.py 中设置的端口一致）
EXPOSE 8004

# 直接运行 main.py 文件
CMD sh -c "echo 'Starting backend...' & cd backend && python main.py"