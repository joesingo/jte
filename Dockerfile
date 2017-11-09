FROM python:3.4-slim

WORKDIR /jte

ADD . /jte

RUN pip install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 80

CMD ["python3", "server.py"]
