#!/usr/bin/env python3
"""Render the five established blog-card types without calculating values.

Every displayed string comes from card_data.json. Missing source values result
in an omitted card with a recorded reason; this module has no auction, tax,
distribution, or money arithmetic.
"""

from __future__ import annotations

import argparse
import json
import sys
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


#: 카드 액센트 = **페르소나 스킨 정본에서 온다**. 여기에 색표를 새로 만들지 않는다.
#  ★2026-08-17 대표 지적("디자인 통일"): 썸네일·푸터는 페르소나별로 갈리는데 카드만
#    고정 금테라 한 글 안에서 톤이 어긋났다. 원인은 썸네일과 **똑같다** — 이 렌더러가
#    페르소나를 아예 안 받았다(볼트 `02_결정/산출기_단일화_원칙.md` §8).
_THEME_SRC = ROOT.parent / "thefin-auction-report" / "src"


@lru_cache(maxsize=None)
def _accent(persona: str | None) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """(테두리·구분선용 진한 액센트, 제목 그라데이션 밝은 끝) — 정본 blog_theme에서 도출."""
    import sys as _sys
    if str(_THEME_SRC) not in _sys.path:
        _sys.path.insert(0, str(_THEME_SRC))
    from utils import blog_theme                                   # noqa: PLC0415
    hexv = blog_theme.theme(persona)["accent"].lstrip("#")
    base = tuple(int(hexv[i:i + 2], 16) for i in (0, 2, 4))
    light = tuple(min(255, round(c + (255 - c) * 0.55)) for c in base)
    return base, light


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


def _accent_text(image: Image.Image, xy: tuple[int, int], text: str,
                 font: ImageFont.FreeTypeFont, accent) -> None:
    base, light = accent
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=font, fill=255, anchor="mm")
    ramp = Image.linear_gradient("L").resize(image.size)
    image.paste(ImageOps.colorize(ramp, black=light, white=base), (0, 0), mask)


def _background(height: int) -> Image.Image:
    ramp = Image.linear_gradient("L").resize((WIDTH, height))
    return ImageOps.colorize(ramp, black=(31, 31, 29), white=(27, 28, 26))


