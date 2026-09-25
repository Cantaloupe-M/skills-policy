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

COPY COA.xlsx /root/COA.xlsx
COPY Aurisic_Prepaid_Expenses_Jan25.pdf /root/Aurisic_Prepaid_Expenses_Jan25.pdf
COPY Aurisic_Prepaid_Expenses_Feb25.pdf /root/Aurisic_Prepaid_Expenses_Feb25.pdf
COPY Aurisic_Prepaid_Expenses_Mar25.pdf /root/Aurisic_Prepaid_Expenses_Mar25.pdf
COPY Aurisic_Prepaid_Expenses_Apr25.pdf /root/Aurisic_Prepaid_Expenses_Apr25.pdf
COPY Aurisic_Prepaid_Insurance.pdf /root/Aurisic_Prepaid_Insurance.pdf
COPY prepaid_expenses_schedule_input.csv /root/prepaid_expenses_schedule_input.csv
COPY prepaid_insurance_schedule_input.csv /root/prepaid_insurance_schedule_input.csv
COPY gl_balances.json /root/gl_balances.json

WORKDIR /root
