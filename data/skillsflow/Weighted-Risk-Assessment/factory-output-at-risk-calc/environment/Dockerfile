FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gnumeric \
    python3-openpyxl \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /root
RUN mkdir -p /root/data /root/output
COPY workbook.xlsx /root/data/workbook.xlsx
