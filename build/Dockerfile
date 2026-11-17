FROM certbot/certbot:latest

WORKDIR /scripts
COPY ./scripts/cpanel_api.py scripts/auth.sh scripts/cleanup.sh scripts/deploy.sh scripts/entrypoint.sh /scripts/
RUN chmod +x /scripts/auth.sh /scripts/cleanup.sh /scripts/deploy.sh /scripts/entrypoint.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
