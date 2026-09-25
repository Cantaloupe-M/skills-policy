FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pandas==2.2.2 \
    scipy==1.13.1 \
    numpy==1.26.4

COPY soc_alert_data.csv /root/soc_alert_data.csv

# Copy skills to common agent skill paths.

WORKDIR /root
