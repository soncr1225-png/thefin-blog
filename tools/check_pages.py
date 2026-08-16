#!/usr/bin/env python3
"""Deterministic contract checks for the static employee-review blog pages."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = ("2024-68165", "2025-51955", "2026-3414")
FORBIDDEN_PUBLIC = (
    "자료에 보증금 액수가 적혀",
    "자료에 표기되지",
    "이 대본은 현장 방문을 했다는 전제로",
    "타당합니다",
    "삼겠습니다",
    "예상낙찰가",
    "입찰 상한선",
)


def check_case(case: str) -> list[str]:
    errors: list[str] = []
    folder = ROOT / case
    meta_path, html_path = folder / "_meta.txt", folder / "index.html"
    if not meta_path.is_file() or not html_path.is_file():
        return [f"{case}: _meta.txt 또는 index.html 없음"]
    meta = meta_path.read_text(encoding="utf-8").splitlines()
    html = html_path.read_text(encoding="utf-8")
    public = html.split('<hr class="cut">', 1)[0]
    if len(meta) != 3 or not all(line.strip() for line in meta):
        errors.append(f"{case}: _meta.txt는 빈 줄 없는 3줄이어야 함")
    required = (
        '<meta name="robots" content="noindex, nofollow">',
        "word-break:keep-all",
        "table-layout:fixed",
        "border-left:3px solid #555",
        '<hr class="cut">',
        'class="tag"',
        'class="w devnote"',
    )
    for token in required:
        if token not in html:
            errors.append(f"{case}: 필수 형식 없음 — {token}")
    for phrase in FORBIDDEN_PUBLIC:
        if phrase in public:
            errors.append(f"{case}: 공개 본문 금지 문구 — {phrase}")
    for src in re.findall(r'<img\s+[^>]*src="([^"]+)"', html):
        if src.startswith(("http://", "https://", "data:")):
            errors.append(f"{case}: 외부/인라인 이미지 금지 — {src}")
            continue
        if not (folder / src).is_file():
            errors.append(f"{case}: 깨진 이미지 경로 — {src}")
    cards = sorted((folder / "img").glob("카드*.png"))
    if len(cards) != 3:
        errors.append(f"{case}: 근거 있는 카드 3장이어야 함, 실제 {len(cards)}장")
    if case != "2024-68165":
        for forbidden_asset in ("썸네일.png", "photo01.jpg", "배치도.png", "구조도.png", "위치도.png", "푸터.jpg"):
            if (folder / "img" / forbidden_asset).exists():
                errors.append(f"{case}: A-33 뒤 우회 생성된 자산 — {forbidden_asset}")
    return errors


def main() -> int:
    errors: list[str] = []
    for case in CASES:
        errors.extend(check_case(case))
    root_html = (ROOT / "index.html").read_text(encoding="utf-8")
    for case in CASES:
        if f'href="{case}/"' not in root_html:
            errors.append(f"목록 링크 없음 — {case}")
    if errors:
        print("\n".join(errors))
        return 1
    image_count = sum(len(re.findall(r'<img\s', (ROOT / case / "index.html").read_text(encoding="utf-8"))) for case in CASES)
    print(f"page contract OK: 3건, 게시 이미지 참조 {image_count}개, 깨진 경로 0개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
