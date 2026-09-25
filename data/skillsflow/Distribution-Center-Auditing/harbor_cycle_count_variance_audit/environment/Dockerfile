FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages     openpyxl==3.1.5     python-docx==1.1.2     pytest==8.4.1     pytest-json-ctrf==0.3.5

COPY Cycle_Plan.xlsx /root/Cycle_Plan.xlsx
COPY Count_Event_Log.xlsx /root/Count_Event_Log.xlsx
COPY Cycle_Template.xlsx /root/Cycle_Template.xlsx

WORKDIR /root
