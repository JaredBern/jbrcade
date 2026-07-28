FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Buildozer dependencies
RUN apt-get update && apt-get install -y \
    git \
    zip \
    unzip \
    openjdk-17-jdk \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    wget \
    curl \
    python3-pip \
    python3-setuptools \
    python3-dev \
    && apt-get clean

# Install Buildozer and Cython
RUN pip3 install --upgrade pip
RUN pip3 install buildozer cython

# Create a non-root user (Buildozer requirement)
RUN useradd -m -d /home/useruser useruser
USER useruser
WORKDIR /home/useruser/project

# Pre-declare Android SDK path inside container
ENV PATH="/home/useruser/.local/bin:${PATH}"

CMD ["/bin/bash"]