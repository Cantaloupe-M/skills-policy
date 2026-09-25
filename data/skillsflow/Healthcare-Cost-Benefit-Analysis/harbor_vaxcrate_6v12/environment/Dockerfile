FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     python3-pytest     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY campaign_manifest.json /root/campaign_manifest.json
COPY crate_cost.csv /root/crate_cost.csv
COPY billing.csv /root/billing.csv
COPY location_overrides.csv /root/location_overrides.csv
COPY suspensions.csv /root/suspensions.csv

WORKDIR /root
