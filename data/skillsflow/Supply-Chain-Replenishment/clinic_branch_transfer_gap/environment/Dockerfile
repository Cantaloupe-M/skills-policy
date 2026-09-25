FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN python3 -m pip install --no-cache-dir --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5 openpyxl==3.1.5
COPY Clinic_Branch_Inventory.xlsx /root/Clinic_Branch_Inventory.xlsx
COPY Clinic_Transfer_Schedule.xlsx /root/Clinic_Transfer_Schedule.xlsx
WORKDIR /root
