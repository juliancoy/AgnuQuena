FROM ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        autoconf \
        build-essential \
        ca-certificates \
        cmake \
        eglexternalplatform-dev \
        extra-cmake-modules \
        file \
        gettext \
        git \
        libbz2-dev \
        libcurl4-openssl-dev \
        libdbus-1-dev \
        libfuse2 \
        libgl1-mesa-dev \
        libglew-dev \
        libgstreamerd-3-dev \
        libgtk-3-dev \
        libmspack-dev \
        libosmesa6-dev \
        libsecret-1-dev \
        libssl-dev \
        libtool \
        libudev-dev \
        libunwind-dev \
        libwebkit2gtk-4.1-dev \
        libx264-dev \
        libxkbcommon-dev \
        nasm \
        ninja-build \
        sudo \
        texinfo \
        wget \
        yasm \
    && rm -rf /var/lib/apt/lists/*
