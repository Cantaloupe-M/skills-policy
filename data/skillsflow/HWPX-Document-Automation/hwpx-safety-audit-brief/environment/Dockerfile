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

COPY safety_audit_template.hwpx /root/safety_audit_template.hwpx
COPY audit_overview.json /root/audit_overview.json
COPY corrective_actions.json /root/corrective_actions.json

WORKDIR /root
