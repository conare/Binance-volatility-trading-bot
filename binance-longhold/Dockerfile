FROM python:3.9.5-buster

WORKDIR /app

VOLUME [ "/app" ]

COPY requirements.txt requirements.txt 

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN cp moonings.py bot.py
