FROM skillflow/harbor-cli-base:ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     build-essential     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages     pytest==8.4.1     pytest-json-ctrf==0.3.5     pdfplumber==0.11.9     openpyxl==3.1.5     pandas==2.3.3     rapidfuzz==3.14.3

WORKDIR /root

COPY service_packets.pdf /root/service_packets.pdf
COPY contractor_directory.xlsx /root/contractor_directory.xlsx
COPY work_orders.csv /root/work_orders.csv
COPY work_order_revisions.csv /root/work_order_revisions.csv
