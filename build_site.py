"""jeomsin_newyear.py 결과 JSON -> 신년운세 HTML 페이지.

디자인 레퍼런스: Behance 'Eltoro Studio 15th Anniversary'
(검정 그레인 배경, 핑크/그린 듀오톤, 금색 라인 프레임, 타로·카드 모티프)

사용 예:
  python build_site.py output/newyear_2026_홍길동_19990521.json
"""
import datetime
import html
import json
import pathlib
import re
import sys

# 데이터 키 -> (영문 라벨, 카드 문양, 강조색)
CHAPTERS = [
    ("Saju", "NATAL CHART", "eye", "gold"),
    ("Total", "THE YEAR AHEAD", "sparkle", "pink"),
    ("Money", "WEALTH", "diamond", "green"),
    ("Love", "LOVE", "heart", "pink"),
    ("Marriage", "MARRIAGE", "ring", "green"),
    ("Job", "CAREER", "spade", "pink"),
    ("Business", "BUSINESS", "club", "green"),
    ("Friend", "PEOPLE", "sparkle", "pink"),
    ("Health", "HEALTH", "heart", "green"),
    ("ReviewYear", "PREVIEW", "eye", "gold"),
]
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
STEMS = "갑을병정무기경신임계"
STEM_COLORS = ["푸른", "푸른", "붉은", "붉은", "노란", "노란", "흰", "흰", "검은", "검은"]
BRANCHES = "자축인묘진사오미신유술해"
ANIMALS = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]
ANIMALS_EN = ["RAT", "OX", "TIGER", "RABBIT", "DRAGON", "SNAKE", "HORSE", "GOAT", "MONKEY", "ROOSTER", "DOG", "PIG"]
COLORS_EN = {"푸른": "BLUE", "붉은": "RED", "노란": "YELLOW", "흰": "WHITE", "검은": "BLACK"}

SUITS = {
    "heart": '<path d="M12 21s-8-5.2-8-11a4.5 4.5 0 0 1 8-2.8A4.5 4.5 0 0 1 20 10c0 5.8-8 11-8 11z"/>',
    "spade": '<path d="M12 2s8 6.5 8 11a4 4 0 0 1-7 2.6L14 21h-4l1-5.4A4 4 0 0 1 4 13c0-4.5 8-11 8-11z"/>',
    "club": '<circle cx="12" cy="7" r="4"/><circle cx="7" cy="14" r="4"/><circle cx="17" cy="14" r="4"/>'
            '<path d="M11 14h2l1.5 7h-5z"/>',
    "diamond": '<path d="M12 1.5 20 12l-8 10.5L4 12z"/>',
    "sparkle": '<path d="M12 0c.9 7.4 3.6 10.1 12 12-8.4 1.9-11.1 4.6-12 12-.9-7.4-3.6-10.1-12-12C8.4 10.1 11.1 7.4 12 0z"/>',
    "ring": '<circle cx="12" cy="14" r="7" fill="none" stroke-width="2.4"/><path d="M12 1l3.5 3.5L12 8 8.5 4.5z"/>',
    "eye": '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" fill="none" stroke-width="1.6"/>'
           '<circle cx="12" cy="12" r="3.6"/>',
}


def suit(name, cls=""):
    return f'<svg class="suit {cls}" viewBox="0 0 24 24" aria-hidden="true">{SUITS[name]}</svg>'


def esc(s):
    return html.escape(str(s).strip())


