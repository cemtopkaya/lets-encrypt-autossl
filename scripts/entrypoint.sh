#!/bin/sh
set -eu

if [ "${1:-}" = "daemon" ]; then
  trap 'exit 0' TERM INT
  while :; do
    certbot renew \
      --manual-auth-hook /scripts/auth.sh \
      --manual-cleanup-hook /scripts/cleanup.sh \
      --deploy-hook /scripts/deploy.sh \
      --non-interactive
    sleep 12h & wait $!
  done
fi

exec certbot "$@"
