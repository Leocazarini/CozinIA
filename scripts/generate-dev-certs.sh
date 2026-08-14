#!/usr/bin/env bash
#
# Generates the certificate the app is served with on the LAN.
#
# The phone will only register a service worker — and therefore only install
# the app — over https it trusts. There is no public name to get a real
# certificate for on a home network, so this creates a small certificate
# authority of its own, installs nothing on this machine, and signs one
# certificate for the addresses the app is reached at.
#
# Run it once:
#
#   ./scripts/generate-dev-certs.sh
#
# Then install certs/rootCA.pem on the phone (Android: Settings > Security >
# Encryption & credentials > Install a certificate > CA certificate) and open
# the app at the https address it prints.
#
# On the VPS none of this is used: point TLS_CERT_FILE/TLS_KEY_FILE at the
# Let's Encrypt files instead. Nothing else changes.
set -euo pipefail

cd "$(dirname "$0")/.."
CERT_DIR="certs"
DAYS=825 # the longest a leaf certificate may live and still be accepted

mkdir -p "$CERT_DIR"

# Every address the app might be opened at. The LAN IP is the one that
# matters — a certificate is only valid for names it lists, and phones reach
# this machine by address, not by name.
LAN_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')"
if [[ -z "${LAN_IP}" ]]; then
  echo "Não consegui descobrir o IP desta máquina na rede. Informe-o à mão:" >&2
  echo "  LAN_IP=192.168.0.10 $0" >&2
  exit 1
fi

SANS="DNS:localhost,DNS:cozinia.local,IP:127.0.0.1,IP:${LAN_IP}"

if [[ ! -f "$CERT_DIR/rootCA.pem" ]]; then
  echo "→ Criando a autoridade certificadora local (certs/rootCA.pem)"
  openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
    -keyout "$CERT_DIR/rootCA-key.pem" \
    -out "$CERT_DIR/rootCA.pem" \
    -subj "/CN=CozinIA local CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
fi

echo "→ Emitindo o certificado do servidor para ${SANS}"
openssl req -newkey rsa:2048 -sha256 -nodes \
  -keyout "$CERT_DIR/cozinia-key.pem" \
  -out "$CERT_DIR/cozinia.csr" \
  -subj "/CN=cozinia.local" 2>/dev/null

openssl x509 -req -in "$CERT_DIR/cozinia.csr" \
  -CA "$CERT_DIR/rootCA.pem" -CAkey "$CERT_DIR/rootCA-key.pem" -CAcreateserial \
  -out "$CERT_DIR/cozinia.pem" -days "$DAYS" -sha256 \
  -extfile <(printf 'subjectAltName=%s\nextendedKeyUsage=serverAuth\n' "$SANS") 2>/dev/null

rm -f "$CERT_DIR/cozinia.csr" "$CERT_DIR/rootCA.srl"
chmod 600 "$CERT_DIR"/*-key.pem

cat <<EOF

Pronto.

  App:      https://${LAN_IP}
  CA:       certs/rootCA.pem  (instale no celular, uma vez)
  Validade: ${DAYS} dias

Se o IP desta máquina mudar, rode este script de novo — e reserve um IP fixo
no roteador, porque o endereço é a identidade do app instalado: mudou o IP,
o celular passa a ver outro app, sem as receitas guardadas para uso offline.
EOF