def paragraphs(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n", str(text)) if p.strip()]
    return "".join(f"<p>{esc(p)}</p>" for p in parts)


def sorted_keys(node, prefix):
    keys = [k for k in node if re.fullmatch(prefix + r"\d+", k)]
    return sorted(keys, key=lambda k: int(k[len(prefix):]))


def render_depth(depth, accent, cat_title):
    out = []
    title = depth.get("title", "")
    points = [depth[k] for k in sorted_keys(depth, "point")]
    if title and title != cat_title:
        out.append(f'<h4 class="sub">{suit("sparkle", "tiny " + accent)}{esc(title)}</h4>')
    if points:
        icons = ["spade", "heart", "club", "diamond"]
        items = "".join(
            f'<li class="pt"><span class="pt-idx">{suit(icons[i % 4], accent)}<b>{i + 1:02d}</b></span>'
            f'<p>{esc(p)}</p></li>' for i, p in enumerate(points))
        out.append(f'<ol class="points">{items}</ol>')
    if depth.get("img"):
        out.append(f'<p class="tagline {accent}">{esc(depth["img"])}</p>')
    if depth.get("text"):
        out.append(f'<div class="prose">{paragraphs(depth["text"])}</div>')
    return "".join(out)


def render_scores(category, accent):
    nums = [category[k] for k in sorted_keys(category, "num")]
    depths = [category[k] for k in sorted_keys(category, "depth")]
    if not nums or len(nums) != len(depths):
        return ""
    rows = "".join(
        f'<li><span class="sc-label">{esc(d.get("title", ""))}</span>'
        f'<span class="sc-track"><span class="sc-fill" style="--v:{int(n)}%"></span></span>'
        f'<span class="sc-num">{int(n)}</span></li>' for d, n in zip(depths, nums))
    return f'<ul class="scores">{rows}</ul>'


def render_chapter(i, key, en, icon, accent, data):
    menu = next(iter(data.values()))
    title = menu.get("title", "")
    frames = []
    for ck in sorted_keys(menu, "category"):
        cat = menu[ck]
        ctitle = cat.get("title", "")
        body = render_scores(cat, accent)
        body += '<div class="divider">✦</div>'.join(
            render_depth(cat[dk], accent, ctitle) for dk in sorted_keys(cat, "depth"))
        frames.append(
            f'<div class="frame"><span class="frame-title {accent}">{esc(ctitle)}</span>'
            f'{body}<span class="frame-foot">{ROMAN[i]} · {esc(en)}</span></div>')
    return (
        f'<section class="chapter" id="{key}">'
        f'<header class="ch-head"><span class="ch-num {accent}">{ROMAN[i]}</span>'
        f'{suit(icon, "big " + accent)}<h2>{esc(title)}</h2><span class="ch-en">{esc(en)}</span></header>'
        f'{"".join(frames)}</section>')


def first_tagline(data):
    """카드에 쓸 짧은 한 줄: 짧은 img 필드 (총운풀이가 아니면 소제목을 붙인다)."""
    found = []

    def walk(n):
        if isinstance(n, dict):
            img = n.get("img")
            if isinstance(img, str) and 0 < len(img.strip()) <= 22:
                title = n.get("title", "")
                found.append(img if title in ("", "총운풀이") else f"{title} · {img}")
            for v in n.values():
                walk(v)
    walk(data)
    return found[0] if found else ""


def render_deck(result):
    cards = []
    for i, (key, en, icon, accent) in enumerate(CHAPTERS):
        data = result.get(key)
        if not data:
            continue
        title = next(iter(data.values())).get("title", "")
        cards.append(
            f'<a class="card {accent}" href="#{key}">'
            f'<span class="corner tl">{ROMAN[i]}{suit(icon, "mini")}</span>'
            f'<span class="corner br">{ROMAN[i]}{suit(icon, "mini")}</span>'
            f'<span class="card-art">{suit(icon, "card-suit")}</span>'
            f'<span class="card-name">{esc(title)}</span>'
            f'<span class="card-en">{esc(en)}</span>'
            f'<span class="card-tag">{esc(first_tagline(data))}</span></a>')
    return "".join(cards)


def profile_values(doc):
    """저장된 프로필 -> 입력 폼 기본값."""
    p = doc["profile"]
    unknown = p["birthTime"] == "00" and p["birthMinute"] == "00"
    return {
        "name": p["name"],
        "birth": f'{int(p["birthYear"]):04d}-{int(p["birthMonth"]):02d}-{int(p["birthDay"]):02d}',
        "calendar": "solar" if p["calendarType"] == 0 else "lunar",
        "leap": "1" if p["isLeapMonth"] else "",
        "time": "" if unknown else f'{p["birthTime"]}:{p["birthMinute"]}',
        "unknown": "1" if unknown else "",
        "gender": "male" if p["gender"] == "0" else "female",
        "year": str(doc["year"]),
    }


def build(src):
    """결과 JSON -> 정적 HTML 파일 (입력 폼 없음)."""
    doc = json.loads(pathlib.Path(src).read_text(encoding="utf-8"))
    out = pathlib.Path(src).with_suffix(".html")
    out.write_text(render_page(doc), encoding="utf-8")
    return out


def render_page(doc, form=False):
    """결과 페이지 HTML. form=True 면 '사주 변경' 폼을 넣는다 (app.py 에서 사용)."""
    p, year, result = doc["profile"], int(doc["year"]), doc["result"]
    ganji = STEMS[(year - 4) % 10] + BRANCHES[(year - 4) % 12]
    color, animal = STEM_COLORS[(year - 4) % 10], (year - 4) % 12
    zodiac = f"{color} {ANIMALS[animal]}"
    zodiac_en = f"YEAR OF THE {COLORS_EN[color]} {ANIMALS_EN[animal]}"
    cal = "양력" if p["calendarType"] == 0 else ("음력 윤달" if p["isLeapMonth"] else "음력")
    birth = f'{p["birthYear"]}.{int(p["birthMonth"]):02d}.{int(p["birthDay"]):02d} {cal}'
    btime = "시간 모름" if p["birthTime"] == "00" and p["birthMinute"] == "00" else f'{p["birthTime"]}:{p["birthMinute"]}'
    gender = "남" if p["gender"] == "0" else "여"

    total = (result.get("Total") or {}).get("menu2", {}).get("category1", {})
    advice = total.get("depth4", {}).get("text", "")
    best = total.get("depth2", {}).get("img", "")
    care = total.get("depth3", {}).get("img", "")

    chapters = "".join(
        render_chapter(i, key, en, icon, accent, result[key])
        for i, (key, en, icon, accent) in enumerate(CHAPTERS) if result.get(key))

    page = TEMPLATE
    for k, v in {
        "{{YEAR}}": str(year), "{{GANJI}}": ganji, "{{ZODIAC}}": zodiac, "{{ZODIAC_EN}}": zodiac_en, "{{NAME}}": esc(p["name"]),
        "{{BIRTH}}": esc(birth), "{{BTIME}}": esc(btime), "{{GENDER}}": gender,
        "{{BEST}}": esc(best), "{{CARE}}": esc(care), "{{ADVICE}}": paragraphs(advice),
        "{{DECK}}": render_deck(result), "{{CHAPTERS}}": chapters,
        "{{CHANGE}}": (
            '<details class="change"><summary>사주 변경 ✦</summary>'
            f'{render_form(values=profile_values(doc), band=False, title="사주 정보 변경")}</details>') if form else "",
        "/*{{FORM_CSS}}*/": FORM_CSS if form else "",
        "{{FORM_JS}}": FORM_JS if form else "",
    }.items():
        page = page.replace(k, v)
    return page


TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{YEAR}} 신년운세 · {{NAME}}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Gloock&family=Song+Myung&family=Gowun+Dodum&family=Oswald:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#070607; --bg2:#0e0c0d; --ink:#efe6d2; --muted:#a39985;
  --pink:#f0668c; --green:#72d96a; --gold:#c9a24e; --gold-dim:#5d4a22;
  --display:"Gloock",serif; --kr-display:"Song Myung",serif;
  --body:"Gowun Dodum",sans-serif; --label:"Oswald",sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  background:var(--bg); color:var(--ink); font-family:var(--body);
  font-size:16.5px; line-height:1.85; overflow-x:hidden;
}
/* 필름 그레인 */
body::before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:100; opacity:.16; mix-blend-mode:screen;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='220'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 .8 0 0 0 0 .7 0 0 0 0 .9 0 0 0 1.4 -.55'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
a{color:inherit;text-decoration:none}
.pink{color:var(--pink)} .green{color:var(--green)} .gold{color:var(--gold)}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}

