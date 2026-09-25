FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN python3 -m pip install --break-system-packages     pytest==8.4.1     pytest-json-ctrf==0.3.5     openpyxl==3.1.5

COPY orchestra_assumptions_and_roster.xlsx /root/orchestra_assumptions_and_roster.xlsx

WORKDIR /root
