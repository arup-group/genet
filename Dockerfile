FROM python:3.11.4-bullseye

RUN apt-get update && \
apt-get upgrade -y && \
apt-get -y install gcc git libgdal-dev libgeos-dev libspatialindex-dev curl coinor-cbc cmake &&  \
rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --compile --upgrade pip

COPY . ./src

RUN pip3 install --no-cache-dir --compile -e ./src && pip cache purge

