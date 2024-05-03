FROM alpine:latest

MAINTAINER Eliot Lear "lear@lear.ch"

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN apk add python3 uwsgi-cgi py3-cryptography py3-pip py3-werkzeug \
    	    py3-flask py3-authlib uwsgi-http uwsgi uwsgi-python3 tzdata && \
    pip3 install -r requirements.txt

COPY . /app

ENTRYPOINT [ "uwsgi" ]

CMD ["--http-socket",":8191","--plugin","python","uwsgi.ini"]