/* 상단 바 */
.topbar{
  position:sticky; top:0; z-index:50; display:flex; justify-content:space-between; align-items:center;
  padding:12px 24px; font-family:var(--label); font-size:12px; letter-spacing:.32em; text-transform:uppercase;
  color:var(--gold); background:linear-gradient(var(--bg) 60%,transparent);
}
.topbar nav{display:flex; gap:18px}
.topbar nav a:hover{color:var(--green)}

/* 히어로 */
.hero{position:relative; text-align:center; padding:72px 0 40px; isolation:isolate}
.hero::before{
  content:""; position:absolute; z-index:-1; left:50%; top:52%; width:min(760px,120vw); height:420px;
  transform:translate(-50%,-50%); filter:blur(70px); opacity:.33;
  background:radial-gradient(closest-side,var(--green),transparent 70%),
             radial-gradient(closest-side at 70% 60%,var(--pink),transparent 70%);
  animation:aura 9s ease-in-out infinite alternate;
}
@keyframes aura{to{transform:translate(-46%,-54%) scale(1.12) rotate(8deg)}}
.emblem{width:92px; height:auto; margin:0 auto 26px; display:block}
.emblem .line{fill:none; stroke:var(--gold); stroke-width:1.6}
.emblem .s1{fill:var(--pink)} .emblem .s2{fill:var(--green)}
.twinkle{animation:tw 2.6s ease-in-out infinite} .twinkle:nth-of-type(2n){animation-delay:1.1s}
@keyframes tw{50%{opacity:.25}}
.hero-ganji{font-family:var(--kr-display); color:var(--gold); letter-spacing:.6em; font-size:15px; margin-bottom:8px; padding-left:.6em}
.hero-title{
  font-family:var(--display); font-size:clamp(64px,13vw,150px); line-height:.9; color:var(--ink);
  transform:perspective(500px) rotateX(14deg); text-shadow:0 0 40px rgba(114,217,106,.18);
}
.hero-duo{display:flex; justify-content:center; gap:clamp(16px,4vw,46px); margin-top:22px; flex-wrap:wrap}
.hero-duo div{display:flex; flex-direction:column; align-items:center}
.hero-duo strong{font-family:var(--kr-display); font-weight:400; font-size:clamp(30px,5.5vw,52px); letter-spacing:.32em; padding-left:.32em; line-height:1.2}
.hero-duo small{font-family:var(--label); font-size:clamp(11px,1.6vw,15px); letter-spacing:.45em; padding-left:.45em}
.hero-who{
  display:inline-flex; flex-wrap:wrap; justify-content:center; gap:6px 22px; margin-top:34px; padding:10px 26px;
  border:1px solid var(--gold-dim); border-radius:999px; font-size:14.5px; color:var(--muted);
}
.hero-who b{color:var(--ink); font-weight:400}

