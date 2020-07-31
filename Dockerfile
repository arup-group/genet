FROM python:3.7-slim-stretch

RUN apt-get update &&  apt-get -y install gcc mono-mcs &&  rm -rf /var/lib/apt/lists/*
RUN apt-get update &&  apt-get upgrade -y &&  apt-get install -y git
RUN apt-get install -y libspatialindex-dev
RUN /usr/local/bin/python -m pip install --upgrade pip

COPY ./scripts .
COPY . .

RUN pip3 install -e .

ENV PYTHONPATH=./scripts:${PYTHONPATH}

ENTRYPOINT ["python3"]