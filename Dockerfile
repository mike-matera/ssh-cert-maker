FROM python:3.10 as builder 

RUN adduser --system certmaker
USER certmaker
COPY . /app 
WORKDIR /app 
RUN pip3 install -r /app/requirements.txt 

ENTRYPOINT ["/home/certmaker/.local/bin/gunicorn", "app"]
