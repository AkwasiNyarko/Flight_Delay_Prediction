/* Predictor: builds the model's 22 inputs from the form and scores them live. */
(function () {
  "use strict";
  var L, S = {}, weatherCustom = false;
  var STATE_NAMES = ["Calm", "Typical", "Busy", "Severe"];
  var $ = function (id) { return document.getElementById(id); };

  function typical(origin, hour) { return (L.typical[origin] || {})[hour] || null; }
  function hoursFor(origin) { return Object.keys(L.typical[origin] || {}).map(Number).sort(function (a, b) { return a - b; }); }
  function route() {
    return (L.routes[S.origin] || []).find(function (r) { return r.dest === S.dest; }) || null;
  }

  /* The exact record the model expects (see flight_delay/config.py MODEL_FEATURES). */
  function record(s) {
    var t = typical(s.origin, s.hour), r = (L.routes[s.origin] || []).find(function (x) { return x.dest === s.dest; });
    var plane = L.plane[s.carrier] || {};
    var cv = L.carrier_volume[s.carrier + "|" + s.origin + "|" + s.hour];
    var hasRecent = t && t.recent_delay;
    return {
      sched_dep_hour: s.hour, day_of_week: (new Date(s.date).getUTCDay() + 6) % 7,
      month: new Date(s.date).getUTCMonth() + 1, distance: r ? r.distance : null,
      plane_age: plane.plane_age, seats: plane.seats,
      temp: s.temp, dewp: App.dewPoint(s.temp, s.humid), humid: s.humid, wind_speed: s.wind,
      wind_gust: null, precip: s.precip, pressure: s.pressure, visib: s.visib,
      origin_hourly_volume: t ? t.volume : null, carrier_hour_volume: cv === undefined ? 1 : cv,
      days_to_holiday: App.daysToHoliday(s.date),
      origin_recent_delay: hasRecent ? t.recent_delay[s.state] : null,
      origin_recent_delay_rate: hasRecent ? t.recent_rate[s.state] : null,
      carrier: s.carrier, origin: s.origin,
      dest_grouped: L.top_dests.indexOf(s.dest) >= 0 ? s.dest : "OTHER"
    };
  }
  function prob(overrides) { return App.model.predict(record(Object.assign({}, S, overrides || {}))); }

  /* ---------- form population ---------- */
  function options(sel, items, value) {
    sel.innerHTML = items.map(function (it) {
      return '<option value="' + App.esc(it.value) + '"' + (it.value === value ? " selected" : "") + ">" + App.esc(it.label) + "</option>";
    }).join("");
    if (!items.some(function (it) { return it.value === value; }) && items.length) sel.value = items[0].value;
    return sel.value;
  }
  function fillDest() {
    S.dest = options($("f-dest"), (L.routes[S.origin] || []).map(function (r) {
      return { value: r.dest, label: r.dest + " – " + App.airportName(r.dest) };
    }), S.dest);
  }
  function fillCarrier() {
    var r = route();
    S.carrier = options($("f-carrier"), (r ? r.carriers : []).map(function (c) {
      return { value: c, label: App.carrierName(c) + " (" + c + ")" };
    }), S.carrier);
  }
  function fillHours() {
    var v = options($("f-hour"), hoursFor(S.origin).map(function (h) { return { value: String(h), label: App.hourLabel(h) }; }), String(S.hour));
    S.hour = Number(v);
  }
  function applyTypicalWeather() {
    var w = (L.weather[S.origin] || {})[new Date(S.date).getUTCMonth() + 1] || {};
    S.temp = w.temp != null ? Math.round(w.temp) : 55;
    S.humid = w.humid != null ? Math.round(w.humid) : 60;
    S.wind = w.wind_speed != null ? Math.round(w.wind_speed) : 9;
    S.pressure = w.pressure != null ? Math.round(w.pressure) : 1017;
    S.visib = w.visib != null ? w.visib : 10;
    S.precip = 0;
    weatherCustom = false;
    syncSliders();
  }
  var SLIDERS = [
    ["temp", "f-temp", "o-temp", function (v) { return v + " °F"; }],
    ["humid", "f-humid", "o-humid", function (v) { return v + "%"; }],
    ["wind", "f-wind", "o-wind", function (v) { return v + " mph"; }],
    ["precip", "f-precip", "o-precip", function (v) { return v === 0 ? "None" : v.toFixed(2) + " in/hr"; }],
    ["visib", "f-visib", "o-visib", function (v) { return v >= 10 ? "10 mi (clear)" : v + " mi"; }],
    ["pressure", "f-pressure", "o-pressure", function (v) { return v + " mb"; }]
  ];
  function syncSliders() {
    SLIDERS.forEach(function (s) { $(s[1]).value = S[s[0]]; $(s[2]).textContent = s[3](S[s[0]]); });
  }

  /* ---------- rendering ---------- */
  function stateDetail() {
    var t = typical(S.origin, S.hour), el = $("state-detail");
    if (!t || !t.recent_delay) {
      el.textContent = "No flights leave " + S.origin + " two to three hours before " + App.hourLabel(S.hour) + ", so the model uses its default for this input.";
      return;
    }
    el.textContent = STATE_NAMES[S.state] + " at " + S.origin + " around " + App.hourLabel(S.hour) +
      ": earlier departures averaged " + Math.round(t.recent_delay[S.state]) + " min late, and " +
      App.pct(t.recent_rate[S.state]) + " of them left 15+ min late.";
  }

  function renderTicket(p) {
    var thr = App.model.threshold, risky = p >= thr, t = typical(S.origin, S.hour);
    var d = new Date(S.date);
    $("t-flight").textContent = App.carrierName(S.carrier);
    $("t-route").textContent = S.origin + " → " + S.dest;
    $("t-when").textContent = d.toLocaleDateString("en-US", { weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) +
      ", departs " + App.hourLabel(S.hour) + " for " + App.airportName(S.dest);
    $("t-prob").textContent = App.pct(p);
    $("t-prob").classList.toggle("is-risk", risky);
    $("t-meter").style.width = (p * 100).toFixed(1) + "%";
    $("t-meter").classList.toggle("is-risk", risky);
    $("t-mark").style.left = (thr * 100) + "%";
    $("t-verdict").innerHTML = (risky ? "Delay likely" : "Likely on time") +
      "<small>" + (risky ? "Above" : "Below") + " the model's " + App.pct(thr) + " decision threshold. In " + App.year + ", " +
      (t ? App.pct(t.delay_rate) : "–") + " of all departures from " + S.origin + " at this hour left 15+ min late.</small>";
  }

  function renderHours(p) {
    var hours = hoursFor(S.origin);
    var probs = hours.map(function (h) { return h === S.hour ? p : prob({ hour: h }); });
    var c = App.COLORS;
    var cfg = {
      type: "line",
      data: {
        labels: hours.map(App.hourLabel),
        datasets: [
          { label: "Delay risk", data: probs, borderColor: c.ink, backgroundColor: c.ink, borderWidth: 2, tension: 0.25,
            pointRadius: hours.map(function (h) { return h === S.hour ? 7 : 3; }),
            pointBackgroundColor: probs.map(function (q) { return q >= App.model.threshold ? c.amber : c.blue; }),
            pointBorderColor: hours.map(function (h) { return h === S.hour ? c.ink : "transparent"; }), pointBorderWidth: 2 },
          { label: "Decision threshold", data: hours.map(function () { return App.model.threshold; }),
            borderColor: c.grey, borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0 }
        ]
      },
      options: {
        scales: { y: App.pctAxis(1), x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } } },
        plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: function (ctx) { return ctx.dataset.label + ": " + App.pct(ctx.parsed.y); } } } },
        animation: false
      }
    };
    var ch = App.charts["c-hours"];
    if (ch) { ch.data = cfg.data; ch.update("none"); } else App.chart("c-hours", cfg);
  }

  function renderWhatIf(p) {
    var items = [];
    var altHour = S.hour <= 9 ? 19 : 7;
    if (hoursFor(S.origin).indexOf(altHour) >= 0) items.push(["Leaving at " + App.hourLabel(altHour) + " instead", prob({ hour: altHour })]);
    if (S.state !== 0) items.push(["The airport running calmly", prob({ state: 0 })]);
    else items.push(["The airport badly backed up", prob({ state: 3 })]);
    if (S.precip > 0 || S.visib < 10) items.push(["Dry, clear weather", prob({ precip: 0, visib: 10 })]);
    else items.push(["Rain and 2-mile visibility", prob({ precip: 0.1, visib: 2, humid: 95 })]);
    var r = route();
    if (r && r.carriers.length > 1) {
      var best = r.carriers.filter(function (c) { return c !== S.carrier; })
        .map(function (c) { return [c, prob({ carrier: c })]; })
        .sort(function (a, b) { return a[1] - b[1]; })[0];
      items.push(["Flying " + App.carrierName(best[0]) + " on this route", best[1]]);
    }
    $("whatif").innerHTML = items.map(function (it) {
      var d = it[1] - p, pts = Math.round(d * 100);
      var cls = pts > 0 ? "delta--up" : pts < 0 ? "delta--down" : "";
      var txt = pts === 0 ? "no change" : (pts > 0 ? "+" : "−") + Math.abs(pts) + " pts";
      return "<li><span>" + App.esc(it[0]) + '</span><span class="p">' + App.pct(it[1]) + '</span><span class="delta ' + cls + '">' + txt + "</span></li>";
    }).join("");
  }

  function update() {
    var p = prob();
    stateDetail();
    renderTicket(p);
    renderHours(p);
    renderWhatIf(p);
  }

  /* ---------- wiring ---------- */
  function readDate() {
    var v = $("f-date").value, m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v);
    if (!m) return false;
    S.date = Date.UTC(+m[1], +m[2] - 1, +m[3]);
    return true;
  }

  App.views.predict = {
    init: function () {
      L = App.data.lookup;
      var origins = Object.keys(L.routes).sort();
      S = { origin: "JFK", dest: "MCO", carrier: "B6", hour: 19, state: 1 };
      $("f-date").value = App.year + "-12-20";
      readDate();
      options($("f-origin"), origins.map(function (o) { return { value: o, label: o + " – " + App.airportName(o) }; }), S.origin);
      fillDest(); fillCarrier(); fillHours(); applyTypicalWeather();

      $("f-origin").addEventListener("change", function (e) {
        S.origin = e.target.value; fillDest(); fillCarrier(); fillHours();
        if (!weatherCustom) applyTypicalWeather();
        update();
      });
      $("f-dest").addEventListener("change", function (e) { S.dest = e.target.value; fillCarrier(); update(); });
      $("f-carrier").addEventListener("change", function (e) { S.carrier = e.target.value; update(); });
      $("f-hour").addEventListener("change", function (e) { S.hour = Number(e.target.value); update(); });
      $("f-date").addEventListener("change", function () {
        if (!readDate()) return;
        if (!weatherCustom) applyTypicalWeather();
        update();
      });
      $("f-state").addEventListener("change", function (e) { S.state = Number(e.target.value); update(); });
      SLIDERS.forEach(function (s) {
        $(s[1]).addEventListener("input", function (e) {
          S[s[0]] = Number(e.target.value); weatherCustom = true;
          $(s[2]).textContent = s[3](S[s[0]]); update();
        });
      });
      $("weather-reset").addEventListener("click", function () { applyTypicalWeather(); update(); });
      $("predict-form").addEventListener("submit", function (e) { e.preventDefault(); });
      update();
    },
    show: function () { if (App.charts["c-hours"]) App.charts["c-hours"].resize(); }
  };

  /* exposed for the browser test */
  App.predictRecord = function () { return record(S); };
})();
