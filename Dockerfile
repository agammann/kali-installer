FROM kalilinux/kali-rolling@sha256:30399bd65187e06525008dd13eecc2b3439d26a82b2c6b0ba32dee72bd843117

RUN apt-get update \
    && apt-get install -y ca-certificates git simple-cdd debian-cd curl xorriso cpio mtools dosfstools isolinux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
