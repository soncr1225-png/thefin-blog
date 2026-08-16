from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_cards as cards


class CardGeneratorTest(unittest.TestCase):
    def test_all_five_card_types_render_without_edge_clipping(self) -> None:
        sample = {
            "title": "긴 제목도 카드 안에 표시",
            "rows": [
                {"label": "긴 왼쪽 항목 이름", "value": "긴 오른쪽 결과 값"},
                {"label": "둘째 항목", "value": "결과 있음", "highlight": True},
                {"label": "셋째 항목", "value": "확인 완료"}
            ],
            "note": "출처와 기준일을 카드 아래에 표시"
        }
        output = cards.ROOT / "2024-68165" / "img"
        written = []
        try:
            for index, filename in enumerate(cards.CARD_FILES.values(), start=1):
                path = output / f"_test_{index}_{filename}"
                written.append(path)
                cards.render_card(sample, path)
                with Image.open(path) as image:
                    self.assertEqual(image.width, 800)
                    self.assertGreaterEqual(image.height, 460)
                    self.assertEqual(image.getbbox(), (0, 0, image.width, image.height))
        finally:
            for path in written:
                path.unlink(missing_ok=True)

    def test_unmade_cards_have_explicit_reasons(self) -> None:
        data = json.loads(cards.DEFAULT_DATA.read_text(encoding="utf-8"))
        self.assertEqual(cards.validate(data), [])
        for case in data["cases"].values():
            self.assertEqual(set(case["cards"]) | set(case["omitted"]), set(cards.CARD_FILES))


if __name__ == "__main__":
    unittest.main()
