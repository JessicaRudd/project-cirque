#!/usr/bin/env bash
set -euo pipefail

SWIFT_VERSION="6.0.3"
INSTALL_ROOT="${SWIFT_INSTALL_ROOT:-/tmp/swift}"
SWIFT_BIN="${INSTALL_ROOT}/usr/bin/swift"
MODULEMAP_PATH="${INSTALL_ROOT}/usr/lib/swift/linux/module.modulemap"

write_csqlite_modulemap() {
  local target_map="$1"
  local arch_triplet
  arch_triplet="$(uname -m)-linux-gnu"
  local header_path="/usr/include/sqlite3.h"
  if [[ ! -f "${header_path}" && -f "/usr/include/${arch_triplet}/sqlite3.h" ]]; then
    header_path="/usr/include/${arch_triplet}/sqlite3.h"
  fi
  if [[ ! -f "${header_path}" ]]; then
    echo "error: sqlite3.h not found under /usr/include" >&2
    exit 1
  fi

  if ! grep -q "module CSQLite" "${target_map}" 2>/dev/null; then
    cat >> "${target_map}" <<EOF

module CSQLite [system] {
  header "${header_path}"
  link "sqlite3"
  export *
}
EOF
  fi
}

if [[ -x "${SWIFT_BIN}" ]]; then
  write_csqlite_modulemap "${MODULEMAP_PATH}"
  echo "Swift toolchain ready at ${SWIFT_BIN}"
  exit 0
fi

ARCH="$(uname -m)"
case "${ARCH}" in
  x86_64)
    PLATFORM_DIR="ubuntu2204"
    PLATFORM_TAG="ubuntu22.04"
    ;;
  aarch64|arm64)
    PLATFORM_DIR="ubuntu2204-aarch64"
    PLATFORM_TAG="ubuntu22.04-aarch64"
    ;;
  *)
    echo "error: unsupported architecture '${ARCH}'" >&2
    exit 1
    ;;
esac

RELEASE_TAG="swift-${SWIFT_VERSION}-RELEASE"
TARBALL="${RELEASE_TAG}-${PLATFORM_TAG}.tar.gz"
DOWNLOAD_URL="https://download.swift.org/swift-${SWIFT_VERSION}-release/${PLATFORM_DIR}/${RELEASE_TAG}/${TARBALL}"
TMP_ARCHIVE="$(mktemp "/tmp/${TARBALL}.XXXXXX")"
trap 'rm -f "${TMP_ARCHIVE}"' EXIT

echo "Downloading ${DOWNLOAD_URL} ..."
# Force HTTP/1.1 to avoid intermittent HTTP/2 stream framing resets on large toolchain tarballs.
curl --http1.1 -fSL --retry 3 --retry-delay 2 -o "${TMP_ARCHIVE}" "${DOWNLOAD_URL}"

mkdir -p "${INSTALL_ROOT}"
tar -xzf "${TMP_ARCHIVE}" --strip-components=1 -C "${INSTALL_ROOT}"
write_csqlite_modulemap "${MODULEMAP_PATH}"

echo "Installed $("${SWIFT_BIN}" --version | head -n 1) at ${INSTALL_ROOT}"
