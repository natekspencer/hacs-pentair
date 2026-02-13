#!/usr/bin/env bash
set -euo pipefail

YEAR=$(date +"%Y")

if sed --version >/dev/null 2>&1; then
  # GNU sed
  sed -i -E "s/(Copyright( \(c\)| ©)? [0-9]{4})(–[0-9]{4})?/\1–$YEAR/" LICENSE
else
  # BSD sed
  sed -i '' -E "s/(Copyright( \(c\)| ©)? [0-9]{4})(–[0-9]{4})?/\1–$YEAR/" LICENSE
fi
