#!/bin/bash
# Fetches code-maat.jar (churn.py's dependency) -- not committed to git,
# see .gitignore. Idempotent: skips if already present.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JAR="$DIR/tools/code-maat.jar"
if [ -f "$JAR" ]; then
  echo "code-maat.jar already present at $JAR"
  exit 0
fi
mkdir -p "$DIR/tools"
URL="https://github.com/adamtornhill/code-maat/releases/download/v1.0.4/code-maat-1.0.4-standalone.jar"
echo "Fetching code-maat.jar from $URL"
curl -sL -o "$JAR" "$URL"
file "$JAR" | grep -q "Java archive" && echo "OK: $JAR" || { echo "FAILED: not a valid jar"; rm -f "$JAR"; exit 1; }
