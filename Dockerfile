FROM python:latest

MAINTAINER Eliot Lear "lear@lear.ch"

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app

ENTRYPOINT [ "uwsgi" ]

CMD ["uwsgi.ini"]

