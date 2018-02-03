FROM python:3.4-slim

WORKDIR /jte/src

ADD . /jte

RUN pip install --trusted-host pypi.python.org -r ../requirements.txt

EXPOSE 5000

CMD ["python3", "server.py"]
