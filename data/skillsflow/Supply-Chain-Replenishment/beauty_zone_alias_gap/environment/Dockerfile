FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN python3 -m pip install --no-cache-dir --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5 openpyxl==3.1.5
COPY Beauty_Zone_Stock.xlsx /root/Beauty_Zone_Stock.xlsx
COPY Beauty_Mixed_Feed.xlsx /root/Beauty_Mixed_Feed.xlsx
COPY Beauty_Zone_Alias_Key.xlsx /root/Beauty_Zone_Alias_Key.xlsx
WORKDIR /root
