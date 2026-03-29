FROM python:3.10-slim-bookworm

WORKDIR /app

# 更换为阿里云源
RUN rm -f /etc/apt/sources.list.d/debian.sources && \
    echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装基本依赖和生物信息学工具
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git curl wget bash ca-certificates xz-utils \
    fastqc trimmomatic spades samtools bowtie2 bcftools openjdk-17-jre && \
    rm -rf /var/lib/apt/lists/*

# 安装 Node.js
RUN curl -L -o /tmp/node.tar.xz "https://nodejs.org/dist/v20.11.1/node-v20.11.1-linux-x64.tar.xz" && \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && \
    rm /tmp/node.tar.xz && \
    node --version && npm --version

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 创建上传目录
RUN mkdir -p uploads

# 暴露端口
EXPOSE 8004

# 启动命令
CMD sh -c "echo 'Starting backend...' & cd backend && python main.py"