/* 금색 도트 띠 */
.band{
  height:46px; margin:34px 0;
  background:radial-gradient(circle,var(--gold) .9px,transparent 1.3px) 0 0/7px 7px;
  -webkit-mask:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent);
          mask:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent);
  opacity:.55;
}

/* 프레임 */
.frame{
  position:relative; margin:44px 0 0; padding:44px clamp(20px,4vw,48px) 40px;
  border:2px dotted var(--gold); border-radius:26px;
  box-shadow:inset 0 0 0 6px var(--bg), inset 0 0 0 7px var(--gold-dim);
  background:linear-gradient(180deg,rgba(201,162,78,.04),transparent 40%);
}
.frame-title,.frame-foot{
  position:absolute; left:50%; transform:translateX(-50%); white-space:nowrap; background:var(--bg);
  padding:0 18px;
}
.frame-title{top:-.85em; font-family:var(--kr-display); font-size:clamp(19px,2.6vw,24px); letter-spacing:.42em; padding-left:calc(18px + .42em)}
.frame-foot{bottom:-.8em; font-family:var(--label); font-size:12px; letter-spacing:.42em; color:var(--gold)}

/* 인트로 */
.intro{display:grid; grid-template-columns:1fr auto 1fr; gap:34px; align-items:center}
.intro .stat{text-align:center}
.intro .stat span{display:block; font-family:var(--label); font-size:12px; letter-spacing:.4em; color:var(--muted)}
.intro .stat strong{display:block; font-family:var(--kr-display); font-weight:400; font-size:clamp(26px,4vw,38px); letter-spacing:.12em}
.intro .door{width:62px}
.advice{margin-top:30px; text-align:center; color:var(--ink); word-break:keep-all; max-width:720px; margin-inline:auto}
.advice p+p{margin-top:.8em}

