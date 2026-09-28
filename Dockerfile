FROM debian:stable-slim AS build

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3 \
    pipx \
    rrdtool \
    python3-rrdtool \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/ham /opt/ham/scripts /opt/ham/data
WORKDIR /opt/ham
VOLUME ["/opt/ham/scripts", "/opt/ham/data"]

EXPOSE 80

ENTRYPOINT ["ham", "-vv", "--scripts", "/opt/ham/scripts", "--http-host", "0.0.0.0", "--http-port", "80"]


FROM build AS dev

RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=ham/,target=ham/ \
    pipx install --global \
    --system-site-packages \
    .


FROM build

ARG HAM_TAG
RUN pipx install --global \
    --system-site-packages \
    git+https://github.com/ivofrolov/ham.git@$HAM_TAG
