FROM skillflow/harbor-cli-base:ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     build-essential     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages     pytest==8.4.1     pytest-json-ctrf==0.3.5     pdfplumber==0.11.9     openpyxl==3.1.5     pandas==2.3.3     rapidfuzz==3.14.3

WORKDIR /root

COPY chargeback_packets.pdf /root/chargeback_packets.pdf
COPY provider_directory.xlsx /root/provider_directory.xlsx
COPY maintenance_orders.json /root/maintenance_orders.json
COPY maintenance_adjustments.csv /root/maintenance_adjustments.csv
