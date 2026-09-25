FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     python3-pytest     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY program_catalog.json /root/program_catalog.json
COPY cooler_cost.csv /root/cooler_cost.csv
COPY contract_payment.csv /root/contract_payment.csv
COPY site_overrides.csv /root/site_overrides.csv

WORKDIR /root
