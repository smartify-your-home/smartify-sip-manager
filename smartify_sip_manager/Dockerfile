# HA base contains s6-overlay and with-contenv (Supervisor token handling).
ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.12-alpine3.23
FROM ${BUILD_FROM}
RUN python3 -c "import yaml" 2>/dev/null || python3 -m pip install --no-cache-dir "PyYAML==6.0.2"
WORKDIR /app
COPY config.yaml app.py anlage.py generator.py rtsp.py verbindungen.py inbound_routes.py index.html app.js anlage-ui.js verbindungen-ui.js pjsip-builder.js app.css ./
COPY run.sh /run.sh
RUN chmod 0755 /run.sh
CMD ["/run.sh"]
