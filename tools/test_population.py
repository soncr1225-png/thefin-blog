#!/usr/bin/env python3
"""모집단 폐쇄 게이트의 자체역검증.

무엇을 지키나 — 2026-08-18 실측:
  `_meta.txt` 가 없는 `2026-9999/index.html` 과 중첩된 `archive/2026-9998/index.html` 을 심어도
  당시 검사기는 "6건"만 보고 **exit 0** 이었다. 공개는 파일이 발행되면 일어나는데
  모집단은 메타 파일 관행을 따라갔기 때문이다.
  필드 하나가 아니라 **산출물 하나가 통째로 모든 검사를 우회**하는 축이다.

왜 스스로 트리를 짓나:
  리포 안에 시험 HTML 을 만들면 그 자체가 오탐이 된다(게이트가 자기 픽스처를 위반으로 센다).
  그래서 `discover(root)` 를 파라미터로 받게 만들고 여기서 임시 트리를 지어 직접 부른다.

실행: python tools/test_population.py   (pytest 없이도 돈다 — 훅이 소비한다)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_pages import check_population, discover  # noqa: E402


def _tree(root: Path, rels: list[str], meta: list[str], links: list[str]) -> None:
    """rels = index.html 을 둘 폴더 / meta = _meta.txt 를 둘 폴더 / links = 루트 목록이 링크할 폴더."""
    for r in rels:
        d = root / r
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text("<html></html>", encoding="utf-8")
    for m in meta:
        d = root / m
        d.mkdir(parents=True, exist_ok=True)
        (d / "_meta.txt").write_text("a\nb\nc", encoding="utf-8")
    body = "".join('<a href="%s/"></a>' % l for l in links)
    (root / "index.html").write_text("<html>%s</html>" % body, encoding="utf-8")


def _writable_base() -> str:
    """쓸 수 있는 임시 부모를 **찾아서** 쓴다.

    🔴2026-08-18 코덱스 반대검증 지적: 초판은 기본 `tempfile` 만 써서 `%TEMP%` ACL 이 막힌
      환경에서 `PermissionError` 로 **exit 1** 이었다. 내 PC 에서만 초록이던 것이다.
      환경 잡음으로 죽는 게이트는 거짓 빨강이 되고, 거짓 빨강은 사람이 게이트를 끄게 만든다
      (이 저장소에서 2026-08-14 에 실제로 저장소 전체 커밋이 막힌 적이 있다).
    ★리포 밖을 먼저 고른다 — 리포 안에 트리를 지으면 모집단 게이트가 그것을 위반으로 센다.
    """
    import os
    here = Path(__file__).resolve().parent
    cands = [os.environ.get("TMPDIR"), os.environ.get("TEMP"), os.environ.get("TMP"),
             str(Path.home() / ".cache"), str(here / "_selfcheck")]
    for c in cands:
        if not c:
            continue
        try:
            p = Path(c)
            p.mkdir(parents=True, exist_ok=True)
            probe = p / ".w"
            probe.write_text("x", encoding="utf-8")
            probe.unlink()
            return str(p)
        except Exception:  # noqa: BLE001
            continue
    raise SystemExit("쓸 수 있는 임시 폴더를 찾지 못했다 — 자체역검증을 조용히 건너뛰지 않는다")


def _run(rels, meta, links, stray=()):
    with tempfile.TemporaryDirectory(dir=_writable_base()) as td:
        root = Path(td)
        _tree(root, rels, meta, links)
        for s in stray:
            p = root / s
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("<html></html>", encoding="utf-8")
        return check_population(discover(root), registry={})


def test_healthy_tree_is_green():
    """A = B = C 이고 stray 0 이면 위반 없음 — 오탐이 없어야 게이트가 살아남는다."""
    errs = _run(["2026-1", "2026-2"], ["2026-1", "2026-2"], ["2026-1", "2026-2"])
    assert errs == [], "정상 트리인데 위반이 났다: %s" % errs


def test_meta_less_page_is_red():
    """수리 전 GREEN 이던 축 ① — `_meta.txt` 없는 1단계 공개 페이지."""
    errs = _run(["2026-1", "2026-9999"], ["2026-1"], ["2026-1"])
    assert any("2026-9999" in e and "계약 밖" in e for e in errs), errs
    assert any("2026-9999" in e and "고아 발행" in e for e in errs), errs


def test_nested_page_is_red():
    """수리 전 GREEN 이던 축 ② — 중첩 경로의 공개 페이지(1단계만 보면 통째로 샌다)."""
    errs = _run(["2026-1", "archive/2026-9998"], ["2026-1"], ["2026-1"])
    assert any("archive/2026-9998" in e and "계약 밖" in e for e in errs), errs


def test_dangling_link_is_red():
    """목록이 링크하는데 페이지가 없다 — 반대 방향도 본다."""
    errs = _run(["2026-1"], ["2026-1"], ["2026-1", "2026-없음"])
    assert any("2026-없음" in e and "페이지가 없다" in e for e in errs), errs


def test_meta_without_page_is_red():
    """계약만 있고 산출물이 없다."""
    errs = _run(["2026-1"], ["2026-1", "2026-빈껍데기"], ["2026-1"])
    assert any("2026-빈껍데기" in e and "index.html 이 없다" in e for e in errs), errs


def test_stray_html_needs_registry():
    """index.html 이 아닌 HTML 은 사유 있는 등재부 밖이면 RED."""
    errs = _run(["2026-1"], ["2026-1"], ["2026-1"], stray=["draft/미리보기.html"])
    assert any("등재부 밖 HTML" in e and "draft/미리보기.html" in e for e in errs), errs


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print("[GREEN] %s" % name)
        except AssertionError as e:
            failed += 1
            print("[RED] %s\n  %s" % (name, e))
    # ★판정을 print 로만 내면 훅이 통과시킨다(A-104 와 같은 병).
    sys.exit(1 if failed else 0)
