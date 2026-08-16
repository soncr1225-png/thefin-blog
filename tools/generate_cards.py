#!/usr/bin/env python3
"""Render the five established blog-card types without calculating values.

Every displayed string comes from card_data.json. Missing source values result
in an omitted card with a recorded reason; this module has no auction, tax,
distribution, or money arithmetic.
"""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path(__file__).with_name("card_data.json")
WIDTH = 800
CARD_FILES = {
    "summary": "카드1_사건요약.png",
    "market_gap": "카드2_감정가실거래.png",
    "rights": "카드3_권리.png",
    "distribution": "카드4_배당.png",
    "acquisition_tax": "카드5_취득세.png",
}
FONT_BOLD = Path(r"C:\Users\s\OneDrive\바탕 화면\잡다\폰트\폰트\SEBANG Gothic Bold.ttf")
FONT_REGULAR = Path(r"C:\Windows\Fonts\malgun.ttf")


@lru_cache(maxsize=None)
def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise FileNotFoundError(f"필수 글꼴 없음: {path}")
    return ImageFont.truetype(str(path), size=size)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, path: Path, start: int, max_width: int) -> ImageFont.FreeTypeFont:
    for size in range(start, 19, -1):
        font = _font(path, size)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
            return font
    raise ValueError(f"카드 폭에 들어가지 않는 문자열: {text}")


def _gold_text(image: Image.Image, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont) -> None:
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=font, fill=255, anchor="mm")
    ramp = Image.linear_gradient("L").resize(image.size)
    gradient = ImageOps.colorize(ramp, black=(246, 220, 151), white=(188, 151, 74))
    image.paste(gradient, (0, 0), mask)


def _background(height: int) -> Image.Image:
    ramp = Image.linear_gradient("L").resize((WIDTH, height))
    return ImageOps.colorize(ramp, black=(31, 31, 29), white=(27, 28, 26))


def render_card(card: dict[str, Any], destination: Path) -> None:
    rows = card["rows"]
    if not 2 <= len(rows) <= 5:
        raise ValueError(f"행 수는 2~5개여야 합니다: {destination}")
    height = max(460, 226 + len(rows) * 78)
    image = _background(height)
    draw = ImageDraw.Draw(image)
    gold, line = (181, 142, 43), (58, 58, 55)
    label_color, white, highlight = (188, 188, 188), (255, 255, 255), (246, 222, 157)

    draw.rectangle((24, 24, WIDTH - 25, height - 25), outline=gold, width=2)
    _gold_text(image, (WIDTH // 2, 76), card["title"], _fit_font(draw, card["title"], FONT_BOLD, 48, 680))
    draw.line((86, 132, WIDTH - 86, 132), fill=(118, 91, 30), width=1)

    y0 = 154
    for index, row in enumerate(rows):
        y = y0 + index * 78
        if index:
            draw.line((46, y - 22, WIDTH - 46, y - 22), fill=line, width=1)
        draw.text((47, y), row["label"], font=_fit_font(draw, row["label"], FONT_REGULAR, 27, 330),
                  fill=label_color, anchor="lm")
        draw.text((753, y), row["value"], font=_fit_font(draw, row["value"], FONT_BOLD, 36, 390),
                  fill=highlight if row.get("highlight") else white, anchor="rm")

    note = card.get("note", "")
    if note:
        draw.text((WIDTH // 2, height - 60), note, font=_fit_font(draw, note, FONT_REGULAR, 20, 680),
                  fill=(145, 145, 145), anchor="mm")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = data.get("cases")
    if not isinstance(cases, dict) or not cases:
        return ["cases가 비어 있습니다"]
    for case_key, case in cases.items():
        cards, omitted = case.get("cards", {}), case.get("omitted", {})
        if set(cards) | set(omitted) != set(CARD_FILES) or set(cards) & set(omitted):
            errors.append(f"{case_key}: 5종 카드가 cards/omitted에 정확히 한 번씩 있어야 합니다")
        for kind, card in cards.items():
            if kind not in CARD_FILES:
                errors.append(f"{case_key}: 알 수 없는 카드 {kind}")
                continue
            if not card.get("source_refs"):
                errors.append(f"{case_key}/{kind}: source_refs 없음")
            for row in card.get("rows", []):
                if not row.get("label") or not row.get("value") or not row.get("source_ref"):
                    errors.append(f"{case_key}/{kind}: label/value/source_ref가 빈 행")
        for kind, reason in omitted.items():
            if not str(reason).strip():
                errors.append(f"{case_key}/{kind}: 생략 사유 없음")
    return errors


def generate(data_path: Path, selected_case: str | None = None) -> int:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        raise ValueError("\n".join(errors))
    made = 0
    for case_key, case in data["cases"].items():
        if selected_case and case_key != selected_case:
            continue
        for kind, card in case["cards"].items():
            render_card(card, ROOT / case_key / "img" / CARD_FILES[kind])
            made += 1
    return made


def main() -> int:
    parser = argparse.ArgumentParser(description="THE FIN 블로그 카드 5종 결정론 생성기")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--case", choices=["2024-68165", "2025-51955", "2026-3414"])
    parser.add_argument("--check", action="store_true", help="데이터 계약만 검사")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        print("\n".join(errors))
        return 1
    if args.check:
        expected = sum(len(case["cards"]) for case in data["cases"].values())
        omitted = sum(len(case["omitted"]) for case in data["cases"].values())
        print(f"card data OK: 생성 대상 {expected}장, 근거 부족 생략 {omitted}장")
        return 0
    print(f"생성 {generate(args.data, args.case)}장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
