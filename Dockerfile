FROM ubuntu:jammy

WORKDIR /root

RUN apt-get update && \
    apt-get install -y build-essential libvips-dev vim python3 python3-pip imagemagick libjxr-dev  libjxr-tools


COPY . /root

RUN cd /root && pip install --upgrade pip && \
    pip install -r requirements.txt

ENTRYPOINT [ "/root/script.py" ]