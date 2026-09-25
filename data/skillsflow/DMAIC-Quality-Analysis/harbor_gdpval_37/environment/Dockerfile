FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pandas==2.2.3 \
    openpyxl==3.1.5

COPY process_capability_data.xlsx /root/process_capability_data.xlsx

# Copy skills to common agent locations without modification.

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /root
