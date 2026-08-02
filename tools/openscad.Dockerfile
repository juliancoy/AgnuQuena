FROM ubuntu:24.04 AS build

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bison \
        build-essential \
        ca-certificates \
        cmake \
        flex \
        gettext \
        git \
        lib3mf-dev \
        libboost-program-options-dev \
        libboost-regex-dev \
        libboost-system-dev \
        libcairo2-dev \
        libcgal-dev \
        libdouble-conversion-dev \
        libeigen3-dev \
        libffi-dev \
        libfontconfig-dev \
        libfreetype-dev \
        libgl1-mesa-dev \
        libglew-dev \
        libglib2.0-dev \
        libgmp-dev \
        libharfbuzz-dev \
        libmimalloc-dev \
        libmpfr-dev \
        libopencsg-dev \
        libqscintilla2-qt6-dev \
        libqt6core5compat6-dev \
        libqt6opengl6-dev \
        libqt6svg6-dev \
        libtbb-dev \
        libxi-dev \
        libxml2-dev \
        libxmu-dev \
        libzip-dev \
        nettle-dev \
        ninja-build \
        pkg-config \
        qt6-base-dev \
        qt6-multimedia-dev \
        ragel \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /src

RUN cmake -S /src -B /build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DEXPERIMENTAL=ON \
        -DENABLE_TESTS=OFF \
        -DUSE_QT6=ON \
    && cmake --build /build -j"$(nproc)" \
    && cmake --install /build --prefix /opt/openscad

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        lib3mf1 \
        libboost-program-options1.83.0 \
        libboost-regex1.83.0 \
        libcairo2 \
        libdouble-conversion3 \
        libfontconfig1 \
        libfreetype6 \
        libgl1 \
        libglew2.2 \
        libglib2.0-0t64 \
        libgmp10 \
        libharfbuzz0b \
        libmpfr6 \
        libopencsg1 \
        libqscintilla2-qt6-15 \
        libqt6core5compat6 \
        libqt6gui6 \
        libqt6multimedia6 \
        libqt6network6 \
        libqt6opengl6 \
        libqt6printsupport6 \
        libqt6svg6 \
        libqt6widgets6 \
        libtbb12 \
        libxml2 \
        libzip4t64 \
        xauth \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglu1-mesa \
        libmimalloc2.0 \
        libqt6openglwidgets6t64 \
        libssl3t64 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /opt/openscad /opt/openscad

ENTRYPOINT ["xvfb-run", "-a", "/opt/openscad/bin/openscad"]
