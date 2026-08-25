#!/usr/bin/env python3
"""Deterministic contract checks for the static employee-review blog pages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def discover(root: Path = ROOT) -> dict[str, set[str]]:
    """공개 가능한 페이지 모집단을 **디스크 구조에서** 도출한다.

    ★2026-08-16: 사건번호 3개가 손으로 박혀 있어 새 게시물이 검사 대상 밖으로 빠졌다.
      그래서 `_meta.txt` 보유 폴더로 바꿨는데, 그것도 **관행 의존**이었다 —
    ★2026-08-18 실측: `_meta.txt` 없는 `2026-9999/index.html` 과 중첩된
      `archive/2026-9998/index.html` 을 심어도 검사기는 "6건"만 보고 **exit 0** 이었다.
      공개는 파일이 발행되면 일어나는데 모집단은 메타 파일 관행을 따라간 것이다.
      필드 하나가 아니라 **산출물 하나가 통째로 모든 검사를 우회**하는 축이라 여기부터 닫는다.

    A = 재귀 전체의 index.html 보유 폴더(root 자신 제외 · .git 제외) = **실제 공개되는 것**
    B = 루트 index.html 이 링크하는 폴더
    C = `_meta.txt` 보유 폴더 = **계약을 갖춘 것**
    S = index.html 이 아닌 모든 *.html (stray)

    ★디스크 전수를 고른 이유(git 추적이 아니라): 리포 밖 스크래치에서도 픽스처가 돌아야 하고,
      과잉 포함은 **안전한 방향으로** 틀린다(공개 아닌 것을 빨갛게 — 조용한 유출의 반대).
    ★`root` 를 파라미터로 받는다 — 픽스처가 리포 안에 시험 HTML 을 만들면 그 자체가 오탐이 된다.
    """
    def _rel_dirs(pattern: str) -> set[str]:
        out = set()
        for p in root.rglob(pattern):
            if ".git" in p.parts or not p.is_file():
                continue
            rel = p.parent.relative_to(root).as_posix()
            if rel != ".":
                out.add(rel)
        return out

    root_index = root / "index.html"
    root_html = root_index.read_text(encoding="utf-8") if root_index.is_file() else ""
    stray = set()
    for p in root.rglob("*.html"):
        if ".git" in p.parts or not p.is_file() or p.name == "index.html":
            continue
        stray.add(p.relative_to(root).as_posix())
    return {
        "A": _rel_dirs("index.html"),
        "B": {m.group(1) for m in re.finditer(r'href="([^"?#:]+?)/"', root_html)},
        "C": _rel_dirs("_meta.txt"),
        "S": stray,
    }


def load_registry(root: Path = ROOT) -> dict:
    """공개하지 않을 HTML의 면제 등재부(경로 → {사유, 날짜}).

    🔴**fail-closed.** 파일이 없거나 못 읽으면 오류다 — 2026-08-18 코덱스 반대검증 지적:
      초판은 파일이 없으면 `{}` 를 돌려줘, **등재부를 지우면 게이트가 조용히 헐거워졌다.**
      면제 장치가 fail-open 이면 그것은 면제가 아니라 구멍이다.
    """
    p = root / "tools" / "page_registry.json"
    if not p.is_file():
        raise SystemExit(
            f"등재부가 없다 — {p}\n"
            "  면제 등재부는 비어 있어도 파일로 존재해야 한다(`{}`). 지우면 게이트가 헐거워진다."
        )
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"등재부를 읽을 수 없다 — {p}: {e} (게이트가 조용히 꺼지지 않게 오류로 낸다)")
    if not isinstance(data, dict):
        raise SystemExit(f"등재부 형식 오류 — {p}: 최상위는 객체여야 한다")
    return data


def registry_violations(registry: dict) -> list[str]:
    """등재 항목이 **사유와 날짜를 갖췄는지**. 경로만 적고 빠져나가는 것을 막는다.

    🔴2026-08-18 코덱스 지적: 초판은 키 존재만 봐서 `"draft/x.html": null` 도 면제됐다.
      면제는 **왜·언제**가 남아야 나중에 회수할 수 있다.
    """
    out = []
    for path, meta in sorted(registry.items()):
        if not isinstance(meta, dict):
            out.append(f"등재부 항목이 객체가 아니다 — {path} (사유·날짜를 적어라)")
            continue
        for key in ("reason", "date"):
            if not str(meta.get(key) or "").strip():
                out.append(f"등재부 항목에 {key} 가 없다 — {path}")
    return out


def check_population(pop: dict[str, set[str]], registry: dict) -> list[str]:
    """모집단 정합. 네 방향의 대칭차를 전부 본다 — 한 방향만 보면 반대편이 샌다."""
    errors: list[str] = []
    for d in sorted(pop["A"] - pop["C"]):
        errors.append(f"공개되는데 계약 밖 — {d}/index.html 이 발행되지만 _meta.txt 가 없다")
    for d in sorted(pop["C"] - pop["A"]):
        errors.append(f"_meta.txt 만 있고 index.html 이 없다 — {d}")
    for d in sorted(pop["B"] - pop["A"]):
        errors.append(f"목록이 링크하는데 페이지가 없다 — {d}")
    for d in sorted(pop["A"] - pop["B"]):
        errors.append(f"고아 발행 — {d} (공개되지만 목록에서 링크되지 않는다)")
    for f in sorted(pop["S"] - set(registry)):
        errors.append(f"등재부 밖 HTML — {f} (tools/page_registry.json 에 경로·사유·날짜를 등재하라)")
    errors.extend(registry_violations(registry))
    return errors


def check_root_page(root: Path = ROOT) -> list[str]:
    """루트 목록 페이지도 **공개된다** — 내부 문구가 있으면 RED.

    🔴2026-08-18 코덱스 반대검증이 잡은 구멍: 모집단 A 는 `root` 자신을 제외한다(사건 폴더만 셈).
      그래서 루트 `index.html` 에 `내부 검토용`·`class="w devnote"` 를 넣어도 **exit 0** 이었다.
      저장소에 `.nojekyll` 이 있어 루트 HTML 도 경로 그대로 공개되는데도 그랬다.
      오늘 사건 페이지에서 실제로 터진 사고와 **같은 형태가 루트에 남아 있었다.**
    """
    p = root / "index.html"
    if not p.is_file():
        return ["루트 목록 페이지가 없다 — index.html"]
    html = p.read_text(encoding="utf-8")
    return [f"루트 목록 공개 금지 문구 — {phrase}" for phrase in FORBIDDEN_PUBLIC if phrase in html]


def discover_cases(root: Path = ROOT) -> list[str]:
    """계약을 갖춘 게시물(= A ∩ C). 계약 밖은 check_population 이 RED 로 낸다."""
    pop = discover(root)
    return sorted(pop["A"] & pop["C"])


FORBIDDEN_PUBLIC = (
    "자료에 보증금 액수가 적혀",
    "자료에 표기되지",
    "이 대본은 현장 방문을 했다는 전제로",
    "타당합니다",
    "삼겠습니다",
    "예상낙찰가",
    "입찰 상한선",
    # 🔴2026-08-18 오전 신설 → **같은 날 오후 대표 결정으로 해제**.
    #   신설 경위: 내부 문서가 공개 URL 로 나간 사고(대표가 라이브에서 발견).
    #   해제 경위: 대표가 **위험을 고지받은 상태에서** 내부 검토 메모의 공개 복원을 선택했다.
    #     고지 내용 = "독자에게 배관 사정·초안 대비 수정 내역·사내 표기(대표 확정 B-2, 커밋 해시)가
    #     다시 보이고, 이 게이트를 풀면 다음에 같은 노출을 아무도 못 막는다."
    #   ★그래서 **이 7개만** 목록에서 뺐다. 아래 원래 항목들(보증금 액수·예상낙찰가·입찰 상한선 등
    #     법적·영업적 위험 문구)과 외부 이미지·깨진 경로 검사는 **그대로 살아 있다**.
    #   ★되살리려면 이 블록의 주석을 지우고 아래 7줄을 FORBIDDEN_PUBLIC 안으로 되돌리면 된다:
    #       "내부 검토용" / "네이버에 옮기지 마세요" / "배관 사정" / 'class="w devnote"'
    #       / "이이사님이 주신 초안" / "대표 확정 2026" / "대표 지적 2026"
)


def _strip_approved_devnote(html: str) -> str:
    """대표 승인(2026-08-18)된 내부 검토 블록을 **문구 검사 대상에서만** 제외한다.

    div 균형을 세어 블록 끝을 찾는다 — 첫 `</div>` 를 끝으로 보면 중첩 때문에 잘못 자른다.
    블록이 없거나 균형이 안 맞으면 **원문 그대로** 돌려준다(자르지 않는 쪽이 안전).
    """
    key = 'class="w devnote"'
    i = html.find(key)
    if i < 0:
        return html
    start = html.rfind("<div", 0, i)
    if start < 0:
        return html
    depth, j = 0, start
    while j < len(html):
        nd, nc = html.find("<div", j), html.find("</div>", j)
        if nc < 0:
            return html
        if 0 <= nd < nc:
            depth += 1
            j = nd + 4
        else:
            depth -= 1
            j = nc + 6
            if depth == 0:
                return html[:start] + html[j:]
    return html



# ── A-15 · 다음 차수 매각기일·최저가 금지 (대표 확정 2026-08-15) ────────────────
#   정본 = docs/블로그_문체정본_더핀.md A-15. 대표 원문:
#     "다음 매각기일을 보여주는 건 이번 차수 말고 **다음 차수를 노리게 만드는** 형태야."
#   🔴2026-08-26 실제 위반 — 51365 원고에 1~4차 기일·최저가 표를 실었다. 결론은
#     "기다리면 손해"였지만 표 자체가 다음 차수를 광고한다. 규칙이 막는 것이 그것이다.
#   ★판정을 구조에서 도출한다: _meta.txt 3번째 줄이 이번 차수 매각기일이다.
#     그보다 **뒤인 날짜**는 다음 차수다. 과거 날짜(전입·말소·준공)는 앞이라 안 걸린다.
#     단지명의 '3차'(문정3차푸르지오) 같은 오탐도 날짜로 잡으므로 생기지 않는다.
_DATE_PATS = (
    re.compile(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})"),
    re.compile(r"(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일"),
)


def _dates(text: str) -> set[tuple[int, int, int]]:
    out = set()
    for pat in _DATE_PATS:
        for y, m, d in pat.findall(text):
            try:
                out.add((int(y), int(m), int(d)))
            except ValueError:
                pass
    return out



# ── 평형 일치 · 목록 제목 vs 본문 (2026-08-26) ──────────────────────────────
#   🔴같은 값을 두 곳에서 적으면 갈린다 — 실측 2건:
#     · 51365 = 내가 **전용평(32.47)** 을 평형이라 썼다. 평형은 **공급면적** 기준이고
#       옥션원이 목록에 '공급 43평형'이라 직접 적어 준다. 썸네일(43)과 본문(32)이 어긋났다.
#     · 72192 = _meta.txt 는 40평형, 본문은 49평형. 목록과 글이 갈렸다.
#   ★두 생산자(_meta.txt 제목 · 본문 제목)가 같은 값을 말하는지만 본다.
#     둘 다 틀린 경우는 여기서 못 잡는다 — 그건 킷 썸네일(공급평형 정본)과의 대조 몫이다.
_PY = re.compile(r"(\d{1,3})\s*평형")


def check_pyeong_agreement(case: str, meta: list[str], html: str) -> list[str]:
    m_meta = _PY.search(meta[1] if len(meta) > 1 else "")
    m_body = re.search(r'class="se-title"[^>]*>([^<]+)', html)
    if not m_meta or not m_body:
        return []
    m_title = _PY.search(m_body.group(1))
    if not m_title:
        return []
    if m_meta.group(1) != m_title.group(1):
        return ["%s: 평형이 목록과 글에서 다르다 — _meta.txt %s평형 vs 본문 %s평형 "
                "(평형은 공급면적 기준 · 전용평과 혼동 금지)"
                % (case, m_meta.group(1), m_title.group(1))]
    return []


def check_next_round_leak(case: str, meta: list[str], public: str) -> list[str]:
    """이번 차수 매각기일보다 뒤인 날짜가 **회차 문맥에서** 보이면 빨강.

    🔴미래 날짜를 전부 잡으면 안 된다(2026-08-26 실측 오탐 4건):
      · `<style>` 안의 주석 날짜 — 태그만 지우면 CSS 본문이 남는다 → style/script 통째로 제거
      · *"구리시는 2027년 12월 31일까지 토지거래허가구역"* — 정당한 법적 사실이지 다음 차수가 아니다
    그래서 **문맥으로 좁힌다**: 그 날짜 둘레에 `차`(회차) 또는 `최저`가 있을 때만 다음 차수로 본다.
    영구 빨강은 사람이 게이트를 꺼 버리게 만든다 — 좁히는 것이 게이트를 살리는 길이다.
    """
    sale = _dates(meta[2] if len(meta) > 2 else "")
    if not sale:
        return ["%s: _meta.txt 3번째 줄에서 매각기일을 못 읽었다 — A-15를 검사할 수 없다" % case]
    this_round = max(sale)

    body = re.sub(r"<(style|script)[^>]*>.*?</>", " ", public, flags=re.S | re.I)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", body)

    hits = []
    for pat in _DATE_PATS:
        for m in pat.finditer(text):
            try:
                d = tuple(int(g) for g in m.groups())
            except ValueError:
                continue
            if d <= this_round:
                continue
            around = text[max(0, m.start() - 60):m.end() + 60]
            if "차" in around or "최저" in around:
                hits.append((d, re.sub(r"\s+", " ", around.strip())[:70]))
    if not hits:
        return []
    d, ctx = sorted(hits)[0]
    return ["%s: 다음 차수 기일이 본문에 있다 — %04d.%02d.%02d (이번 차수 %04d.%02d.%02d) "
            "· 문체 정본 A-15(대표 확정 2026-08-15) · 근처: %s"
            % (case, *d, *this_round, ctx)]

def check_case(case: str) -> list[str]:
    errors: list[str] = []
    folder = ROOT / case
    meta_path, html_path = folder / "_meta.txt", folder / "index.html"
    if not meta_path.is_file() or not html_path.is_file():
        return [f"{case}: _meta.txt 또는 index.html 없음"]
    meta = meta_path.read_text(encoding="utf-8").splitlines()
    html = html_path.read_text(encoding="utf-8")
    # 🔴2026-08-18 — 예전에는 `html.split('<hr class="cut">')[0]` 을 공개로 봤다. 그 전제가 사고를 냈다.
    #   이 파일들은 GitHub Pages 로 **파일 전체가 공개**된다. 자르는 선은 매니저가 네이버에 복붙할 때
    #   쓰라는 표시일 뿐 배포를 막지 않는다. 그래서 선 뒤에 있던 devnote(개발 로그·사내 표기)가
    #   금지 문구 검사를 한 번도 안 받고 공개 URL 로 나갔다(대표가 라이브에서 발견).
    #   ★검사 범위는 "우리가 공개라고 믿는 곳"이 아니라 **실제로 배포되는 것 전체**여야 한다.
    # 🔴2026-08-18 오후 — 대표가 내부 검토 블록의 **공개 복원**을 선택했다(위험 고지 후).
    #   그 블록 안에는 "예상낙찰가와 입찰 상한선은 공개하지 않았습니다" 처럼 **금지어를 부정하는
    #   문장**이 들어 있어, 단순 부분문자열 검사가 *안 실었다는 설명*까지 빨갛게 만든다.
    #   ★그래서 목록을 지우지 않고 **승인된 블록만 문구 검사 대상에서 뺀다.**
    #     - 기사 본문에 진짜 `예상낙찰가` 수치가 들어오면 **여전히 RED**(보호 유지)
    #     - 블록 밖 검사(외부 이미지·깨진 경로·필수 형식)는 전 파일 그대로
    #   ★되돌리려면 이 블록을 지우고 `public = html` 한 줄로 되돌리면 된다.
    public = _strip_approved_devnote(html)
    if len(meta) != 3 or not all(line.strip() for line in meta):
        errors.append(f"{case}: _meta.txt는 빈 줄 없는 3줄이어야 함")
    required = (
        '<meta name="robots" content="noindex, nofollow">',
        "word-break:keep-all",
        "table-layout:fixed",
        "border-left:3px solid #555",
        '<hr class="cut">',
        'class="tag"',
        # 🔴`class="w devnote"` 를 필수에서 뺐다(2026-08-18).
        #   내부 검토 블록은 공개 노출 사고로 6편 전부에서 제거됐다(b1d2dbd). 필수로 두면
        #   **정상 상태가 영구 RED** 가 되고, 영구 빨강은 사람이 게이트를 꺼버리게 만든다.
    )
    for token in required:
        if token not in html:
            errors.append(f"{case}: 필수 형식 없음 — {token}")
    for phrase in FORBIDDEN_PUBLIC:
        if phrase in public:
            errors.append(f"{case}: 공개 본문 금지 문구 — {phrase}")
    errors += check_next_round_leak(case, meta, public)
    errors += check_pyeong_agreement(case, meta, html)
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


#: 네이버 저품질(어뷰징) 판정 — **여기서 새로 만들지 않는다.**
#  정본 엔진 = `thr-fin-intranet/blog-rules/naver_blog_safety.js`(ADR-20260613에서 결정).
#  발행 화면·대본 추출·이 검사기가 **같은 파일**을 부른다. 규칙을 복제하면 세 곳이 서로 다른
#  판정을 내고, 그때 아무도 어느 게 맞는지 모른다(볼트 `02_결정/산출기_단일화_원칙.md`).
SAFETY_JS = ROOT.parent / "thr-fin-intranet" / "blog-rules" / "naver_blog_safety.js"
ABUSE_FAIL_GRADES = ("위험",)      # '주의'는 경고로 띄우고 막지는 않는다(막으면 게이트를 끄게 된다)


def check_naver_abuse(cases: list[str]) -> list[str]:
    """게시본을 어뷰징 검사기에 통과시킨다. node·엔진이 없으면 **통과가 아니라 오류**다."""
    import json
    import shutil
    import subprocess

    if not SAFETY_JS.is_file():
        return [f"어뷰징 검사기 없음 — {SAFETY_JS} (게이트가 조용히 꺼지지 않게 오류로 낸다)"]
    if not shutil.which("node"):
        return ["node 없음 — 어뷰징 검사를 돌리지 못했다(미실행은 통과가 아니다)"]

    script = (
        "const S=require(process.argv[1]),X=require(process.argv[2]),fs=require('fs');"
        "const out={};for(const c of process.argv.slice(4)){"
        "const h=fs.readFileSync(process.argv[3]+'/'+c+'/index.html','utf8');"
        "const r=S.analyzeDraft(X.publicText(h),X.meta(h));"
        "out[c]={score:r.score,grade:r.grade,issues:(r.issues||[]).map(i=>i.code+':'+i.severity)};}"
        "console.log(JSON.stringify(out));"
    )
    proc = subprocess.run(
        ["node", "-e", script, str(SAFETY_JS), str(ROOT / "tools" / "_extract.js"), str(ROOT), *cases],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        return ["어뷰징 검사 실행 실패 — " + (proc.stderr or "").strip()[:300]]

    errors: list[str] = []
    for case, r in json.loads(proc.stdout).items():
        mark = "!" if r["grade"] in ABUSE_FAIL_GRADES else " "
        print(f"  {mark} 어뷰징 {case}: {r['score']}점 {r['grade']}"
              + (f" — {', '.join(r['issues'])}" if r["issues"] else ""))
        if r["grade"] in ABUSE_FAIL_GRADES:
            errors.append(f"어뷰징 위험 등급 — {case} ({r['score']}점): {', '.join(r['issues'])}")
    return errors


def main() -> int:
    # ★한글 콘솔(cp949)에서 — 같은 문자를 출력하다 죽으면 **오류를 못 읽는다**.
    #   2026-08-17: 신규 검사가 실제로 위반을 잡았는데 출력 단계에서 UnicodeEncodeError로
    #   죽어 "무엇이 틀렸는지"가 안 보였다. 검사기가 자기 결과를 못 보여주면 게이트가 아니다.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    # ★모집단 먼저. 어떤 필드를 검사하느냐보다 **무엇을 검사 대상으로 세느냐**가 먼저다 —
    #   2026-08-18에 공개 페이지 2개가 모집단 밖이라 모든 검사를 통째로 우회했다.
    pop = discover()
    errors: list[str] = check_population(pop, load_registry())
    errors.extend(check_root_page())
    cases = sorted(pop["A"] & pop["C"])
    if not cases:
        # 표본 0건은 통과가 아니다 — 검사기가 아무것도 안 본 것이다.
        print("게시물을 하나도 발견하지 못했습니다 — 검사 대상 0건은 통과로 세지 않습니다")
        return 1
    for case in cases:
        errors.extend(check_case(case))
    root_html = (ROOT / "index.html").read_text(encoding="utf-8")

    # ★목록 표지는 썸네일이어야 한다(대표 지적 2026-08-17).
    #   글 안에는 썸네일을 넣고 목록은 안 고쳐, 표지에 카드1(사건요약)이 뜨는 사고가 났다.
    #   "한쪽만 고치고 고쳤다고 하는" 형태라 검사기로 박는다.
    for case in cases:
        thumb = ROOT / case / "img" / "썸네일.png"
        ref = f'{case}/img/썸네일.png'
        if thumb.exists() and ref not in root_html:
            errors.append(f"목록 표지가 썸네일이 아니다 — {case} (img/썸네일.png 가 있는데 목록이 안 쓴다)")

    # ★목록·본문이 가리키는 이미지가 실제로 있어야 한다.
    for m in re.finditer(r'src="([^"]+\.(?:png|jpg|jpeg))"', root_html):
        if not (ROOT / m.group(1)).exists():
            errors.append(f"목록 이미지 없음 — {m.group(1)}")
    for case in cases:
        page = (ROOT / case / "index.html").read_text(encoding="utf-8")
        for m in re.finditer(r'src="([^"]+\.(?:png|jpg|jpeg))"', page):
            if not (ROOT / case / m.group(1)).exists():
                errors.append(f"본문 이미지 없음 — {case}/{m.group(1)}")
    errors.extend(check_naver_abuse(cases))

    if errors:
        print("\n".join(errors))
        return 1
    image_count = sum(len(re.findall(r'<img\s', (ROOT / case / "index.html").read_text(encoding="utf-8"))) for case in cases)
    print(f"page contract OK: {len(cases)}건, 게시 이미지 참조 {image_count}개, 깨진 경로 0개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
