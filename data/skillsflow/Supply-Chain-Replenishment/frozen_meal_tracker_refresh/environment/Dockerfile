FROM skillflow/harbor-cli-base:ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN python3 -m pip install --no-cache-dir --break-system-packages pytest==8.4.1 pytest-json-ctrf==0.3.5 openpyxl==3.1.5
COPY Frozen_Meal_Template.xlsx /root/Frozen_Meal_Template.xlsx
COPY Frozen_Meal_Current_Stock.xlsx /root/Frozen_Meal_Current_Stock.xlsx
COPY Frozen_Meal_Recovery_Log.xlsx /root/Frozen_Meal_Recovery_Log.xlsx
WORKDIR /root
