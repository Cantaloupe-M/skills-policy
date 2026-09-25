FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     python3-pytest     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY therapy_catalog.json /root/therapy_catalog.json
COPY bag_supply_cost.csv /root/bag_supply_cost.csv
COPY delivery_payment.csv /root/delivery_payment.csv
COPY patient_overrides.csv /root/patient_overrides.csv

WORKDIR /root
