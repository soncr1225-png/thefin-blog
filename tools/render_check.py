"""Render the blog pages at the target mobile width and fail on visible breakage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


PAGES = (
    ("root", ""),
    ("2024-68165", "2024-68165/"),
    ("2025-51955", "2025-51955/"),
    ("2026-3414", "2026-3414/"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765/")
    parser.add_argument("--screenshot-dir", type=Path, default=Path(".render-check"))
    args = parser.parse_args()
    args.screenshot_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    results: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        for name, relative_url in PAGES:
            response = page.goto(args.base_url + relative_url, wait_until="networkidle")
            page.wait_for_timeout(150)
            status = response.status if response else None
            metrics = page.evaluate(
                """
                () => {
                  const width = document.documentElement.clientWidth;
                  const offenders = [...document.querySelectorAll('body *')]
                    .map((element) => {
                      const rect = element.getBoundingClientRect();
                      return {
                        tag: element.tagName.toLowerCase(),
                        cls: String(element.className || '').slice(0, 80),
                        left: Math.round(rect.left * 10) / 10,
                        right: Math.round(rect.right * 10) / 10,
                      };
                    })
                    .filter((item) => item.left < -0.5 || item.right > width + 0.5)
                    .slice(0, 10);
                  const brokenImages = [...document.images]
                    .filter((img) => !img.complete || img.naturalWidth === 0)
                    .map((img) => img.getAttribute('src'));
                  return {
                    clientWidth: width,
                    scrollWidth: document.documentElement.scrollWidth,
                    scrollHeight: document.documentElement.scrollHeight,
                    offenders,
                    brokenImages,
                  };
                }
                """
            )
            page.screenshot(path=args.screenshot_dir / f"{name}-full.png", full_page=True)
            positions = {
                "top": 0,
                "middle": max(0, (int(metrics["scrollHeight"]) - 844) // 2),
                "bottom": max(0, int(metrics["scrollHeight"]) - 844),
            }
            for label, position in positions.items():
                page.evaluate("position => window.scrollTo(0, position)", position)
                page.wait_for_timeout(50)
                page.screenshot(path=args.screenshot_dir / f"{name}-{label}.png")

            result = {"name": name, "status": status, **metrics}
            results.append(result)
            if status != 200:
                failures.append(f"{name}: HTTP {status}")
            if metrics["scrollWidth"] > metrics["clientWidth"] or metrics["offenders"]:
                failures.append(f"{name}: horizontal overflow")
            if metrics["brokenImages"]:
                failures.append(f"{name}: broken images {metrics['brokenImages']}")
        browser.close()

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print(f"render OK: {len(results)}페이지, 390px 넘침 0건, 깨진 이미지 0건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
