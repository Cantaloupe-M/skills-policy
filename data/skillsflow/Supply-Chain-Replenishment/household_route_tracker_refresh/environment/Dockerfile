FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN python3 -m pip install --no-cache-dir --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5 openpyxl==3.1.5
COPY Household_Route_Template.xlsx /root/Household_Route_Template.xlsx
COPY Household_Current_Stock.xlsx /root/Household_Current_Stock.xlsx
COPY Household_Dispatch_Queue.xlsx /root/Household_Dispatch_Queue.xlsx
WORKDIR /root
