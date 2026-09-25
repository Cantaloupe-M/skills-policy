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

COPY compute_capacity_schedule_input.csv /root/compute_capacity_schedule_input.csv
COPY storage_capacity_schedule_input.csv /root/storage_capacity_schedule_input.csv
COPY capacity_ledger_balances.json /root/capacity_ledger_balances.json
COPY Nimbus_Compute_Reservation_Register_Q1Q2_2025.txt /root/Nimbus_Compute_Reservation_Register_Q1Q2_2025.txt
COPY Nimbus_Storage_Commitment_Register_Q1Q2_2025.txt /root/Nimbus_Storage_Commitment_Register_Q1Q2_2025.txt
COPY nimbus_platform_ledger_notes_apr25.txt /root/nimbus_platform_ledger_notes_apr25.txt


WORKDIR /root
