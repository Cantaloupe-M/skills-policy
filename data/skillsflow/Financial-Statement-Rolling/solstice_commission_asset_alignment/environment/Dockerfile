FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5 openpyxl==3.1.5

COPY commission_activity.json /root/commission_activity.json
COPY commission_metadata.csv /root/commission_metadata.csv
COPY gl_balances.json /root/gl_balances.json

WORKDIR /root
