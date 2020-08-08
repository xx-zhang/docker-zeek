#!/bin/bash

LLVM_VERSION=10

apt-get install -q -y --no-install-recommends gnupg2 curl ca-certificates
bash -c "curl -sSL https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -"
echo "deb http://apt.llvm.org/buster/ llvm-toolchain-buster-${LLVM_VERSION} main" >> /etc/apt/source
apt-get -y update


    apt-get install -q -y -t buster-backports --no-install-recommends \
        binutils \
        ccache \
        clang-${LLVM_VERSION} \
        file \
        flex \
        git \
        google-perftools \
        jq \
        libclang-${LLVM_VERSION}-dev \
        libfl-dev \
        libgoogle-perftools-dev \
        libkrb5-dev \
        libmaxminddb-dev \
        libpcap0.8-dev \
        libssl-dev \
        llvm-${LLVM_VERSION}-dev \
        locales-all \
        make \
        ninja-build \
        patch \
        python3 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        swig \
        zlib1g-dev && \
        pip3 install --no-cache-dir zkg btest pre-commit && \
  mkdir -p "${CMAKE_DIR}" && \
    curl -sSL "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-Linux-x86_64.tar.gz" | tar xzf - -C "${CMAKE_DIR}" --strip-components 1 && \
  cd "${SRC_BASE_DIR}" && \
    curl -sSL "https://ftp.gnu.org/gnu/bison/bison-${BISON_VERSION}.tar.gz" | tar xzf - -C "${SRC_BASE_DIR}" && \
    cd "./bison-${BISON_VERSION}" && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
  cd "${SRC_BASE_DIR}" && \
    curl -sSL "https://old.zeek.org/downloads/zeek-${ZEEK_VERSION}.tar.gz" | tar xzf - -C "${SRC_BASE_DIR}" && \
    cd "./zeek-${ZEEK_VERSION}" && \
    bash -c "for i in ${ZEEK_PATCH_DIR}/* ; do patch -p 1 -r - --no-backup-if-mismatch < \$i || true; done" && \
    ./configure --prefix="${ZEEK_DIR}" --generator=Ninja --ccache --enable-perftools && \
    cd build && \
    ninja && \
    ninja install && \
    zkg autoconfig && \
    bash /usr/local/bin/zeek_install_plugins.sh && \
    bash -c "find ${ZEEK_DIR}/lib -type d -name CMakeFiles -exec rm -rf '{}' \; 2>/dev/null || true" && \
    bash -c "file ${ZEEK_DIR}/{lib,bin}/* ${ZEEK_DIR}/lib/zeek/plugins/packages/*/lib/* ${ZEEK_DIR}/lib/zeek/plugins/*/lib/* ${SPICY_DIR}/{lib,bin}/* ${SPICY_DIR}/lib/spicy/Zeek_Spicy/lib/* | grep 'ELF 64-bit' | sed 's/:.*//' | xargs -l -r strip -v --strip-unneeded"

apt-get -q update && \
    apt-get install -q -y -t buster-backports --no-install-recommends \
      file \
      libatomic1 \
      libclang-cpp${LLVM_VERSION} \
      libclang1-${LLVM_VERSION} \
      libgoogle-perftools4 \
      libkrb5-3 \
      libmaxminddb0 \
      libpcap0.8 \
      libssl1.0 \
      libtcmalloc-minimal4 \
      libunwind8 \
      libzmq5 \
      llvm-${LLVM_VERSION} \
      procps \
      psmisc \
      python \
      python3 \
      python3-pip \
      python3-setuptools \
      python3-wheel \
      supervisor \
      vim-tiny && \
    pip3 install --no-cache-dir pyzmq && \
    apt-get -q -y --purge remove libssl-dev && \
      apt-get -q -y autoremove && \
      apt-get clean && \
      rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

git clone https://github.com/xx-zhang/docker-zeek \
  && cp -r docker-zeek/zeek/config/*.zeek /usr/local/zeek/share/zeek/site/ && \
  cp  docker-zeek/etc/networks.cfg ${ZEEK_DIR}/etc/networks.cfg && \
cp docker-zeek/etc/zeekctl.cfg ${ZEEK_DIR}/etc/zeekctl.cfg && \
cp docker-zeek/docker-entrypoint.sh /entrypoint.sh

ZEEKCFG_VERSION=0.0.5 && \
  wget -qO ${ZEEK_DIR}/bin/zeekcfg https://github.com/activecm/zeekcfg/releases/download/v${ZEEKCFG_VERSION}/zeekcfg_${ZEEKCFG_VERSION}_linux_amd64 \
 && chmod +x ${ZEEK_DIR}/bin/zeekcfg && \
  echo "*/5       *       *       *       *      ${ZEEK_DIR}/bin/zeekctl cron" >> /etc/crontab

#修改失去。

dpkg-reconfigure tzdata
ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

## 安装docekr
apt-get -y update && \
  apt-get install apt-transport-https ca-certificates curl gnupg2 software-properties-common -y && \

