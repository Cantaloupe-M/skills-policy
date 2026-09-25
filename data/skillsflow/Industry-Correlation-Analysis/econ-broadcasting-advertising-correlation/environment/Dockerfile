FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     curl     git     vim     && rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages --no-cache-dir     pandas==2.2.3     numpy==1.26.4     openpyxl==3.1.5     scipy==1.14.1     statsmodels==0.14.4

RUN pip install --break-system-packages --no-cache-dir     pytest==8.4.1     pytest-json-ctrf==0.3.5

WORKDIR /root
COPY media_release_table_05.xlsx /root/
COPY media_release_table_12.xlsx /root/
COPY media_service_prices.xlsx /root/
