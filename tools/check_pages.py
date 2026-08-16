#!/usr/bin/env python3
"""Deterministic contract checks for the static employee-review blog pages."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def discover_cases() -> list[str]:
    """게시 사건은 손으로 적지 않는다 — `_meta.txt`가 있는 폴더가 곧 게시물이다.

    ★2026-08-16: 여기 사건번호 3개가 손으로 박혀 있었다. 새 게시물이 검사 대상 밖으로
      조용히 빠지는 구조였다(볼트 관통 원리 1 — 손 목록은 매번 실제의 일부였다).
    """
    return sorted(p.parent.name for p in ROOT.glob("*/_meta.txt") if p.is_file())


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
    # ★2026-08-16 제거된 두 규칙 — 둘 다 정상 산출을 오류로 판정하고 있었다.
    #   (1) "카드는 정확히 3장" — 카드는 근거가 있을 때만 만든다. 배당·취득세 근거가 있는
    #       사건은 5장이 맞고, 개수를 고정하면 근거 있는 카드를 못 싣는다.
    #   (2) "썸네일·도면·사진·푸터가 있으면 A-33 우회" — A-33(신규 킷 CLI 사망)이 수리되어
    #       정본 경로로 자산이 나온다. 그 규칙은 이제 **제대로 만든 것을 차단**한다.
    #   개수·종류를 여기서 세지 않는다. 자산 계약 정본은 auction-report 의
    #   `blog_publish_contract` 이고, 같은 규칙을 두 곳에 구현하지 않는다.
    #   이 검사기가 지키는 것은 **게시 페이지의 형식과 참조 무결성**뿐이다.
    return errors


def main() -> int:
    cases = discover_cases()
    if not cases:
        # 표본 0건은 통과가 아니다 — 검사기가 아무것도 안 본 것이다.
        print("게시물을 하나도 발견하지 못했습니다 — 검사 대상 0건은 통과로 세지 않습니다")
        return 1
    errors: list[str] = []
    for case in cases:
        errors.extend(check_case(case))
    root_html = (ROOT / "index.html").read_text(encoding="utf-8")
    for case in cases:
        if f'href="{case}/"' not in root_html:
            errors.append(f"목록 링크 없음 — {case}")
    if errors:
        print("\n".join(errors))
        return 1
    image_count = sum(len(re.findall(r'<img\s', (ROOT / case / "index.html").read_text(encoding="utf-8"))) for case in cases)
    print(f"page contract OK: {len(cases)}건, 게시 이미지 참조 {image_count}개, 깨진 경로 0개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
