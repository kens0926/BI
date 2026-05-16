#!/usr/bin/env sh
set -eu

if [ -z "${PRJ1_SECRET_KEY:-}" ]; then
  echo "PRJ1_SECRET_KEY is required for production startup." >&2
  exit 1
fi

export PRJ1_DB_PATH="${PRJ1_DB_PATH:-./icp_system.db}"
export PRJ1_HOST="${PRJ1_HOST:-0.0.0.0}"
export PRJ1_PORT="${PRJ1_PORT:-5000}"

exec waitress-serve --host="$PRJ1_HOST" --port="$PRJ1_PORT" wsgi:application
