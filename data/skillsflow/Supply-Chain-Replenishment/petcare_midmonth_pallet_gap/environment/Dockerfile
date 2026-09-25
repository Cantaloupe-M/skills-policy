FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN python3 -m pip install --no-cache-dir --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5 openpyxl==3.1.5
COPY Petcare_Midmonth_Snapshot.xlsx /root/Petcare_Midmonth_Snapshot.xlsx
WORKDIR /root
