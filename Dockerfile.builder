FROM ghcr.io/quarto-dev/quarto-full:1.11.5@sha256:3c0f92b4b7d02ec996a456452d242edc63416747639b4172fc04bb20c844dde3

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip cargo rustc graphviz poppler-utils fonts-noto-cjk fonts-noto-cjk-extra libreoffice \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --no-cache-dir uv==0.10.0 \
 && tlmgr update --self \
 && tlmgr install ctex fancyhdr fvextra needspace enumitem ragged2e caption \
 && test -n "$(kpsewhich ctexbook.cls)" \
 && test -n "$(kpsewhich fancyhdr.sty)" \
 && test -n "$(kpsewhich fvextra.sty)" \
 && test -n "$(kpsewhich needspace.sty)" \
 && test -n "$(kpsewhich enumitem.sty)" \
 && test -n "$(kpsewhich ragged2e.sty)" \
 && test -n "$(kpsewhich caption.sty)"
WORKDIR /workspace
CMD ["make","validate-canonical"]
