FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5 openpyxl==3.1.5

COPY refund_snapshot.json /root/refund_snapshot.json
COPY refund_adjustments.csv /root/refund_adjustments.csv
COPY refund_template.xlsx /root/refund_template.xlsx
COPY gl_balances.json /root/gl_balances.json

WORKDIR /root
