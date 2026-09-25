FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pandas==2.3.3 rapidfuzz==3.14.3 pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /root

COPY 2025-q2 /root/2025-q2
COPY 2025-q3 /root/2025-q3
