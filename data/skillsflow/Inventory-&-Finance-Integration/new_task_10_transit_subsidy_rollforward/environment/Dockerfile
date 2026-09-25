FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5

RUN mkdir -p /opt/harbor && cd /opt/harbor && npm init -y && npm install xlsx@0.18.5

ENV NODE_PATH=/opt/harbor/node_modules

COPY bus_pass_schedule_input.csv /root/bus_pass_schedule_input.csv
COPY rail_pass_schedule_input.csv /root/rail_pass_schedule_input.csv
COPY fare_liability_balances.json /root/fare_liability_balances.json
COPY MetroLink_Bus_Pass_Issuance_Notes_Q1Q2_2025.txt /root/MetroLink_Bus_Pass_Issuance_Notes_Q1Q2_2025.txt
COPY MetroLink_Rail_Pass_Issuance_Notes_Q1Q2_2025.txt /root/MetroLink_Rail_Pass_Issuance_Notes_Q1Q2_2025.txt
COPY metrolink_fare_ledger_control_notes_apr25.txt /root/metrolink_fare_ledger_control_notes_apr25.txt


WORKDIR /root
