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
입력 폼은 Firecrawl 키가 필요해서 내 PC에서만 동작합니다.

운세 데이터 출처: 점신(jeomsin.co.kr) · 개인 열람용
