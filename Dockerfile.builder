FROM ghcr.io/quarto-dev/quarto-full:1.11.4@sha256:4fe656d4c69ff8c5a4ab4757741d34f7e8fc6ebbbb2b0d53034c191bdc155b1e

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip cargo rustc graphviz poppler-utils fonts-noto-cjk fonts-noto-cjk-extra libreoffice \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --break-system-packages --no-cache-dir uv==0.10.0
WORKDIR /workspace
CMD ["make","validate-canonical"]
