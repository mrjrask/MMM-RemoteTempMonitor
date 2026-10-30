#!/usr/bin/env bash
# Update installed services using checkout sources and transactional rollback.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/install-full.sh" --update "$@"
