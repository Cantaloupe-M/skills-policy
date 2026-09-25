FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends     python3     python3-pip     python3-pil     python3-openpyxl     python3-pytest     tesseract-ocr     libtesseract-dev     && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest-json-ctrf==0.3.5

COPY workspace /app/workspace

WORKDIR /app/workspace
