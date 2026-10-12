"""점신(jeomsin.co.kr) 신년운세 크롤러 (Firecrawl 사용).

/newyearunse 는 프로필(이름·생년월일 등)이 있어야 결과가 나오는 페이지라서
Firecrawl 브라우저로 사이트를 연 뒤, 사이트 자체의 신년운세 요청 함수를
executeJavascript 액션으로 호출해 결과를 받아온다.

사용 예:
  python jeomsin_newyear.py --name 홍길동 --birth 1990-01-01 --time 12:00 --gender male
  python jeomsin_newyear.py --name 홍길동 --birth 1990-01-01 --calendar lunar --leap --gender female --year 2027
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
FIRECRAWL_URL = "https://api.firecrawl.dev/v2/scrape"

# 사이트 webpack 모듈 id (사이트가 재배포되면 바뀔 수 있음)
MOD_KIND, MOD_NEWYEAR, NEWYEAR_CHUNKS = 75910, 53974, [7725, 4380, 4806]

# 신년운세 페이지 탭 순서 (Kt 키 -> 저장용 한글 이름)
CATEGORIES = [
    ("Saju", "평생운세/대운풀이"), ("Total", "총운"), ("Money", "재물운"), ("Love", "애정운"),
    ("Marriage", "결혼운"), ("Job", "직업운"), ("Business", "사업운"), ("Friend", "친구운"),
    ("Health", "건강운"), ("ReviewYear", "다시보는/미리보는 한 해"),
]


def load_key():
    text = (HERE / ".env").read_text(encoding="utf-8")
    m = re.search(r"fc-[A-Za-z0-9]+", text)
    if not m:
        raise RuntimeError(".env 에서 Firecrawl API 키(fc-...)를 찾지 못했습니다.")
    return m.group(0)


def build_js(profile, year):
    keys = json.dumps([k for k, _ in CATEGORIES])
    start = f"""
