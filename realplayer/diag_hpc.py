"""Quick check of the headless Chromium on the cluster: version, H.264/AAC support in Media Source Extensions,
and what one dash.js page does for 20 s (console messages, page errors, failed requests, requested URLs).

    PLAYWRIGHT_BROWSERS_PATH=$ROOT/.pw-browsers .venv/bin/python realplayer/diag_hpc.py
"""
import asyncio
import os
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from realplayer import testbed as tb  # noqa: E402

CODECS = ['video/mp4; codecs="avc1.42c01e"', 'video/mp4; codecs="avc1.64001f"', 'audio/mp4; codecs="mp4a.40.2"',
          'video/webm; codecs="vp9"']


async def main():
    from playwright.async_api import async_playwright
    bn = tb.Bottleneck(8e6)
    srv = tb.Server(bn, None)
    os.makedirs(os.path.join(tb.WWW, "pages"), exist_ok=True)
    with open(os.path.join(tb.WWW, "pages", "p0.html"), "w") as f:
        f.write(tb.PAGE.replace("{P}", "0"))
    server = await asyncio.start_server(srv.handle, "127.0.0.1", 9798)
    sched = asyncio.create_task(bn.run())
    bn.x = {"video": 0.5, "bulk": 0.5}
    async with async_playwright() as pw:
        print("chromium executable:", pw.chromium.executable_path)
        br = await pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required", "--disable-gpu",
                                            "--mute-audio", "--disable-dev-shm-usage", "--no-sandbox"])
        print("chromium version:", br.version)
        pg = await br.new_page()
        pg.on("console", lambda m: print("console:", m.type, m.text[:300]))
        pg.on("pageerror", lambda e: print("page error:", str(e)[:300]))
        pg.on("requestfailed", lambda r: print("request failed:", r.url, r.failure))
        pg.on("crash", lambda p: print("PAGE CRASHED"))
        urls = []
        pg.on("request", lambda r: urls.append(r.url))
        srv.t0 = time.monotonic()
        await pg.goto("http://127.0.0.1:9798/pages/p0.html")
        for c in CODECS:
            ok = await pg.evaluate(f"MediaSource.isTypeSupported('{c}')")
            print(f"MSE supports {c}: {ok}")
        await asyncio.sleep(20)
        print("requests:", len(urls))
        for u in urls[:12]:
            print("  ", u)
        await br.close()
    sched.cancel()
    server.close()


if __name__ == "__main__":
    asyncio.run(main())
