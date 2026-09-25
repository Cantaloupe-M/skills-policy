FROM skillflow/harbor-cli-base:ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y     python3     python3-pip     build-essential     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages     pytest==8.4.1     pytest-json-ctrf==0.3.5     pdfplumber==0.11.9     openpyxl==3.1.5     pandas==2.3.3     rapidfuzz==3.14.3

WORKDIR /root

COPY shift_claims.pdf /root/shift_claims.pdf
COPY clinician_directory.xlsx /root/clinician_directory.xlsx
COPY shift_authorizations.csv /root/shift_authorizations.csv
COPY shift_crosswalk.csv /root/shift_crosswalk.csv
