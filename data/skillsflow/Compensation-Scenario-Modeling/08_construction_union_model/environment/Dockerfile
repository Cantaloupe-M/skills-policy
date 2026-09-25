FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN python3 -m pip install --break-system-packages     pytest==8.4.1     pytest-json-ctrf==0.3.5     openpyxl==3.1.5

COPY union_assumptions_and_roster.xlsx /root/union_assumptions_and_roster.xlsx
COPY project_codes.xlsx /root/project_codes.xlsx
COPY member_projects.xlsx /root/member_projects.xlsx

WORKDIR /root
