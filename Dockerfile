FROM debian:stable-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3 \
    pipx \
    rrdtool \
    python3-rrdtool \
    && rm -rf /var/lib/apt/lists/*

RUN pipx install --global --system-site-packages git+https://github.com/ivofrolov/ham.git
# in local development mode use this instead
# WORKDIR /tmp
# RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
#     --mount=type=bind,source=ham/,target=ham/ \
#     pipx install --global --system-site-packages .

RUN mkdir -p /opt/ham /opt/ham/scripts /opt/ham/data
WORKDIR /opt/ham
VOLUME ["/opt/ham/scripts", "/opt/ham/data"]

EXPOSE 80

ENTRYPOINT ["ham", "-vv", "--scripts", "/opt/ham/scripts", "--http-host", "0.0.0.0", "--http-port", "80"]
