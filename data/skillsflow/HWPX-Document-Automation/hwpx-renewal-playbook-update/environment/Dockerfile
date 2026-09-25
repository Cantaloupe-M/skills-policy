FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pytest-json-ctrf==0.3.5

COPY renewal_playbook.hwpx /root/renewal_playbook.hwpx
COPY renewal_update.json /root/renewal_update.json
COPY followups.csv /root/followups.csv

WORKDIR /root
