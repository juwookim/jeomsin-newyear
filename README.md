# 신년운세 카드 덱

점신(jeomsin.co.kr) 신년운세를 Firecrawl로 수집해 카드 덱 스타일 페이지로 만드는 도구입니다.
`output/` 폴더가 GitHub Pages로 배포됩니다.

## 준비

`.env` 파일에 Firecrawl API 키를 넣습니다 (저장소에는 올라가지 않습니다).

```
FIRECRAWL_API_KEY=fc-...
```

## 새 사람 추가

```
python app.py                # 브라우저 입력 폼 (http://127.0.0.1:8000)
python jeomsin_newyear.py    # 터미널에서 하나씩 입력
```

생성된 결과를 커밋·푸시하면 GitHub Pages에 반영됩니다.

## 사이트에서 바로 입력받기 (Cloudflare Worker)

GitHub Pages 사이트의 입력 폼은 Cloudflare Worker(`worker/worker.js`)를 거쳐 운세를 가져옵니다.
Firecrawl 키는 Worker 비밀값으로만 저장되고 사이트에는 노출되지 않습니다.

1. Cloudflare 무료 계정을 만들고 API 토큰을 발급합니다 (My Profile > API Tokens > 'Edit Cloudflare Workers' 템플릿).
2. `.env` 에 `CLOUDFLARE_API_TOKEN=...` 을 추가합니다.
3. `python deploy_worker.py` 를 실행합니다. Worker 주소가 `site_config.json` 에 저장되고 `output/` 페이지에 입력 폼이 들어갑니다.
4. 커밋·푸시하면 사이트에서 바로 사주 정보를 입력할 수 있습니다.

Worker 는 사이트 주소(`ALLOWED_ORIGINS`)에서 온 요청만 받고, IP 당 1분에 2회로 호출을 제한합니다.

운세 데이터 출처: 점신(jeomsin.co.kr) · 개인 열람용
