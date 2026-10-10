"""Headless smoke test: open fec-with-moq/smoke.html in Chromium or Firefox (Playwright) and report
what Shaka played. No FEC. Serve the repo root on localhost:8080 first.

    python run_smoke.py RELAY_URL NAMESPACE [--secs 60] [--draft draft-18] [--browser chromium|firefox]

Prints a sample every 5 s (decoded/dropped frames, play and buffering time), then the page log and
the browser console's warnings and errors, and saves a screenshot next to this file.
"""
import argparse, json, os, time
from playwright.sync_api import sync_playwright

p = argparse.ArgumentParser()
p.add_argument("url")
p.add_argument("ns", help="namespace fields joined by '/', e.g. live/channel1")
p.add_argument("--secs", type=int, default=60)
p.add_argument("--draft", default="draft-18")
p.add_argument("--browser", choices=("chromium", "firefox"), default="chromium")
p.add_argument("--page", default="http://localhost:8080/fec-with-moq/smoke.html")
a = p.parse_args()

SAMPLE = """() => {
    const v = document.querySelector('video');
    const q = v.getVideoPlaybackQuality ? v.getVideoPlaybackQuality() : {};
    const st = window.player ? window.player.getStats() : {};
    return {t: v.currentTime, ready: v.readyState, w: v.videoWidth, h: v.videoHeight,
            totalFrames: q.totalVideoFrames, droppedFrames: q.droppedVideoFrames,
            decodedFrames: st.decodedFrames, playTime: st.playTime,
            bufferingTime: st.bufferingTime};
}"""

with sync_playwright() as pw:
    if a.browser == "chromium":
        b = pw.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    else:
        b = pw.firefox.launch(headless=True, firefox_user_prefs={
            "media.autoplay.default": 0, "network.webtransport.enabled": True,
            "network.webtransport.datagrams.enabled": True})
    print("browser", a.browser, b.version, flush=True)
    pg = b.new_page()
    console = []
    pg.on("console", lambda m: console.append(f"{m.type}: {m.text}"))
    pg.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
    pg.goto(f"{a.page}?url={a.url}&ns={a.ns}&ver={a.draft}")
    t0 = time.time()
    while time.time() - t0 < a.secs:
        time.sleep(5)
        s = pg.evaluate(SAMPLE)
        s["elapsed"] = round(time.time() - t0, 1)
        print("SAMPLE", json.dumps(s), flush=True)
    print("PAGE LOG")
    for line in pg.evaluate("() => window.smokeLog || []"):
        print("  ", line)
    print("CONSOLE (warnings and errors)")
    for c in console:
        if c.startswith(("error", "warning", "pageerror")):
            print("  ", c[:400])
    pg.screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), f"frame-{a.browser}.png"))
    b.close()
