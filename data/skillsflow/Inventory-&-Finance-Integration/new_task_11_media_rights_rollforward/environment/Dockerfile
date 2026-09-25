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

COPY film_rights_schedule_input.csv /root/film_rights_schedule_input.csv
COPY music_rights_schedule_input.csv /root/music_rights_schedule_input.csv
COPY rights_ledger_balances.json /root/rights_ledger_balances.json
COPY Aurora_Film_Licensor_Invoices_Q1Q2_2025.txt /root/Aurora_Film_Licensor_Invoices_Q1Q2_2025.txt
COPY Aurora_Music_Licensor_Invoices_Q1Q2_2025.txt /root/Aurora_Music_Licensor_Invoices_Q1Q2_2025.txt
COPY aurora_rights_ledger_control_notes_apr25.txt /root/aurora_rights_ledger_control_notes_apr25.txt


WORKDIR /root