(function(){{
  window.__r = null;
  var req;
  self.webpackChunkjeomsin_web_react.push([[Math.floor(Math.random()*1e9)], {{}}, function(r){{ req = r; }}]);
  var Kt = req({MOD_KIND}).Kt;
  var p = {json.dumps(profile, ensure_ascii=False)};
  Promise.all({json.dumps(NEWYEAR_CHUNKS)}.map(function(c){{ return req.e(c); }})).then(function(){{
    var f = req({MOD_NEWYEAR}).s, out = {{}};
    return {keys}.reduce(function(chain, k){{
      return chain.then(function(){{
        return f(p, '{year}', Kt[k].kind).then(function(d){{ out[k] = d === undefined ? null : d; }});
      }});
    }}, Promise.resolve()).then(function(){{ return out; }});
  }}).then(function(o){{ window.__r = {{ok: true, data: o}}; }})
    .catch(function(e){{ window.__r = {{ok: false, error: String(e)}}; }});
}})();
"""
    # Firecrawl 반환값에서 비ASCII 문자가 깨지지 않도록 \\uXXXX 로 이스케이프
    collect = (r"JSON.stringify(window.__r).replace(/[\u0080-￿]/g, function(c){"
               r" return '\\u' + ('0000' + c.charCodeAt(0).toString(16)).slice(-4); })")
    return start, collect


def scrape(key, profile, year):
    start, collect = build_js(profile, year)
    body = {
        "url": "https://www.jeomsin.co.kr/",
        "formats": ["markdown"],
        "waitFor": 2000,
        "actions": [
            {"type": "wait", "milliseconds": 3000},
            {"type": "executeJavascript", "script": start},
            {"type": "wait", "milliseconds": 15000},
            {"type": "executeJavascript", "script": collect},
        ],
    }
    req = urllib.request.Request(
        FIRECRAWL_URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        res = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Firecrawl 오류 {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
    value = res["data"]["actions"]["javascriptReturns"][-1]["value"]
    result = json.loads(value) if value else None
    if not result:
        raise RuntimeError("결과가 아직 도착하지 않았습니다. 잠시 후 다시 시도하세요.")
    if not result["ok"]:
        raise RuntimeError(f"사이트 요청 실패: {result['error']}")
    return result["data"]


def to_markdown(node, depth=2):
    """API 응답(menuN/categoryN/depthN 트리)을 읽기 쉬운 마크다운으로 변환."""
    lines = []
    if isinstance(node, dict):
        title = node.get("title")
        if isinstance(title, str) and title.strip():
            lines.append(f"{'#' * min(depth, 6)} {title.strip()}\n")
        for k, v in node.items():
            if k == "title":
                continue
            if isinstance(v, (dict, list)):
                lines.extend(to_markdown(v, depth + 1))
            elif isinstance(v, str) and v.strip():
                label = {"text": "", "img": "> "}.get(k, f"**{k}**: ")
                lines.append(f"{label}{v.strip()}\n")
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                lines.append(f"- {k}: {v}")
    elif isinstance(node, list):
        for item in node:
            lines.extend(to_markdown(item, depth))
    return lines


def make_fortune(name, birth, time="", calendar="solar", leap=False, gender="male",
                 year="2026", out=HERE / "output"):
    """크롤링 -> JSON/MD 저장 -> HTML 페이지와 목록 페이지 생성. 생성된 HTML 경로를 반환."""
    import build_site

    name = name.strip()
    if not name:
        raise ValueError("이름을 입력하세요.")
    if not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", birth or ""):
        raise ValueError("생년월일은 YYYY-MM-DD 형식으로 입력하세요.")
    if time and not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", time):
        raise ValueError("태어난 시간은 HH:MM 형식으로 입력하세요.")
    if calendar not in ("solar", "lunar") or gender not in ("male", "female"):
        raise ValueError("양력/음력, 성별 값을 확인하세요.")

    y, m, d = (int(x) for x in birth.split("-"))
    # 사이트는 '시간 모름'을 00시 00분으로 보낸다
    hh, mm = time.split(":") if time else ("0", "0")
    profile = {
        "name": name, "birthYear": str(y), "birthMonth": str(m), "birthDay": str(d),
        "birthTime": f"{int(hh):02d}", "birthMinute": f"{int(mm):02d}",
        "calendarType": 0 if calendar == "solar" else 1,
        "isLeapMonth": bool(leap) and calendar == "lunar", "gender": "0" if gender == "male" else "1",
    }

    data = scrape(load_key(), profile, year)
    if not any(data.values()):
        raise RuntimeError(f"점신에서 {year}년 운세 결과가 오지 않았습니다. 아직 제공하지 않는 연도일 수 있어요.")

    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[\/:*?"<>|\s]+', "_", name)
    stem = f"newyear_{year}_{safe}_{y:04d}{m:02d}{d:02d}"
    json_path = out / f"{stem}.json"
    json_path.write_text(
        json.dumps({"profile": profile, "year": year, "result": data}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    md = [f"# {year}년 신년운세 - {name} ({birth}, {calendar}, {gender})\n"]
    for k, label in CATEGORIES:
        md.append(f"\n---\n\n## [{label}]\n")
        md.extend(to_markdown(data.get(k), 3) if data.get(k) else ["(결과 없음)\n"])
    (out / f"{stem}.md").write_text("\n".join(md), encoding="utf-8")

    page = build_site.build(json_path)
    build_site.build_index(out)
    return page


def ask(label, default=""):
    v = input(f"{label}{f' [{default}]' if default else ''}: ").strip()
    return v or default


def main():
    ap = argparse.ArgumentParser(description="점신 신년운세 크롤러 (Firecrawl). 인자를 빼면 하나씩 물어본다.")
    ap.add_argument("--name")
    ap.add_argument("--birth", help="YYYY-MM-DD")
    ap.add_argument("--time", help="HH:MM (모르면 생략)")
    ap.add_argument("--calendar", choices=["solar", "lunar"])
    ap.add_argument("--leap", action="store_true", help="음력 윤달")
    ap.add_argument("--gender", choices=["male", "female"])
    ap.add_argument("--year", default="2026", help="운세 연도")
    ap.add_argument("--out", default=str(HERE / "output"))
    a = ap.parse_args()

    interactive = not (a.name and a.birth and a.gender)
    if interactive:
        a.name = a.name or ask("이름")
        a.birth = a.birth or ask("생년월일 (YYYY-MM-DD)")
        if a.calendar is None:
            a.calendar = "lunar" if ask("양력/음력", "양력") == "음력" else "solar"
        if a.calendar == "lunar" and not a.leap:
            a.leap = ask("윤달입니까? (y/N)", "N").lower() == "y"
        if a.time is None:
            a.time = ask("태어난 시간 (HH:MM, 모르면 엔터)")
        if a.gender is None:
            a.gender = "female" if ask("성별 (남/여)") == "여" else "male"
        a.year = ask("운세 연도", a.year)

    print("점신에서 운세를 가져오는 중입니다 (30초 정도 걸려요)...")
    try:
        page = make_fortune(a.name, a.birth, a.time or "", a.calendar or "solar", a.leap,
                            a.gender, a.year, a.out)
    except (ValueError, RuntimeError) as e:
        sys.exit(f"실패: {e}")
    print(f"완료: {page}")
    print(f"목록: {page.parent / 'index.html'}")


if __name__ == "__main__":
    main()
