FROM ghcr.io/quarto-dev/quarto-full:1.11.9@sha256:7a08949fe0b6759a63eec7e7565284a78f4af6f0f98506744c7baace14de30b2

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
