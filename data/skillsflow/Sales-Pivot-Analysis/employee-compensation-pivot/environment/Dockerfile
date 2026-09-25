FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    openpyxl==3.1.5 \
    pandas==2.2.3 \
    pdfplumber==0.11.4

COPY departments.pdf /root/departments.pdf
COPY employee_compensation.csv /root/employee_compensation.csv

RUN pip install --no-cache-dir \
    pytest==8.3.4 \
    pytest-json-ctrf==0.3.6

WORKDIR /root
