FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages --no-cache-dir pandas==2.2.2 pytest pytest-json-ctrf

WORKDIR /root
COPY data /root/environment/data