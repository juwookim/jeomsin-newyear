"""worker/worker.js 를 Cloudflare Workers 에 배포하고 사이트 입력 폼을 켠다.

준비: .env 에 Cloudflare API 토큰을 추가한다 ('Edit Cloudflare Workers' 템플릿으로 만든 토큰).
  CLOUDFLARE_API_TOKEN=...
  CLOUDFLARE_ACCOUNT_ID=...   (선택, 없으면 토큰의 첫 번째 계정)

하는 일:
  1. Worker 업로드 (Firecrawl 키는 secret 으로, 허용 사이트 주소, IP 당 분당 2회 제한)
  2. workers.dev 주소 활성화
  3. site_config.json 에 Worker 주소 저장 -> output/ 페이지를 입력 폼 포함으로 다시 생성

사용:
  python deploy_worker.py
  python deploy_worker.py --origin https://juwookim.github.io --name jeomsin-fortune
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
import uuid

HERE = pathlib.Path(__file__).resolve().parent
API = "https://api.cloudflare.com/client/v4"


def env_value(name):
    text = (HERE / ".env").read_text(encoding="utf-8")
    m = re.search(rf"^\s*{name}\s*=\s*(\S+)", text, re.M)
    return m.group(1).strip("\"'") if m else ""


def firecrawl_key():
    m = re.search(r"fc-[A-Za-z0-9]+", (HERE / ".env").read_text(encoding="utf-8"))
    if not m:
        sys.exit(".env 에서 Firecrawl API 키(fc-...)를 찾지 못했습니다.")
    return m.group(0)


def cf(token, method, path, body=None, content_type="application/json"):
    data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": content_type})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except ValueError:
            return {"success": False, "errors": [{"message": f"HTTP {e.code}"}]}


def errors(res):
    return "; ".join(e.get("message", "") for e in res.get("errors") or []) or "알 수 없는 오류"


def upload(token, account, name, metadata):
    boundary = uuid.uuid4().hex
    script = (HERE / "worker" / "worker.js").read_bytes()
    parts = [
        (f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"; filename="metadata.json"\r\n'
         'Content-Type: application/json\r\n\r\n').encode() + json.dumps(metadata).encode() + b"\r\n",
        (f'--{boundary}\r\nContent-Disposition: form-data; name="worker.js"; filename="worker.js"\r\n'
         'Content-Type: application/javascript+module\r\n\r\n').encode() + script + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return cf(token, "PUT", f"/accounts/{account}/workers/scripts/{name}", b"".join(parts),
              f"multipart/form-data; boundary={boundary}")


def main():
    ap = argparse.ArgumentParser(description="신년운세 Worker 배포")
    ap.add_argument("--name", default="jeomsin-fortune", help="Worker 이름")
    ap.add_argument("--origin", default="https://juwookim.github.io", help="입력 폼을 둘 사이트 주소 (쉼표로 여러 개)")
    ap.add_argument("--subdomain", default="", help="workers.dev 하위 도메인이 없을 때 새로 만들 이름")
    a = ap.parse_args()

    token = env_value("CLOUDFLARE_API_TOKEN")
    if not token:
        sys.exit(".env 에 CLOUDFLARE_API_TOKEN=... 을 추가하세요. (Cloudflare 대시보드 > My Profile > API Tokens > "
                 "'Edit Cloudflare Workers' 템플릿)")
    account = env_value("CLOUDFLARE_ACCOUNT_ID")
    if not account:
        res = cf(token, "GET", "/accounts")
        if not res.get("success") or not res.get("result"):
            sys.exit(f"Cloudflare 계정을 찾지 못했습니다: {errors(res)}")
        account = res["result"][0]["id"]

    bindings = [
        {"type": "secret_text", "name": "FIRECRAWL_API_KEY", "text": firecrawl_key()},
        {"type": "plain_text", "name": "ALLOWED_ORIGINS", "text": a.origin},
    ]
    limiter = {"type": "ratelimit", "name": "LIMITER", "namespace_id": "1001", "simple": {"limit": 2, "period": 60}}
    meta = {"main_module": "worker.js", "compatibility_date": "2025-01-01"}
    res = upload(token, account, a.name, {**meta, "bindings": bindings + [limiter]})
    if not res.get("success"):
        print(f"호출 제한 바인딩 없이 다시 시도합니다 ({errors(res)})")
        res = upload(token, account, a.name, {**meta, "bindings": bindings})
    if not res.get("success"):
        sys.exit(f"Worker 업로드 실패: {errors(res)}")
    print("Worker 업로드 완료")

    res = cf(token, "GET", f"/accounts/{account}/workers/subdomain")
    sub = (res.get("result") or {}).get("subdomain") if res.get("success") else None
    if not sub:
        if not a.subdomain:
            sys.exit("workers.dev 하위 도메인이 아직 없습니다. --subdomain 원하는이름 을 붙여 다시 실행하세요.")
        res = cf(token, "PUT", f"/accounts/{account}/workers/subdomain", {"subdomain": a.subdomain})
        if not res.get("success"):
            sys.exit(f"workers.dev 하위 도메인 생성 실패: {errors(res)}")
        sub = a.subdomain
    res = cf(token, "POST", f"/accounts/{account}/workers/scripts/{a.name}/subdomain",
             {"enabled": True, "previews_enabled": False})
    if not res.get("success"):
        sys.exit(f"workers.dev 주소 활성화 실패: {errors(res)}")

    api_url = f"https://{a.name}.{sub}.workers.dev/fortune"
    (HERE / "site_config.json").write_text(json.dumps({"api_url": api_url}, indent=2) + "\n", encoding="utf-8")
    print(f"Worker 주소: {api_url}")

    import build_site
    for f in sorted((HERE / "output").glob("newyear_*.json")):
        build_site.build(f)
    build_site.build_index(HERE / "output")
    print("output/ 페이지를 입력 폼 포함으로 다시 만들었습니다. git push 하면 사이트에 반영됩니다.")


if __name__ == "__main__":
    main()
