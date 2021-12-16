FROM python:3.10-slim as builder 

RUN apt update -y && apt install openssh-client -y

ENV PYTHONUNBUFFERED True
COPY . /app 
WORKDIR /app 
RUN pip3 install --no-cache-dir -r /app/requirements.txt 

CMD gunicorn --bind :$PORT app:app
