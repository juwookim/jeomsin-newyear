/* 신년운세 Cloudflare Worker.
 *
 * GitHub Pages 사이트의 입력 폼이 POST /fortune 으로 사주 정보를 보내면,
 * Firecrawl 브라우저로 점신을 열어 사이트 자체의 신년운세 요청 함수를 실행하고 결과 JSON을 돌려준다.
 * (jeomsin_newyear.py 의 scrape() 와 같은 방식)
 *
 * 필요한 설정
 *   FIRECRAWL_API_KEY  (secret)  Firecrawl API 키
 *   ALLOWED_ORIGINS    (var)     요청을 허용할 사이트 주소, 쉼표로 구분
 *   LIMITER            (선택)    rate limit 바인딩 - IP 당 호출 수 제한
 */

const FIRECRAWL_URL = "https://api.firecrawl.dev/v2/scrape";

// 점신 사이트 webpack 모듈 id (사이트가 재배포되면 바뀔 수 있음)
const MOD_KIND = 75910, MOD_NEWYEAR = 53974, NEWYEAR_CHUNKS = [7725, 4380, 4806];
const CATEGORY_KEYS = ["Saju", "Total", "Money", "Love", "Marriage", "Job", "Business", "Friend", "Health", "ReviewYear"];

class InputError extends Error {}

function buildProfile(body) {
  const name = String(body.name || "").trim();
  const birth = String(body.birth || "");
  const time = String(body.time || "");
  const calendar = body.calendar, gender = body.gender;
  const year = String(body.year || "");
  if (!name || name.length > 20) throw new InputError("이름을 1~20자로 입력하세요.");
  const m = birth.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (!m) throw new InputError("생년월일을 YYYY-MM-DD 형식으로 입력하세요.");
  if (time && !/^([01]?\d|2[0-3]):[0-5]\d$/.test(time)) throw new InputError("태어난 시간을 HH:MM 형식으로 입력하세요.");
  if (!["solar", "lunar"].includes(calendar) || !["male", "female"].includes(gender)) {
    throw new InputError("양력/음력, 성별 값을 확인하세요.");
  }
  if (!/^\d{4}$/.test(year)) throw new InputError("운세 연도를 확인하세요.");
  // 점신은 '시간 모름'을 00시 00분으로 보낸다
  const [hh, mm] = time ? time.split(":") : ["0", "0"];
  return {
    year,
    profile: {
      name, birthYear: String(+m[1]), birthMonth: String(+m[2]), birthDay: String(+m[3]),
      birthTime: String(+hh).padStart(2, "0"), birthMinute: String(+mm).padStart(2, "0"),
      calendarType: calendar === "solar" ? 0 : 1,
      isLeapMonth: !!body.leap && calendar === "lunar",
      gender: gender === "male" ? "0" : "1",
    },
  };
}

function buildScripts(profile, year) {
  const start = `
(function(){
  window.__r = null;
  var req;
  self.webpackChunkjeomsin_web_react.push([[Math.floor(Math.random()*1e9)], {}, function(r){ req = r; }]);
  var Kt = req(${MOD_KIND}).Kt;
  var p = ${JSON.stringify(profile)};
  Promise.all(${JSON.stringify(NEWYEAR_CHUNKS)}.map(function(c){ return req.e(c); })).then(function(){
    var f = req(${MOD_NEWYEAR}).s, out = {};
    return ${JSON.stringify(CATEGORY_KEYS)}.reduce(function(chain, k){
      return chain.then(function(){
        return f(p, '${year}', Kt[k].kind).then(function(d){ out[k] = d === undefined ? null : d; });
      });
    }, Promise.resolve()).then(function(){ return out; });
  }).then(function(o){ window.__r = {ok: true, data: o}; })
    .catch(function(e){ window.__r = {ok: false, error: String(e)}; });
})();
`;
  // Firecrawl 반환값에서 비ASCII 문자가 깨지지 않도록 \uXXXX 로 이스케이프
  const collect = "JSON.stringify(window.__r).replace(/[\\u0080-\\uffff]/g, function(c){" +
    " return '\\\\u' + ('0000' + c.charCodeAt(0).toString(16)).slice(-4); })";
  return { start, collect };
}

async function scrape(key, profile, year) {
  const { start, collect } = buildScripts(profile, year);
  const res = await fetch(FIRECRAWL_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      url: "https://www.jeomsin.co.kr/",
      formats: ["markdown"],
      waitFor: 2000,
      actions: [
        { type: "wait", milliseconds: 3000 },
        { type: "executeJavascript", script: start },
        { type: "wait", milliseconds: 15000 },
        { type: "executeJavascript", script: collect },
      ],
    }),
  });
  if (!res.ok) throw new Error(`Firecrawl 오류 ${res.status}`);
  const json = await res.json();
  const returns = json?.data?.actions?.javascriptReturns || [];
  const value = returns.length ? returns[returns.length - 1].value : null;
  const result = value ? JSON.parse(value) : null;
  if (!result) throw new Error("결과가 아직 도착하지 않았어요. 잠시 후 다시 시도해 주세요.");
  if (!result.ok) throw new Error("점신 요청에 실패했어요.");
  return result.data;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = String(env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
    const cors = {
      "Access-Control-Allow-Origin": allowed.includes(origin) ? origin : allowed[0] || "",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      Vary: "Origin",
    };
    const reply = (status, body) => new Response(JSON.stringify(body), {
      status, headers: { ...cors, "Content-Type": "application/json; charset=utf-8" },
    });

    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (url.pathname !== "/fortune" || request.method !== "POST") return reply(404, { error: "없는 주소예요." });
    if (!allowed.includes(origin)) return reply(403, { error: "허용되지 않은 사이트에서 온 요청이에요." });

    if (env.LIMITER) {
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      const { success } = await env.LIMITER.limit({ key: ip });
      if (!success) return reply(429, { error: "요청이 너무 잦아요. 1분 뒤에 다시 시도해 주세요." });
    }

    let input;
    try {
      input = buildProfile(await request.json());
    } catch (e) {
      return reply(400, { error: e instanceof InputError ? e.message : "입력 형식이 올바르지 않아요." });
    }

    try {
      const data = await scrape(env.FIRECRAWL_API_KEY, input.profile, input.year);
      if (!Object.values(data).some(Boolean)) {
        return reply(422, { error: `점신에서 ${input.year}년 운세 결과가 오지 않았어요. 아직 제공하지 않는 연도일 수 있어요.` });
      }
      return reply(200, { profile: input.profile, year: input.year, result: data });
    } catch (e) {
      return reply(502, { error: e.message || "운세를 가져오지 못했어요." });
    }
  },
};
