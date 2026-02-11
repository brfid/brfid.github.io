# ITS disk image builder — runs on x86_64 (Mac M2 via Rosetta or native x86)
# Produces: ITS RP06 disk image + KLH10 config, ready to copy to Pi
FROM --platform=linux/amd64 debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    autoconf \
    automake \
    expect \
    libpcap-dev \
    libtool \
    make \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Clone the ITS project (Lars Brinkhoff's canonical repo)
RUN git clone --depth=1 https://github.com/PDP-10/its.git

WORKDIR /build/its

# Build ITS using the project's own build system
# This compiles KLH10, assembles ITS, and creates a bootable disk image
# The EMULATOR=klh10 MACHINE=KS target produces an RP06 image
RUN make EMULATOR=klh10 MACHINE=KS

# The build produces artifacts in out/
# Key files:
#   out/klh10/  — KLH10 binary + config
#   out/klh10/rp0.dsk — the RP06 disk image with ITS installed

# Stage 2: collect artifacts into /artifacts for easy extraction
RUN mkdir -p /artifacts && \
    cp -r out/klh10/* /artifacts/ 2>/dev/null || true && \
    ls -la /artifacts/

# Default: just list what was built
CMD ["ls", "-la", "/artifacts"]
