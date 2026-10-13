#!/usr/bin/env bash
# Check that the live site is up, served over HTTPS, and that its certificate
# is not about to expire. Exits non-zero if anything is wrong.
set -u

DOMAIN="elliottolson.com"
MIN_CERT_DAYS=14
failed=0

fail() {
  echo "FAIL: $1"
  failed=1
}

fetch() {
  curl --silent --show-error --max-time 20 --retry 3 --retry-delay 10 --retry-all-errors "$@"
}

# The homepage loads and contains the expected content
body=$(fetch "https://$DOMAIN/") || fail "https://$DOMAIN/ did not load"
if [[ "$body" == *"<title>Elliott Olson"* ]]; then
  echo "ok: homepage loads"
else
  fail "homepage is missing the expected title"
fi

# Plain HTTP and www both redirect to the secure address
for url in "http://$DOMAIN/" "https://www.$DOMAIN/"; do
  target=$(fetch --output /dev/null --write-out '%{redirect_url}' "$url")
  if [[ "$target" == "https://$DOMAIN/" ]]; then
    echo "ok: $url redirects to https://$DOMAIN/"
  else
    fail "$url redirects to '${target:-nothing}'"
  fi
done

# The certificate is valid for at least MIN_CERT_DAYS more days
cert=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null)
if echo "$cert" | openssl x509 -noout -checkend $((MIN_CERT_DAYS * 86400)) >/dev/null 2>&1; then
  echo "ok: certificate valid ($(echo "$cert" | openssl x509 -noout -enddate | cut -d= -f2))"
else
  fail "certificate is missing or expires within $MIN_CERT_DAYS days"
fi

exit $failed
