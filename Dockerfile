FROM alpine:latest

MAINTAINER Landon Noll "docker@ioccc.org"

RUN mkdir -p /app

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN apk add python3 uwsgi-cgi py3-cryptography py3-pip py3-werkzeug \
    	    py3-flask py3-authlib uwsgi-http uwsgi uwsgi-python3 tzdata && \
    python3 -m pip install --break-system-packages -r requirements.txt

COPY . /app

ENTRYPOINT [ "uwsgi" ]

CMD ["--http-socket",":5001","--plugin","python","uwsgi.ini"]

