FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     python3-pytest     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY panel_manifest.json /root/panel_manifest.json
COPY shipper_cost.csv /root/shipper_cost.csv
COPY contract_terms.csv /root/contract_terms.csv
COPY network_adjustments.csv /root/network_adjustments.csv
COPY lab_capacity_overrides.csv /root/lab_capacity_overrides.csv
COPY holdouts.json /root/holdouts.json
COPY report_template.json /root/report_template.json

WORKDIR /root
