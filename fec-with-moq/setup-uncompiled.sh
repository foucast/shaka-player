#!/usr/bin/env bash
# Prepare Shaka's uncompiled mode for the MSF smoke test without Java or a full `npm ci`:
# the Closure library and closure-make-deps at the versions package.json pins, then
# dist/locales.js and dist/deps.js (what build/gendeps.py produces).
#
#   fec-with-moq/setup-uncompiled.sh        # needs node + npm (any current LTS), python3, curl
set -euo pipefail
cd "$(dirname "$0")/.."

command -v node >/dev/null || { echo "node is required (any current LTS)" >&2; exit 1; }

# closure-make-deps (package.json: "google-closure-deps": "^20230802.0.0")
npm install --no-save --no-package-lock --ignore-scripts --silent \
    --prefix fec-with-moq/.tools google-closure-deps@20230802.0.0

# Closure library (package.json: "google-closure-library": "github:joeyparrish/closure-library#74db0395")
if [ ! -f node_modules/google-closure-library/closure/goog/base.js ]; then
  mkdir -p node_modules/google-closure-library
  curl -fsSL https://codeload.github.com/joeyparrish/closure-library/tar.gz/74db0395 \
    | tar xz --strip-components=1 -C node_modules/google-closure-library
fi

mkdir -p dist
(cd build && python3 -c 'import compiler, sys; sys.exit(0 if compiler.GenerateLocalizations(None).generate() else 1)')
fec-with-moq/.tools/node_modules/.bin/closure-make-deps \
    -r demo lib ui third_party -f dist/locales.js \
    --closure-path node_modules/google-closure-library/closure/goog > dist/deps.js
[ -s dist/deps.js ] || { echo "closure-make-deps produced nothing" >&2; exit 1; }

echo "ready. Serve the repo root, e.g.  python3 -m http.server 8080 --bind 127.0.0.1"
echo "then open  http://localhost:8080/fec-with-moq/smoke.html?url=<relay>&ns=<a/b>&ver=draft-18"
