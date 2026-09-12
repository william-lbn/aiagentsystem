FROM ghcr.io/quarto-dev/quarto-full:1.11.1@sha256:fb4b3d369c7399f97dbfcc90a4edfdd09fc581f4cd654813ba84694248e65b13

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip cargo rustc graphviz poppler-utils fonts-noto-cjk fonts-noto-cjk-extra libreoffice \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --no-cache-dir uv==0.10.0 \
 && tlmgr install ctex fancyhdr fvextra needspace \
 && test -n "$(kpsewhich ctexbook.cls)" \
 && test -n "$(kpsewhich fancyhdr.sty)" \
 && test -n "$(kpsewhich fvextra.sty)" \
 && test -n "$(kpsewhich needspace.sty)"
WORKDIR /workspace
CMD ["make","validate-canonical"]
