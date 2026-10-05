"""
Turnstile environment isolation test.
Run on your Mac with real Chrome, real GPU, residential IP.
If Turnstile renders here but not on seedlo, the server environment is the problem.
"""
import asyncio, sys
from patchright.async_api import async_playwright


TARGET_URL = "https://vimm.net/vault/17307"

async def main():
    pw = await async_playwright().start()

    browser = await pw.chromium.launch(
        channel="chrome",
        headless=False,
    )

    page = await browser.new_page(viewport={"width": 1920, "height": 1080})

    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))
    page.on("pageerror", lambda err: console_msgs.append(f"[PAGE_ERR] {err.message}"))

    print(f"Navigating to {TARGET_URL} ...")
    await page.goto(TARGET_URL, timeout=60000, wait_until="domcontentloaded")

    # Browser fingerprint snapshot
    fp = await page.evaluate("""
        () => ({
            webdriver: navigator.webdriver,
            platform: navigator.platform,
            hardwareConcurrency: navigator.hardwareConcurrency,
            deviceMemory: navigator.deviceMemory,
            plugins_len: navigator.plugins.length,
            languages: navigator.languages,
            vendor: navigator.vendor,
        })
    """)
    print("\n--- Fingerprint ---")
    for k, v in fp.items():
        print(f"  {k}: {v}")

    # Monitor Turnstile widget for up to 60s
    print("\n--- Monitoring Turnstile ---")
    rendered_iframe = False
    had_token = False

    for i in range(30):
        await asyncio.sleep(2)
        inner_len = await page.evaluate(
            "() => document.querySelector('.cf-turnstile')?.innerHTML?.length || 0"
        )
        iframe_count = await page.evaluate(
            "() => document.querySelectorAll('iframe').length"
        )
        token = await page.evaluate(
            "() => document.querySelector('[name=cf-turnstile-response]')?.value || ''"
        )

        if iframe_count > 0:
            rendered_iframe = True
        if token:
            had_token = True

        status = ""
        if rendered_iframe:
            status += " IFRAME"
        if token:
            status += f" TOKEN={token[:30]}..."

        print(f"  {i*2:>3}s: inner={inner_len}B  iframes={iframe_count}  token={'yes' if token else 'no'}{status}")

        if token or (inner_len > 200):
            break

    print("\n--- Console ---")
    for m in console_msgs:
        print(f"  {m}")

    print("\n--- Verdict ---")
    if had_token:
        print("PASS: Turnstile solved automatically — the tool works, the server environment is the problem.")
    elif rendered_iframe:
        print("PARTIAL: Turnstile rendered a widget (iframe) but didn't auto-solve. Manual click may be needed.")
    elif inner_len > 106:
        print("CHANGE: Widget innerHTML grew beyond placeholder — Turnstile is doing something. Investigate.")
    else:
        print("FAIL: Placeholder stayed static at 106B, no iframe, no token. Even on real hardware it fails.")

    await browser.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())