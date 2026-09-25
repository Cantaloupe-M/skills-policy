FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5

RUN mkdir -p /opt/harbor && cd /opt/harbor && npm init -y && npm install xlsx@0.18.5

ENV NODE_PATH=/opt/harbor/node_modules

COPY Backup_Fuel_and_Refills_Latest.xlsx /root/Backup_Fuel_and_Refills_Latest.xlsx


WORKDIR /root
