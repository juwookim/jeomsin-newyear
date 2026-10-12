"""신년운세 웹앱 (내 PC에서 실행).

브라우저에서 이름·생년월일 등을 입력하면 Firecrawl로 점신 신년운세를 가져와
결과 페이지를 만들어 보여준다. Firecrawl API 키는 서버(.env)에만 있고 브라우저로 나가지 않는다.

실행:
  python app.py            -> http://127.0.0.1:8000 이 자동으로 열린다
  python app.py --port 8080 --no-browser
"""
import argparse
import json
import pathlib
import threading
import urllib.parse
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import build_site
from jeomsin_newyear import make_fortune

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "output"
LOCK = threading.Lock()  # Firecrawl 호출과 파일 쓰기는 한 번에 하나씩


class Handler(SimpleHTTPRequestHandler):
    def send_html(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        if path in ("/", "/index.html"):
            return self.send_html(build_site.render_index(OUT, form=True))
        # 결과 페이지는 '사주 변경' 폼을 넣어서 보여준다
        src = (OUT / path.lstrip("/")).with_suffix(".json")
        if path.startswith("/newyear_") and path.endswith(".html") and src.parent == OUT and src.is_file():
            doc = json.loads(src.read_text(encoding="utf-8"))
            return self.send_html(build_site.render_page(doc, form=True))
        return super().do_GET()

    def do_POST(self):
        if self.path != "/make":
            return self.send_error(404)
        length = min(int(self.headers.get("Content-Length") or 0), 10_000)
        form = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8")).items()}
        try:
            with LOCK:
                page = make_fortune(
                    name=form.get("name", ""), birth=form.get("birth", ""),
                    time="" if form.get("unknown") else form.get("time", ""),
                    calendar=form.get("calendar", "solar"), leap=bool(form.get("leap")),
                    gender=form.get("gender", "male"), year=form.get("year", "2026"), out=OUT)
        except (ValueError, RuntimeError) as e:
            return self.send_html(build_site.render_index(OUT, form=True, error=str(e), values=form), 400)
        self.send_response(303)
        self.send_header("Location", "/" + urllib.parse.quote(page.name))
        self.end_headers()


def main():
    ap = argparse.ArgumentParser(description="신년운세 웹앱")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", a.port), partial(Handler, directory=str(OUT)))
    url = f"http://127.0.0.1:{a.port}/"
    print(f"신년운세 웹앱 실행 중: {url}  (종료: Ctrl+C)")
    if not a.no_browser:
        threading.Timer(0.8, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
