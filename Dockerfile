FROM ubuntu:jammy

WORKDIR /root

RUN apt-get update && \
    apt-get install -y build-essential libvips-dev vim python3 python3-pip imagemagick libjxr-dev  libjxr-tools wget unzip

COPY requirements.txt /root

RUN cd /root && pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . /root

RUN wget https://github.com/cmcfadden/czifile/archive/refs/heads/master.zip
RUN unzip master.zip
RUN chmod 777 /root/czifile-master/czifile/czi2tif.py

ENTRYPOINT [ "/root/czifile-master/czifile/czi2tif.py" ]