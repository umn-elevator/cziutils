# czifile-new requires Python >= 3.12; imagecodecs wheels bundle the JPEG XR
# decoder, so no system image libraries are needed for this converter.
FROM python:3.12-slim-bookworm

# Pin upstream czifile by Git ref (release tag or branch) at build time.
ARG CZIFILE_REPO=https://github.com/cgohlke/czifile.git
ARG CZIFILE_REF=v2026.6.12

WORKDIR /root

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install the runtime dependencies first so this layer is cached across
# source changes.
COPY requirements.txt /root/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . /root

# Install upstream czifile from GitHub at the requested release/tag/branch.
# Dependencies are already satisfied by requirements.txt.
RUN git clone "${CZIFILE_REPO}" /tmp/czifile && \
    cd /tmp/czifile && \
    git checkout "${CZIFILE_REF}" && \
    pip install --no-deps . && \
    cd /root && \
    rm -rf /tmp/czifile

ENTRYPOINT [ "python3", "/root/czi2tif.py" ]