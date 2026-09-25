FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y             python3             python3-pip             && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages             openpyxl==3.1.5             pytest==8.4.1             pytest-json-ctrf==0.3.5

COPY radiology_reading_reference.xlsx /root/radiology_reading_reference.xlsx

WORKDIR /root