/* 카드 덱 */
.deck-head{text-align:center; margin-top:84px}
.deck-head h3{font-family:var(--kr-display); font-weight:400; font-size:clamp(22px,3vw,28px); letter-spacing:.45em; color:var(--pink); padding-left:.45em}
.deck-head p{font-family:var(--label); letter-spacing:.42em; font-size:12px; color:var(--green); margin-top:4px}
.deck{display:grid; grid-template-columns:repeat(auto-fill,minmax(168px,1fr)); gap:18px; margin-top:34px}
.card{
  position:relative; aspect-ratio:5/7.4; border-radius:16px; padding:16px; overflow:hidden;
  display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:4px;
  background:
    repeating-radial-gradient(circle at 50% 50%,transparent 0 9px,rgba(201,162,78,.10) 9px 10px),
    linear-gradient(160deg,#141012,#070607);
  border:1px solid var(--gold-dim);
  box-shadow:inset 0 0 0 7px #0b090a, inset 0 0 0 8px rgba(201,162,78,.55);
  transition:transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s;
}
.card:hover,.card:focus-visible{transform:translateY(-8px) rotate(-1.2deg); outline:none;
  box-shadow:inset 0 0 0 7px #0b090a, inset 0 0 0 8px var(--gold), 0 18px 40px -12px rgba(114,217,106,.45)}
.card.pink:hover{box-shadow:inset 0 0 0 7px #0b090a, inset 0 0 0 8px var(--gold), 0 18px 40px -12px rgba(240,102,140,.5)}
.corner{position:absolute; display:flex; flex-direction:column; align-items:center; font-family:var(--display); font-size:13px; line-height:1.1; color:currentColor}
.corner.tl{top:16px; left:17px} .corner.br{bottom:16px; right:17px; transform:rotate(180deg)}
.card-art{display:grid; place-items:center; width:74px; height:74px; border-radius:50%; margin-bottom:10px;
  border:1px solid currentColor; box-shadow:0 0 0 6px #0b090a, 0 0 0 7px var(--gold-dim)}
.card-name{font-family:var(--kr-display); font-size:22px; color:var(--ink); letter-spacing:.18em; padding-left:.18em}
.card-en{font-family:var(--label); font-size:10.5px; letter-spacing:.38em; color:var(--gold)}
.card-tag{font-size:12.5px; color:var(--muted); line-height:1.5; margin-top:8px; min-height:2.9em; word-break:keep-all}

/* 아이콘 */
.suit{fill:currentColor; stroke:currentColor; stroke-width:0; flex:none}
.suit.tiny{width:12px; height:12px} .suit.mini{width:11px; height:11px; margin-top:2px}
.suit.card-suit{width:34px; height:34px} .suit.big{width:30px; height:30px}
.suit [fill="none"]{stroke-width:inherit}
.suit circle[fill="none"],.suit path[fill="none"]{stroke-width:1.8}

/* 챕터 */
.chapter{padding-top:96px; scroll-margin-top:30px}
.ch-head{display:grid; justify-items:center; text-align:center; gap:6px}
.ch-num{font-family:var(--display); font-size:15px; letter-spacing:.3em}
.ch-head h2{font-family:var(--kr-display); font-weight:400; font-size:clamp(40px,7vw,68px); letter-spacing:.3em; padding-left:.3em; line-height:1.15}
.ch-en{font-family:var(--label); font-size:12px; letter-spacing:.5em; color:var(--gold); padding-left:.5em}
.sub{display:flex; align-items:center; gap:10px; font-family:var(--kr-display); font-weight:400; font-size:21px; letter-spacing:.14em; margin-bottom:14px}
.tagline{
  font-family:var(--kr-display); font-size:clamp(21px,2.8vw,27px); line-height:1.5; text-align:center; word-break:keep-all;
  margin:4px auto 22px; max-width:760px;
}
.tagline::before,.tagline::after{content:"✦"; font-size:.55em; vertical-align:middle; margin:0 .8em; color:var(--gold)}
.prose{column-count:2; column-gap:44px; column-rule:1px solid rgba(201,162,78,.22); word-break:keep-all}
.prose p{margin-bottom:.9em; break-inside:avoid-column}
.prose:has(p:only-child){column-count:1; max-width:760px; margin-inline:auto}
.divider{text-align:center; color:var(--gold); font-size:12px; margin:26px 0; letter-spacing:1em; opacity:.8}
.divider::before,.divider::after{content:""; display:inline-block; width:min(140px,25vw); height:1px; background:var(--gold-dim); vertical-align:middle; margin:0 14px}

/* 포인트 */
.points{list-style:none; display:grid; grid-template-columns:repeat(2,1fr); gap:14px}
.pt{display:flex; gap:16px; padding:18px 20px; border:1px solid rgba(201,162,78,.32); border-radius:14px; background:rgba(255,255,255,.015); word-break:keep-all}
.pt-idx{display:flex; flex-direction:column; align-items:center; gap:4px; padding-top:4px}
.pt-idx .suit{width:18px; height:18px}
.pt-idx b{font-family:var(--display); font-weight:400; font-size:13px; color:var(--gold)}
.pt p{font-size:15.5px; line-height:1.75}

/* 점수 */
.scores{list-style:none; display:grid; gap:12px; max-width:640px; margin:0 auto 30px}
.scores li{display:grid; grid-template-columns:90px 1fr 44px; align-items:center; gap:16px}
.sc-label{font-family:var(--kr-display); letter-spacing:.1em}
.sc-track{height:9px; border-radius:9px; border:1px solid var(--gold-dim); padding:1px}
.sc-fill{display:block; height:100%; width:var(--v); border-radius:9px; background:linear-gradient(90deg,var(--pink),var(--green));
  box-shadow:0 0 14px rgba(114,217,106,.45); transform-origin:left; animation:grow 1.4s cubic-bezier(.2,.8,.2,1) both}
@keyframes grow{from{transform:scaleX(0)}}
.sc-num{font-family:var(--display); font-size:22px; color:var(--ink); text-align:right}

/* 푸터 */
footer{text-align:center; padding:110px 0 70px}
.merci{display:flex; justify-content:center; align-items:center; gap:clamp(18px,6vw,70px); font-family:var(--label); letter-spacing:.8em; font-size:14px}
.merci svg{width:56px}
.merci span{white-space:nowrap}
footer small{display:block; margin-top:30px; color:var(--muted); font-size:12.5px; letter-spacing:.06em}

@media (max-width:760px){
  .topbar nav{display:none}
  .intro{grid-template-columns:1fr; gap:18px}
  .prose{column-count:1}
  .points{grid-template-columns:1fr}
  .deck{grid-template-columns:repeat(2,1fr); gap:12px}
  .wrap{padding:0 16px}
  .frame-title{letter-spacing:.2em; padding-left:calc(18px + .2em)}
  .scores li{grid-template-columns:76px 1fr 36px; gap:10px}
  .merci{letter-spacing:.35em; font-size:13px}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important; transition:none!important}}
/*{{FORM_CSS}}*/
</style>
</head>
<body>
<div class="topbar">
  <a href="index.html">← 목록 · {{GANJI}}년 신년운세</a>
  <nav><a href="#deck">Deck</a><a href="#Total">The Year</a><a href="#ReviewYear">Preview</a></nav>
</div>

<main class="wrap">
  <section class="hero">
    <svg class="emblem" viewBox="0 0 100 130" aria-hidden="true">
      <path class="line" d="M14 124V54a36 36 0 0 1 72 0v70z"/>
      <path class="line" d="M22 124V56a28 28 0 0 1 56 0v68"/>
      <path class="line" d="M36 124v-10h14v-10h14v-10h14"/>
      <path class="s1 twinkle" d="M40 42c.5 4 2 5.5 6 6-4 .5-5.5 2-6 6-.5-4-2-5.5-6-6 4-.5 5.5-2 6-6z"/>
      <path class="s2 twinkle" d="M62 58c.4 3 1.5 4 4.5 4.5-3 .4-4.1 1.5-4.5 4.5-.4-3-1.5-4.1-4.5-4.5 3-.5 4.1-1.5 4.5-4.5z"/>
      <circle class="s2 twinkle" cx="56" cy="34" r="1.6"/><circle class="s1 twinkle" cx="34" cy="68" r="1.4"/>
      <circle class="s1" cx="66" cy="80" r="1.2"/><circle class="s2" cx="44" cy="86" r="1.2"/>
    </svg>
    <p class="hero-ganji">{{GANJI}}년</p>
    <h1 class="hero-title">{{YEAR}}</h1>
    <div class="hero-duo">
      <div class="pink"><strong>신년운세</strong><small>NEW YEAR FORTUNE</small></div>
      <div class="green"><strong>{{ZODIAC}}의 해</strong><small>{{ZODIAC_EN}}</small></div>
    </div>
    <p class="hero-who"><span><b>{{NAME}}</b></span><span>{{BIRTH}}</span><span>{{BTIME}}</span><span>{{GENDER}}</span></p>
    {{CHANGE}}
  </section>

  <div class="band"></div>

  <div class="frame">
    <span class="frame-title pink">올해의 흐름</span>
    <div class="intro">
      <div class="stat"><span>BEST</span><strong class="green">{{BEST}}</strong></div>
      <svg class="door" viewBox="0 0 100 130" aria-hidden="true"><path d="M14 124V54a36 36 0 0 1 72 0v70z" fill="none" stroke="#c9a24e" stroke-width="2"/><path d="M36 124v-10h14v-10h14v-10h14" fill="none" stroke="#c9a24e" stroke-width="2"/><path fill="#f0668c" d="M40 42c.5 4 2 5.5 6 6-4 .5-5.5 2-6 6-.5-4-2-5.5-6-6 4-.5 5.5-2 6-6z"/><path fill="#72d96a" d="M62 58c.4 3 1.5 4 4.5 4.5-3 .4-4.1 1.5-4.5 4.5-.4-3-1.5-4.1-4.5-4.5 3-.5 4.1-1.5 4.5-4.5z"/></svg>
      <div class="stat"><span>CAUTION</span><strong class="pink">{{CARE}}</strong></div>
    </div>
    <div class="advice">{{ADVICE}}</div>
    <span class="frame-foot green">ADVICE OF THE YEAR</span>
  </div>

  <div class="deck-head" id="deck">
    <h3>운세 카드 덱</h3>
    <p>{{YEAR}} FORTUNE CARD DECK</p>
  </div>
  <nav class="deck">{{DECK}}</nav>

  {{CHAPTERS}}
</main>

<footer class="wrap">
  <div class="band"></div>
  <div class="merci">
    <span class="pink">감사합니다</span>
    <svg viewBox="0 0 100 130" aria-hidden="true"><path d="M14 124V54a36 36 0 0 1 72 0v70z" fill="none" stroke="#72d96a" stroke-width="3"/><path d="M36 124v-10h14v-10h14v-10h14" fill="none" stroke="#72d96a" stroke-width="3"/></svg>
    <span class="green">THANK YOU</span>
  </div>
  <small>운세 데이터 출처: 점신(jeomsin.co.kr) · Firecrawl로 수집 · 개인 열람용</small>
</footer>
{{FORM_JS}}
</body>
</html>
"""

CSS = re.search(r"<style>(.*?)</style>", TEMPLATE, re.S).group(1)
EMBLEM = re.search(r'<svg class="emblem".*?</svg>', TEMPLATE, re.S).group(0)
FOOTER = re.search(r"<footer.*?</footer>", TEMPLATE, re.S).group(0)


FORM_CSS = """
.fortune-form{margin-top:10px}
.fields{display:grid; grid-template-columns:repeat(2,1fr); gap:22px 34px}
.field{display:grid; gap:8px}
.field>span{font-family:var(--label); font-size:12px; letter-spacing:.38em; color:var(--gold)}
.fortune-form input[type=text],.fortune-form input[type=date],.fortune-form input[type=time]{
  width:100%; padding:12px 14px; border-radius:10px; border:1px solid var(--gold-dim); background:#0d0b0c;
  color:var(--ink); font:inherit; color-scheme:dark;
}
.fortune-form input:focus-visible{outline:none; border-color:var(--green); box-shadow:0 0 0 3px rgba(114,217,106,.18)}
.fortune-form input[type=time]:disabled{opacity:.35}
.seg{display:flex; gap:8px; flex-wrap:wrap; align-items:center}
.seg input[type=time]{flex:1; min-width:130px}
.seg label{position:relative; cursor:pointer}
.seg label input{position:absolute; opacity:0; inset:0; cursor:pointer}
.seg label b{display:block; font-weight:400; padding:10px 18px; border-radius:999px; border:1px solid var(--gold-dim); color:var(--muted); transition:.2s}
.seg label input:checked+b{border-color:var(--pink); color:var(--ink); background:rgba(240,102,140,.12)}
.seg label input:focus-visible+b{box-shadow:0 0 0 3px rgba(240,102,140,.3)}
.seg label input:disabled+b{opacity:.3; cursor:not-allowed}
.draw{display:block; margin:34px auto 6px; padding:16px 46px; border-radius:999px; cursor:pointer;
  font-family:var(--kr-display); font-size:20px; letter-spacing:.3em; color:#0b090a;
  background:linear-gradient(90deg,var(--pink),var(--green)); border:0; box-shadow:0 10px 34px -10px rgba(114,217,106,.6);
  transition:transform .2s}
.draw:hover{transform:translateY(-2px)}
.form-error{text-align:center; color:var(--pink); margin-bottom:22px}
.loading{position:fixed; inset:0; z-index:90; display:grid; place-content:center; justify-items:center; gap:10px;
  background:rgba(7,6,7,.92); text-align:center}
.loading[hidden]{display:none}
.loading .emblem{animation:float 2.4s ease-in-out infinite}
.loading p{font-family:var(--kr-display); font-size:26px; letter-spacing:.3em}
.loading small{color:var(--muted)}
@keyframes float{50%{transform:translateY(-10px)}}
.change{margin-top:22px}
.change summary{list-style:none; display:inline-block; cursor:pointer; padding:9px 24px; border-radius:999px;
  border:1px solid var(--pink); color:var(--pink); font-family:var(--kr-display); letter-spacing:.2em; transition:.2s}
.change summary::-webkit-details-marker{display:none}
.change summary:hover,.change summary:focus-visible{outline:none; background:rgba(240,102,140,.12); color:var(--ink)}
.change[open] summary{background:rgba(240,102,140,.12); color:var(--ink)}
.change .fortune-form{text-align:left; margin-top:46px}
@media (max-width:760px){.fields{grid-template-columns:1fr}}
"""

FORM_JS = """
<script>
(function(){
  var f = document.querySelector('.fortune-form'); if (!f) return;
  var t = f.elements.time, u = f.elements.unknown, leap = f.elements.leap;
  function sync(){
    t.disabled = u.checked; if (u.checked) t.value = '';
    var lunar = f.querySelector('input[name=calendar]:checked').value === 'lunar';
    leap.disabled = !lunar; if (!lunar) leap.checked = false;
  }
  f.addEventListener('change', sync); sync();
  f.addEventListener('submit', function(){
    document.querySelector('.loading').hidden = false;
    f.querySelector('.draw').disabled = true;
  });
})();
</script>
"""


def render_form(error="", values=None, band=True, title="새 카드 뽑기"):
    v = {k: esc(x) for k, x in (values or {}).items()}
    chk = lambda cond: " checked" if cond else ""
    lunar, female = v.get("calendar") == "lunar", v.get("gender") == "female"
    year = v.get("year") or str(datetime.date.today().year)
    err = f'<p class="form-error">{esc(error)}</p>' if error else ""
    return f"""
  <form class="frame fortune-form" method="post" action="/make">
    <span class="frame-title green">{title}</span>
    {err}
    <div class="fields">
      <label class="field"><span>이름</span><input type="text" name="name" required maxlength="20" placeholder="홍길동" value="{v.get('name', '')}"></label>
      <label class="field"><span>생년월일</span><input type="date" name="birth" required min="1900-01-01" max="2099-12-31" value="{v.get('birth', '')}"></label>
      <div class="field"><span>양력 · 음력</span><div class="seg">
        <label><input type="radio" name="calendar" value="solar"{chk(not lunar)}><b>양력</b></label>
        <label><input type="radio" name="calendar" value="lunar"{chk(lunar)}><b>음력</b></label>
        <label><input type="checkbox" name="leap" value="1"{chk(v.get('leap'))}><b>윤달</b></label></div></div>
      <div class="field"><span>태어난 시간</span><div class="seg">
        <input type="time" name="time" value="{v.get('time', '')}">
        <label><input type="checkbox" name="unknown" value="1"{chk(v.get('unknown') or not v)}><b>모름</b></label></div></div>
      <div class="field"><span>성별</span><div class="seg">
        <label><input type="radio" name="gender" value="male"{chk(not female)}><b>남</b></label>
        <label><input type="radio" name="gender" value="female"{chk(female)}><b>여</b></label></div></div>
      <div class="field"><span>운세 연도</span><div class="seg"><label><input type="radio" name="year" value="{year}" checked><b>{year}년</b></label></div></div>
    </div>
    <button class="draw" type="submit">카드 뽑기 ✦</button>
    <span class="frame-foot">DRAW A NEW CARD</span>
  </form>
  <div class="loading" hidden>{EMBLEM}<p>카드를 섞는 중</p><small>점신에서 운세를 가져오고 있어요 · 30초 정도 걸려요</small></div>
  {'<div class="band"></div>' if band else ""}"""


def build_index(out_dir):
    """out_dir 안의 모든 결과 JSON을 카드로 모은 index.html 생성 (입력 폼 없는 정적 버전)."""
    out = pathlib.Path(out_dir) / "index.html"
    out.write_text(render_index(out_dir), encoding="utf-8")
    return out


def render_index(out_dir, form=False, error="", values=None):
    """목록 페이지 HTML. form=True 면 새 사람 입력 폼을 함께 넣는다 (app.py 에서 사용)."""
    out_dir = pathlib.Path(out_dir)
    files = sorted(out_dir.glob("newyear_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    cards, years = [], set()
    for i, f in enumerate(files):
        doc = json.loads(f.read_text(encoding="utf-8"))
        p, year = doc["profile"], int(doc["year"])
        years.add(year)
        ganji = STEMS[(year - 4) % 10] + BRANCHES[(year - 4) % 12]
        total = doc["result"].get("Total", {}).get("menu2", {}).get("category1", {})
        best = total.get("depth2", {}).get("img", "")
        care = total.get("depth3", {}).get("img", "")
        icon, accent = [("sparkle", "pink"), ("diamond", "green"), ("heart", "pink"), ("club", "green")][i % 4]
        cal = "양력" if p["calendarType"] == 0 else "음력"
        birth = f'{p["birthYear"]}.{int(p["birthMonth"]):02d}.{int(p["birthDay"]):02d} {cal}'
        num = ROMAN[i] if i < len(ROMAN) else str(i + 1)
        cards.append(
            f'<a class="card {accent}" href="{html.escape(f.with_suffix(".html").name)}">'
            f'<span class="corner tl">{num}{suit(icon, "mini")}</span>'
            f'<span class="corner br">{num}{suit(icon, "mini")}</span>'
            f'<span class="card-art">{suit(icon, "card-suit")}</span>'
            f'<span class="card-name">{esc(p["name"])}</span>'
            f'<span class="card-en">{year} · {ganji}년</span>'
            f'<span class="card-tag">{esc(birth)}<br>'
            f'<span class="green">{esc(best)}</span> · <span class="pink">{esc(care)}</span></span></a>')
    yrs = sorted(years)
    year_label = (f"{yrs[0]}" if len(yrs) == 1 else f"{yrs[0]}–{yrs[-1]}") if yrs else str(datetime.date.today().year)
    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>신년운세 보관함</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Gloock&family=Song+Myung&family=Gowun+Dodum&family=Oswald:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}{FORM_CSS if form else ""}</style>
</head>
<body>
<div class="topbar"><span>신년운세 · ARCHIVE</span></div>
<main class="wrap">
  <section class="hero">
    {EMBLEM}
    <p class="hero-ganji">FORTUNE ARCHIVE</p>
    <h1 class="hero-title">{year_label}</h1>
    <div class="hero-duo">
      <div class="pink"><strong>신년운세</strong><small>NEW YEAR FORTUNE</small></div>
      <div class="green"><strong>{len(files)}장의 카드</strong><small>PEOPLE IN THE DECK</small></div>
    </div>
  </section>
  <div class="band"></div>
  {render_form(error, values) if form else ""}
  <div class="deck-head" id="deck">
    <h3>운세 카드 덱</h3>
    <p>CHOOSE YOUR CARD</p>
  </div>
  <nav class="deck">{"".join(cards)}</nav>
</main>
{FOOTER}
{FORM_JS if form else ""}
</body>
</html>
"""
    return page


if __name__ == "__main__":
    # 인자가 없으면 output 폴더의 모든 결과를 다시 만든다
    targets = sys.argv[1:] or [str(f) for f in sorted((pathlib.Path(__file__).resolve().parent / "output").glob("newyear_*.json"))]
    if not targets:
        sys.exit("사용법: python build_site.py [결과 json ...]")
    for t in targets:
        print(f"생성 완료: {build(t)}")
    print(f"목록 페이지: {build_index(pathlib.Path(targets[0]).parent)}")
