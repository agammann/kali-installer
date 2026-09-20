#!/usr/bin/env bash
set -euo pipefail

tag=installer-2026-09-20
output="$PWD/kali-installer-download"
base_url=
offline=0
iso=kali-linux-rolling-installer-amd64.iso
while [ "$#" -gt 0 ]; do
  case "$1" in
    --tag|--output|--base-url)
      [ "$#" -ge 2 ] || { echo "Missing value for $1" >&2; exit 1; }
      case "$1" in
        --tag) tag=$2 ;;
        --output) output=$2 ;;
        --base-url) base_url=$2 ;;
      esac
      shift 2 ;;
    --offline) offline=1; shift ;;
    *) echo "Usage: $0 [--tag TAG] [--output DIR] [--offline] [--base-url URL]" >&2; exit 1 ;;
  esac
done
[[ "$tag" =~ ^[A-Za-z0-9_-][A-Za-z0-9._-]*$ ]] || { echo "Invalid release tag" >&2; exit 1; }
base_url=${base_url:-"https://github.com/agammann/kali-installer/releases/download/$tag"}
case "$base_url" in
  https://*|http://127.0.0.1:*) ;;
  *) echo "Use an HTTPS release URL (or a localhost URL for testing)" >&2; exit 1 ;;
esac

if command -v sha256sum >/dev/null 2>&1; then
  hash_file() { sha256sum "$1" | cut -d ' ' -f 1; }
elif command -v shasum >/dev/null 2>&1; then
  hash_file() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
else
  echo "Install sha256sum or shasum first" >&2; exit 1
fi
download() {
  curl --fail --location --silent --show-error --retry 3 --connect-timeout 30 \
    --output "$2" "${base_url%/}/$1"
}
mkdir -p -- "$output"
cd -- "$output"
manifest_tmp=
part_tmp=
iso_tmp=
cleanup() {
  [ -z "$manifest_tmp" ] || rm -f -- "$manifest_tmp"
  [ -z "$part_tmp" ] || rm -f -- "$part_tmp"
  [ -z "$iso_tmp" ] || rm -f -- "$iso_tmp"
}
trap cleanup EXIT
manifest=SHA256SUMS
if [ "$offline" -eq 0 ]; then
  manifest_tmp=$(mktemp .manifest.XXXXXX)
  download SHA256SUMS "$manifest_tmp"
  manifest=$manifest_tmp
fi

part_names=()
part_hashes=()
iso_hash=
line=0
while read -r digest name extra || [ -n "${digest:-}" ]; do
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] && [ -z "$extra" ] || { echo "Invalid checksum manifest" >&2; exit 1; }
  if [ "$line" -eq 0 ]; then
    [ "$name" = "$iso" ] || { echo "Manifest must start with the ISO checksum" >&2; exit 1; }
    iso_hash=$digest
  else
    [ "$line" -le 999 ] || { echo "Too many parts" >&2; exit 1; }
    expected=$(printf '%s.part%03d' "$iso" "$line")
    [ "$name" = "$expected" ] || { echo "Invalid or out-of-order part name" >&2; exit 1; }
    part_names+=("$name")
    part_hashes+=("$digest")
  fi
  line=$((line + 1))
done < "$manifest"
[ "$line" -ge 2 ] || { echo "Manifest has no parts" >&2; exit 1; }
if [ -n "$manifest_tmp" ]; then
  mv -f -- "$manifest_tmp" SHA256SUMS
  manifest_tmp=
fi
if [ -e "$iso" ]; then
  [ "$(hash_file "$iso")" = "$iso_hash" ] || { echo "Existing ISO has a different checksum; use an empty output directory" >&2; exit 1; }
  echo "Already verified: $PWD/$iso"
  exit 0
fi

for ((i=0; i<${#part_names[@]}; i++)); do
  name=${part_names[$i]}
  digest=${part_hashes[$i]}
  if [ -f "$name" ] && [ "$(hash_file "$name")" = "$digest" ]; then
    echo "Verified cached part: $name"
    continue
  fi
  [ "$offline" -eq 0 ] || { echo "Missing or corrupt part: $name" >&2; exit 1; }
  echo "Downloading $name"
  part_tmp=$(mktemp .part.XXXXXX)
  download "$name" "$part_tmp"
  [ "$(hash_file "$part_tmp")" = "$digest" ] || { echo "Checksum mismatch: $name" >&2; exit 1; }
  mv -f -- "$part_tmp" "$name"
  part_tmp=
done
echo "Joining verified parts..."
iso_tmp=$(mktemp .iso.XXXXXX)
cat "${part_names[@]}" > "$iso_tmp"
[ "$(hash_file "$iso_tmp")" = "$iso_hash" ] || { echo "Reconstructed ISO checksum mismatch" >&2; exit 1; }
mv -- "$iso_tmp" "$iso"
iso_tmp=
echo "Verified ISO ready: $PWD/$iso"
