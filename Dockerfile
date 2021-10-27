FROM python:3.7-slim-stretch

RUN apt-get update && \
apt-get upgrade -y && \
apt-get -y install gcc git libspatialindex-dev curl &&  \
rm -rf /var/lib/apt/lists/*

RUN curl -sL https://deb.nodesource.com/setup_17.x | bash -
RUN apt-get -y install nodejs && node --version && npm --version

RUN apt-get install -y coinor-cbc

RUN /usr/local/bin/python -m pip install --upgrade pip

COPY ./scripts .
COPY . .

RUN pip3 install -e .
ENV PYTHONPATH=./scripts:${PYTHONPATH}

ENTRYPOINT ["python3"]