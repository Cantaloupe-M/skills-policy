FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     python3-pytest     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY compound_cost.csv /root/compound_cost.csv
COPY mailer_cost.csv /root/mailer_cost.csv
COPY base_payment.csv /root/base_payment.csv
COPY service_fee.csv /root/service_fee.csv

WORKDIR /root
