FROM python:3.8-slim

ENV PYTHONBUFFERED True

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN pip install -r requirements.txt
RUN pip install dnspython
RUN pip install gunicorn

ARG CONFIG_FILE_ARG
ENV CONFIG_FILE=$CONFIG_FILE_ARG

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app