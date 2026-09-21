#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
DATA_DIR="$ROOT_DIR/data"
BACKUP_DIR="$ROOT_DIR/backups"
mkdir -p "$BACKUP_DIR"

case "${1:-}" in
  backup)
    ts=$(date +%Y%m%d_%H%M%S)
    tar -czf "$BACKUP_DIR/langchain_backup_${ts}.tar.gz" -C "$ROOT_DIR" data
    echo "backup saved to $BACKUP_DIR/langchain_backup_${ts}.tar.gz"
    ;;
  restore)
    file="$2"
    if [[ -z "$file" ]]; then
      echo "usage: $0 restore <backup-file>"
      exit 1
    fi
    tar -xzf "$file" -C "$ROOT_DIR"
    echo "restored $file"
    ;;
  *)
    echo "Usage: $0 {backup|restore <file>}"
    exit 1
    ;;
esac
