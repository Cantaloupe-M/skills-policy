FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     python3-pytest     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY assay_manifest.json /root/assay_manifest.json
COPY carrier_cost.csv /root/carrier_cost.csv
COPY billing.csv /root/billing.csv
COPY lab_overrides.csv /root/lab_overrides.csv
COPY report_template.json /root/report_template.json

WORKDIR /root
