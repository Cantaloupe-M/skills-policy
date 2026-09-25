FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     python3-pytest     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY acquisition_cost.csv /root/acquisition_cost.csv
COPY packaging_cost.csv /root/packaging_cost.csv
COPY reimbursement.csv /root/reimbursement.csv

WORKDIR /root
