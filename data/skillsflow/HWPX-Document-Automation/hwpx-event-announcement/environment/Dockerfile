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

COPY event_announcement_template.hwpx /root/event_announcement_template.hwpx
COPY event_data.json /root/event_data.json

WORKDIR /root
