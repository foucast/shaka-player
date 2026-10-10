# fec-with-moq branch

This branch of Shaka Player is the base for a player that receives forward error correction (FEC)
repair tracks alongside media over MoQ. **It contains no FEC code yet.** So far it adds only a way to
run Shaka's MSF (MoQ) support uncompiled against a live MoQ relay, and a headless smoke test.

- Base: `shaka-project/shaka-player` `main` at `14566579` (Oct 9, 2026).
- Added: `FEC-WITH-MOQ.md`, `fec-with-moq/` (uncompiled and compiled smoke pages, setup script,
  smoke-test driver). Nothing under
  `lib/` is changed.

## Run Shaka's MSF player uncompiled against a relay

MSF is only in Shaka's `experimental` build (`build/all.py`), and no prebuilt bundle of `main` is
published. Uncompiled mode needs neither Java nor a full `npm ci`:

```sh
fec-with-moq/setup-uncompiled.sh          # node + npm, python3, curl; ~10 s
python3 -m http.server 8080 --bind 127.0.0.1
# then open:
# http://localhost:8080/fec-with-moq/smoke.html?url=<relay WebTransport URL>&ns=<ns/fields>&ver=draft-18
```

`setup-uncompiled.sh` fetches the Closure library and `closure-make-deps` at the versions
`package.json` pins, then writes `dist/locales.js` and `dist/deps.js`. The page loads Closure's
`base.js`, `dist/deps.js` and `shaka-player.uncompiled.js`, then calls
`player.load(url, null, 'application/msf')` with
`manifest.msf = {namespaces: ns.split('/'), version: ver}`. A 404 for Closure's own `goog/deps.js`
is expected and harmless.

Notes for MSF (from reading `lib/msf/` at the base commit):
- `namespaces` must be set: the parser subscribes to the `catalog` track there directly.
- `version: 'draft-18'` pins the dialect. `main` offers drafts 18, 20, 21 and 22; the 5.2.x releases
  offer draft 16 with draft-14 fallback instead.
- The relay needs a publicly trusted certificate, or use `manifest.msf.fingerprintUri` (hex SHA-256)
  for `serverCertificateHashes`.
- Packaging: LOC and CMAF work; a LOC video track needs `framerate` in the catalog.

## Headless smoke test (no FEC)

```sh
pip install playwright && playwright install --with-deps chromium firefox
# serve the repo root as above, then:
python fec-with-moq/run_smoke.py <relay WebTransport URL> <ns/fields> --secs 60 --browser chromium
python fec-with-moq/run_smoke.py <relay WebTransport URL> <ns/fields> --secs 60 --browser firefox
```

It prints decoded/dropped frames and play/buffering time every 5 s, then the page log and the console's
warnings and errors, and saves `fec-with-moq/frame-<browser>.png`.

A publisher that works with it: aiomoqt's `pub_media` (MSF catalog + LOC), e.g.
`python -m aiomoqt.tools.pub_media -N smoke/one --mp4 clip.mp4 --loop --no-audio --pub-ns --draft 18
moqt://<relay>:<port>`. Use AV1 or H.264 video; Playwright's Chromium may lack H.264/AAC, so AV1 is
the safe choice there. Use a fresh namespace per run.

**Result (Oct 10, 2026)**, through a moqx relay (`ghcr.io/openmoq/moqx:fdba9db`, WebTransport,
draft 18), AV1 640×360 at 30 fps, LOC on subgroup streams, 60 s each, no FEC:

| browser | decoded frames | dropped | buffering |
|---|---|---|---|
| Chromium 153.0.8010.12 (Playwright, headless) | 1,748 | 6 | 1.08 s |
| Firefox 155.0 (Playwright, headless) | 1,674 | 0 | 0.86 s |

## Compiled build

The normal build works on this branch and includes MSF in the `experimental` bundles:

```sh
npm ci                     # ~1 min
python3 build/all.py       # needs Java (21 works); ~16 min on 2 vCPU
```

Oct 10, 2026, on a 2 vCPU / 4 GB Linux VM with Node 24.21 and Temurin JRE 21: `npm ci` 62 s,
`build/all.py` 938 s, exit 0. It produces `dist/shaka-player.experimental.js` (1.24 MB) and its
`-es2021` and `.debug` variants, all containing the MSF parser.

`fec-with-moq/smoke-compiled.html` is the same page loading `../dist/shaka-player.experimental.js`
instead of the uncompiled sources. With it, headless Chromium 153 played the same broadcast for 45 s
(1,297 frames decoded, 1 dropped; no FEC).
