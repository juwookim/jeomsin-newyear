/* 신년운세 사이트 브라우저 스크립트 (GitHub Pages 용).
 *
 * - 입력 폼을 Cloudflare Worker(data-api)로 보내고, 받은 결과를 결과 페이지로 그린다.
 * - 결과 페이지 HTML은 build_site.py 의 render_page(doc, form=True, api=...) 와 같은 결과를 내도록
 *   그대로 옮긴 것이다. 템플릿·상수는 build_site.py 가 만드는 fortune-data.js 에서 읽는다.
 */
(function () {
  "use strict";
  var D = window.FORTUNE_DATA;
  if (!D) return;

  var ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" };
  function esc(s) {
    return String(s == null ? "" : s).trim().replace(/[&<>"']/g, function (c) { return ESC[c]; });
  }
  function pad(n, w) { return String(n).padStart(w, "0"); }
  function replaceAll(s, a, b) { return s.split(a).join(b); }

  function suit(name, cls) {
    return '<svg class="suit ' + (cls || "") + '" viewBox="0 0 24 24" aria-hidden="true">' + D.SUITS[name] + "</svg>";
  }

  function paragraphs(text) {
    return String(text).split(/\n\s*\n|\n/).map(function (p) { return p.trim(); })
      .filter(Boolean).map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("");
  }

  function sortedKeys(node, prefix) {
    var re = new RegExp("^" + prefix + "\\d+$");
    return Object.keys(node).filter(function (k) { return re.test(k); })
      .sort(function (a, b) { return parseInt(a.slice(prefix.length), 10) - parseInt(b.slice(prefix.length), 10); });
  }

  function firstValue(obj) { return obj[Object.keys(obj)[0]]; }

  function renderDepth(depth, accent, catTitle) {
    var out = [];
    var title = depth.title || "";
    var points = sortedKeys(depth, "point").map(function (k) { return depth[k]; });
    if (title && title !== catTitle) {
      out.push('<h4 class="sub">' + suit("sparkle", "tiny " + accent) + esc(title) + "</h4>");
    }
    if (points.length) {
      var icons = ["spade", "heart", "club", "diamond"];
      var items = points.map(function (p, i) {
        return '<li class="pt"><span class="pt-idx">' + suit(icons[i % 4], accent) + "<b>" + pad(i + 1, 2) + "</b></span>" +
          "<p>" + esc(p) + "</p></li>";
      }).join("");
      out.push('<ol class="points">' + items + "</ol>");
    }
    if (depth.img) out.push('<p class="tagline ' + accent + '">' + esc(depth.img) + "</p>");
    if (depth.text) out.push('<div class="prose">' + paragraphs(depth.text) + "</div>");
    return out.join("");
  }

  function renderScores(category) {
    var nums = sortedKeys(category, "num").map(function (k) { return category[k]; });
    var depths = sortedKeys(category, "depth").map(function (k) { return category[k]; });
    if (!nums.length || nums.length !== depths.length) return "";
    var rows = depths.map(function (d, i) {
      var n = Math.trunc(Number(nums[i]));
      return '<li><span class="sc-label">' + esc(d.title || "") + "</span>" +
        '<span class="sc-track"><span class="sc-fill" style="--v:' + n + '%"></span></span>' +
        '<span class="sc-num">' + n + "</span></li>";
    }).join("");
    return '<ul class="scores">' + rows + "</ul>";
  }

  function renderChapter(i, key, en, icon, accent, data) {
    var menu = firstValue(data);
    var title = menu.title || "";
    var frames = sortedKeys(menu, "category").map(function (ck) {
      var cat = menu[ck];
      var ctitle = cat.title || "";
      var body = renderScores(cat, accent);
      body += sortedKeys(cat, "depth").map(function (dk) { return renderDepth(cat[dk], accent, ctitle); })
        .join('<div class="divider">✦</div>');
      return '<div class="frame"><span class="frame-title ' + accent + '">' + esc(ctitle) + "</span>" +
        body + '<span class="frame-foot">' + D.ROMAN[i] + " · " + esc(en) + "</span></div>";
    });
    return '<section class="chapter" id="' + key + '">' +
      '<header class="ch-head"><span class="ch-num ' + accent + '">' + D.ROMAN[i] + "</span>" +
      suit(icon, "big " + accent) + "<h2>" + esc(title) + '</h2><span class="ch-en">' + esc(en) + "</span></header>" +
      frames.join("") + "</section>";
  }

  function firstTagline(data) {
    var found = [];
    (function walk(n) {
      if (n && typeof n === "object" && !Array.isArray(n)) {
        var img = n.img;
        if (typeof img === "string" && img.trim().length > 0 && img.trim().length <= 22) {
          var title = n.title || "";
          found.push(title === "" || title === "총운풀이" ? img : title + " · " + img);
        }
        Object.keys(n).forEach(function (k) { walk(n[k]); });
      }
    })(data);
    return found.length ? found[0] : "";
  }

  function renderDeck(result) {
    return D.CHAPTERS.map(function (c, i) {
      var key = c[0], en = c[1], icon = c[2], accent = c[3], data = result[key];
      if (!data) return "";
      var title = firstValue(data).title || "";
      return '<a class="card ' + accent + '" href="#' + key + '">' +
        '<span class="corner tl">' + D.ROMAN[i] + suit(icon, "mini") + "</span>" +
        '<span class="corner br">' + D.ROMAN[i] + suit(icon, "mini") + "</span>" +
        '<span class="card-art">' + suit(icon, "card-suit") + "</span>" +
        '<span class="card-name">' + esc(title) + "</span>" +
        '<span class="card-en">' + esc(en) + "</span>" +
        '<span class="card-tag">' + esc(firstTagline(data)) + "</span></a>";
    }).join("");
  }

  function profileValues(doc) {
    var p = doc.profile;
    var unknown = p.birthTime === "00" && p.birthMinute === "00";
    return {
      name: p.name,
      birth: pad(parseInt(p.birthYear, 10), 4) + "-" + pad(parseInt(p.birthMonth, 10), 2) + "-" + pad(parseInt(p.birthDay, 10), 2),
      calendar: p.calendarType === 0 ? "solar" : "lunar",
      leap: p.isLeapMonth ? "1" : "",
      time: unknown ? "" : p.birthTime + ":" + p.birthMinute,
      unknown: unknown ? "1" : "",
      gender: p.gender === "0" ? "male" : "female",
      year: String(doc.year)
    };
  }

  function renderForm(api, values, title) {
    var v = {};
    Object.keys(values || {}).forEach(function (k) { v[k] = esc(values[k]); });
    var hasValues = Object.keys(v).length > 0;
    function chk(cond) { return cond ? " checked" : ""; }
    var lunar = v.calendar === "lunar", female = v.gender === "female";
    var year = v.year || String(new Date().getFullYear());
    return "\n" +
      '  <form class="frame fortune-form" method="post" action="#" data-api="' + esc(api) + '">\n' +
      '    <span class="frame-title green">' + title + "</span>\n" +
      "    \n" +
      '    <div class="fields">\n' +
      '      <label class="field"><span>이름</span><input type="text" name="name" required maxlength="20" placeholder="홍길동" value="' + (v.name || "") + '"></label>\n' +
      '      <label class="field"><span>생년월일</span><input type="date" name="birth" required min="1900-01-01" max="2099-12-31" value="' + (v.birth || "") + '"></label>\n' +
      '      <div class="field"><span>양력 · 음력</span><div class="seg">\n' +
      '        <label><input type="radio" name="calendar" value="solar"' + chk(!lunar) + "><b>양력</b></label>\n" +
      '        <label><input type="radio" name="calendar" value="lunar"' + chk(lunar) + "><b>음력</b></label>\n" +
      '        <label><input type="checkbox" name="leap" value="1"' + chk(v.leap) + "><b>윤달</b></label></div></div>\n" +
      '      <div class="field"><span>태어난 시간</span><div class="seg">\n' +
      '        <input type="time" name="time" value="' + (v.time || "") + '">\n' +
      '        <label><input type="checkbox" name="unknown" value="1"' + chk(v.unknown || !hasValues) + "><b>모름</b></label></div></div>\n" +
      '      <div class="field"><span>성별</span><div class="seg">\n' +
      '        <label><input type="radio" name="gender" value="male"' + chk(!female) + "><b>남</b></label>\n" +
      '        <label><input type="radio" name="gender" value="female"' + chk(female) + "><b>여</b></label></div></div>\n" +
      '      <div class="field"><span>운세 연도</span><div class="seg"><label><input type="radio" name="year" value="' + year + '" checked><b>' + year + "년</b></label></div></div>\n" +
      "    </div>\n" +
      '    <button class="draw" type="submit">카드 뽑기 ✦</button>\n' +
      '    <span class="frame-foot">DRAW A NEW CARD</span>\n' +
      "  </form>\n" +
      '  <div class="loading" hidden>' + D.EMBLEM + "<p>카드를 섞는 중</p><small>점신에서 운세를 가져오고 있어요 · 30초 정도 걸려요</small></div>\n" +
      "  ";
  }

  function renderPage(doc, api) {
    var p = doc.profile, year = parseInt(doc.year, 10), result = doc.result;
    var si = ((year - 4) % 10 + 10) % 10, bi = ((year - 4) % 12 + 12) % 12;
    var ganji = D.STEMS[si] + D.BRANCHES[bi];
    var color = D.STEM_COLORS[si];
    var zodiac = color + " " + D.ANIMALS[bi];
    var zodiacEn = "YEAR OF THE " + D.COLORS_EN[color] + " " + D.ANIMALS_EN[bi];
    var cal = p.calendarType === 0 ? "양력" : (p.isLeapMonth ? "음력 윤달" : "음력");
    var birth = p.birthYear + "." + pad(parseInt(p.birthMonth, 10), 2) + "." + pad(parseInt(p.birthDay, 10), 2) + " " + cal;
    var btime = p.birthTime === "00" && p.birthMinute === "00" ? "시간 모름" : p.birthTime + ":" + p.birthMinute;
    var gender = p.gender === "0" ? "남" : "여";

    var total = ((result.Total || {}).menu2 || {}).category1 || {};
    var advice = (total.depth4 || {}).text || "";
    var best = (total.depth2 || {}).img || "";
    var care = (total.depth3 || {}).img || "";

    var chapters = D.CHAPTERS.map(function (c, i) {
      return result[c[0]] ? renderChapter(i, c[0], c[1], c[2], c[3], result[c[0]]) : "";
    }).join("");

    var page = D.TEMPLATE;
    [
      ["{{YEAR}}", String(year)], ["{{GANJI}}", ganji], ["{{ZODIAC}}", zodiac], ["{{ZODIAC_EN}}", zodiacEn],
      ["{{NAME}}", esc(p.name)], ["{{BIRTH}}", esc(birth)], ["{{BTIME}}", esc(btime)], ["{{GENDER}}", gender],
      ["{{BEST}}", esc(best)], ["{{CARE}}", esc(care)], ["{{ADVICE}}", paragraphs(advice)],
      ["{{DECK}}", renderDeck(result)], ["{{CHAPTERS}}", chapters],
      ["{{CHANGE}}", '<details class="change"><summary>사주 변경 ✦</summary>' +
        renderForm(api, profileValues(doc), "사주 정보 변경") + "</details>"],
      ["/*{{FORM_CSS}}*/", D.FORM_CSS],
      ["{{FORM_JS}}", D.API_SCRIPTS]
    ].forEach(function (r) { page = replaceAll(page, r[0], r[1]); });
    return page;
  }

  function showError(form, msg) {
    var el = form.querySelector(".form-error");
    if (!el) {
      el = document.createElement("p");
      el.className = "form-error";
      form.querySelector(".fields").before(el);
    }
    el.textContent = msg;
  }

  function bind(form) {
    var t = form.elements.time, u = form.elements.unknown, leap = form.elements.leap;
    var loading = form.parentNode.querySelector(".loading");
    var btn = form.querySelector(".draw");
    function sync() {
      t.disabled = u.checked; if (u.checked) t.value = "";
      var lunar = form.querySelector("input[name=calendar]:checked").value === "lunar";
      leap.disabled = !lunar; if (!lunar) leap.checked = false;
    }
    form.addEventListener("change", sync); sync();
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var fd = new FormData(form);
      var body = {
        name: fd.get("name") || "", birth: fd.get("birth") || "",
        time: fd.get("unknown") ? "" : (fd.get("time") || ""),
        calendar: fd.get("calendar") || "solar", leap: !!fd.get("leap"),
        gender: fd.get("gender") || "male", year: fd.get("year") || ""
      };
      loading.hidden = false; btn.disabled = true;
      fetch(form.dataset.api, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok) throw new Error(data.error || "운세를 가져오지 못했어요 (오류 " + r.status + "). 잠시 후 다시 시도해 주세요.");
          return data;
        });
      }, function () {
        throw new Error("운세 서버에 연결하지 못했어요. 인터넷 연결을 확인하고 다시 시도해 주세요.");
      }).then(function (doc) {
        var html = renderPage(doc, form.dataset.api);
        document.open(); document.write(html); document.close();
        window.scrollTo(0, 0);
      }).catch(function (err) {
        loading.hidden = true; btn.disabled = false;
        showError(form, err.message);
      });
    });
  }

  window.FortuneRender = { renderPage: renderPage };
  document.querySelectorAll(".fortune-form[data-api]").forEach(bind);
})();
