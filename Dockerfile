# Start with a base image with Java pre-installed
FROM openjdk:11-jdk-slim-buster

# Install system dependencies
RUN apt-get update && \
    apt-get install -y wget && \
    apt-get install -y libjpeg-dev && \
    apt-get install -y zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Download and install jpegxr native library
# RUN wget https://github.com/team-charite/jpegxr/releases/download/v1.2.2/libCharLS-2.2.0-Linux-x86_64.so -P /usr/local/lib/
# ENV LD_LIBRARY_PATH=/usr/local/lib

# Download and install bftools package
RUN wget https://downloads.openmicroscopy.org/bio-formats/6.6.1/artifacts/bftools.zip && \
    unzip bftools.zip -d /usr/local/bftools && \
    rm bftools.zip

# Set an environment variable to use the Bio-Formats JPEG XR plugin
ENV BF_MAX_MEM="8G"

# Set the bftools command to the PATH
ENV PATH="/usr/local/bftools/bin:${PATH}"

# Set an entry point for the container
ENTRYPOINT [ "/usr/local/bftools/bftools/bfconvert" ]