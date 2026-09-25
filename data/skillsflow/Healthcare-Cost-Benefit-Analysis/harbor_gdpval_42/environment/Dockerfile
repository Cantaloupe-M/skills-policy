FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY Wholesale_Price.pdf /root/Wholesale_Price.pdf
COPY Reimbursement.pdf /root/Reimbursement.pdf
COPY wholesale_price.csv /root/wholesale_price.csv
COPY vial_price.csv /root/vial_price.csv
COPY reimbursement.csv /root/reimbursement.csv

WORKDIR /root