def render_card(card: dict[str, Any], destination: Path, persona: str | None = None) -> None:
    rows = card["rows"]
    if not 2 <= len(rows) <= 5:
        raise ValueError(f"행 수는 2~5개여야 합니다: {destination}")
    height = max(460, 226 + len(rows) * 78)
    image = _background(height)
    draw = ImageDraw.Draw(image)
    accent = _accent(persona)
    base, light = accent
    line = (58, 58, 55)
    label_color, white, highlight = (188, 188, 188), (255, 255, 255), light
    rule = tuple(round(c * 0.65) for c in base)

    draw.rectangle((24, 24, WIDTH - 25, height - 25), outline=base, width=2)
    _accent_text(image, (WIDTH // 2, 76), card["title"],
                 _fit_font(draw, card["title"], FONT_BOLD, 48, 680), accent)
    draw.line((86, 132, WIDTH - 86, 132), fill=rule, width=1)

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
        #: 도출 카드는 데이터에 적지 않는다 — 적혀 있으면 그것부터 오류다(손 타이핑 재유입 차단).
        hand = [k for k in DERIVED_KINDS if k in cards]
        if hand:
            errors.append(f"{case_key}: {hand}는 도출 대상이라 손으로 적을 수 없습니다 "
                          f"(inputs에 최저가·전용면적·조정만 적으세요)")
        covered = set(cards) | set(omitted) | set(DERIVED_KINDS)
        if covered != set(CARD_FILES) or (set(cards) & set(omitted)):
            errors.append(f"{case_key}: 5종 카드가 cards/omitted/도출에 정확히 한 번씩 있어야 합니다")
        if not (case.get("inputs") or {}).get("최저가_원"):
            errors.append(f"{case_key}: inputs.최저가_원 없음 — 취득세를 도출할 수 없습니다")
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


#: 돈이 걸린 두 카드는 **도출한다**. 여기 문자열로 적어 넣지 않는다.
#  ★2026-08-17 대표 지적: "고쳐서 매번 발행할거면 내가 왜 이런 프로그램 엔진을 요청하냐."
#    그날 나는 취득세를 계산해서 `"2.91% · 2,466만 원"` 처럼 card_data.json에 타이핑했다.
#    그러면 7번째 사건은 또 손으로 해야 하고, 그건 엔진이 아니다.
#    이제 사람이 적는 것은 **입력**(최저가·전용면적·조정)뿐이고 계산은 bid_calc가 한다.
DERIVED_KINDS = ("acquisition_tax", "distribution")


def _derive(case_key: str, case: dict[str, Any]) -> tuple[dict, dict]:
    """(도출된 카드, 못 만든 사유) — seed가 있으면 seed에서, 없으면 inputs에서."""
    import sys as _sys
    if str(_THEME_SRC) not in _sys.path:
        _sys.path.insert(0, str(_THEME_SRC))
    from utils import blog_cards                                # noqa: PLC0415

    inp = case.get("inputs") or {}
    seed_path = inp.get("seed")
    seed: dict[str, Any] = {}
    if seed_path:
        sp = _THEME_SRC.parent / seed_path
        if sp.is_file():
            seed = json.loads(sp.read_text(encoding="utf-8"))
    #: 최저가는 회차마다 바뀐다 — seed가 아니라 **게시 표에서 확인한 현재 회차 값**이 정본이다
    #  (2026-08-17 실측: 3414 seed 8.69억 vs 현재 회차 6.952억).
    ref = inp.get("source_ref") or seed_path or case_key

    #: 백필 스냅샷 — seed에 아직 안 들어간 사건의 예상배당(옥션원 ca_analy 원자료).
    #  경로는 데이터에 적고, 읽는 방법은 여기 한 곳에만 둔다.
    bd = None
    bd_path = inp.get("baedang")
    if bd_path:
        bp = _THEME_SRC.parent / bd_path
        if bp.is_file():
            bd = json.loads(bp.read_text(encoding="utf-8")).get("예상배당")

    #: 🔴2026-08-26 — 여기서 `from_seed` 를 그대로 돌려주면 **배당을 얻는 대신 취득세를 잃는다.**
    #  `from_seed` 는 전용면적·조정을 seed(`slide23`·`meta.규제지역`)에서만 찾는데, 백필로 예상배당만
    #  붙인 사건은 seed 가 비어 있어 `derive_tax` 가 조용히 실패했다(51365 실측: 배당 연결 전 3장 →
    #  연결 후에도 3장인데 **취득세가 배당으로 바뀐 것**이라 개수만 보면 안 보인다).
    #  ★`inputs` 는 이 파일이 스스로 "회차마다 바뀌므로 seed 가 아니라 여기가 정본"이라 적어 둔 자리다
    #  (위 최저가 주석). 같은 이유가 전용면적·조정에도 그대로 걸린다 — **inputs 를 seed 위에 얹는다.**
    if seed or bd:
        out, why = blog_cards.from_seed(seed, 최저가_원=inp.get("최저가_원"),
                                        source_ref=ref, 예상배당=bd)
        if "acquisition_tax" not in out and inp.get("전용면적_m2") is not None:
            try:
                out["acquisition_tax"] = blog_cards.derive_tax(
                    inp.get("최저가_원"), inp.get("전용면적_m2"),
                    inp.get("조정대상지역"), ref)
                why.pop("acquisition_tax", None)
            except Exception as e:                              # noqa: BLE001
                why["acquisition_tax"] = str(e)
        return out, why

    out, why = {}, {}
    try:
        out["acquisition_tax"] = blog_cards.derive_tax(
            inp.get("최저가_원"), inp.get("전용면적_m2"), inp.get("조정대상지역"), ref)
    except Exception as e:                                      # noqa: BLE001
        why["acquisition_tax"] = str(e)
    why["distribution"] = "예상배당표 미수집 — seed도 백필도 없다(0=fetch실패)"
    return out, why


def generate(data_path: Path, selected_case: str | None = None) -> int:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        raise ValueError("\n".join(errors))
    made = 0
    for case_key, case in data["cases"].items():
        if selected_case and case_key != selected_case:
            continue
        persona = case.get("persona")
        derived, why = _derive(case_key, case)
        cards = dict(case["cards"])
        for kind in DERIVED_KINDS:
            if kind in derived:
                cards[kind] = derived[kind]                     # 손 타이핑을 덮어쓴다
            elif kind in cards:
                raise ValueError(
                    "%s/%s: 카드가 데이터에 있는데 도출이 안 된다(%s). "
                    "돈이 걸린 값은 손으로 적지 않는다." % (case_key, kind, why.get(kind, "")))
        for kind, card in cards.items():
            render_card(card, ROOT / case_key / "img" / CARD_FILES[kind], persona)
            made += 1
    return made


def main() -> int:
    #: ★한글 콘솔(cp949)에서 — 게이트가 위반을 잡고도 출력 단계에서 죽으면 **사유가 안 보인다**.
    #  2026-08-17 실측: "최저가 없음"을 정확히 잡았는데 화면엔 UnicodeEncodeError만 떴다.
    #  검사기가 자기 결과를 못 보여주면 게이트가 아니다(check_pages.py와 같은 수리).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                           # noqa: BLE001
        pass
    parser = argparse.ArgumentParser(description="THE FIN 블로그 카드 5종 결정론 생성기")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    #: ★사건 목록을 손으로 적지 않는다(2026-08-26). 손 목록이면 새 사건을 등록해도
    #  `--case` 가 거부해 "데이터는 있는데 못 만드는" 상태가 된다. 실제로 51365 가 그랬다.
    #  선택지는 **card_data.json 이 실제로 들고 있는 사건**에서 도출한다.
    try:
        _known = sorted(json.loads(DEFAULT_DATA.read_text(encoding="utf-8"))["cases"])
    except Exception:                                           # noqa: BLE001
        _known = None
    parser.add_argument("--case", choices=_known)
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
