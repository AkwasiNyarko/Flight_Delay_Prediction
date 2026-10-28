/* Core: data loading, tab routing, shared helpers. Views register in App.views. */
(function () {
  "use strict";

  var App = {
    data: {},
    model: null,
    views: {},
    started: {},
    charts: {},
    DOW: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    MONTHS: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    COLORS: { blue: "#2f6fed", amber: "#f5a524", late: "#c2410c", ink: "#172033", muted: "#566173", line: "#d5dbe3", grey: "#9aa3b2" }
  };

  /* ---------- formatting ---------- */
  App.pct = function (x, digits) { return (x * 100).toFixed(digits === undefined ? 0 : digits) + "%"; };
  App.int = function (x) { return Math.round(x).toLocaleString("en-US"); };
  App.hhmm = function (sched) { var s = String(sched).padStart(4, "0"); return s.slice(0, 2) + ":" + s.slice(2); };
  App.hourLabel = function (h) { return String(h).padStart(2, "0") + ":00"; };
  App.delayText = function (min) { return (min > 0 ? "+" : "") + min + " min"; };
  App.esc = function (s) {
    return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; });
  };
  App.airportName = function (code) { return App.data.lookup.airports[code] || code; };
  App.carrierName = function (code) { return App.data.lookup.carriers[code] || code; };

  /* ---------- outcomes ---------- */
  App.outcome = function (prob, depDelay) {
    var predicted = prob >= App.model.threshold, actual = depDelay >= 15;
    if (predicted && actual) return { key: "tp", label: "Delay caught", good: true };
    if (!predicted && !actual) return { key: "tn", label: "Correctly on time", good: true };
    if (predicted && !actual) return { key: "fp", label: "False alarm", good: false };
    return { key: "fn", label: "Delay missed", good: false };
  };

  /* ---------- holidays (same rules as flight_delay/features.py: federal holidays of the same year) ---------- */
  function nthWeekday(year, month, weekday, n) {          // n = -1 for last
    if (n > 0) {
      var first = new Date(Date.UTC(year, month, 1));
      var day = 1 + ((weekday - first.getUTCDay() + 7) % 7) + (n - 1) * 7;
      return Date.UTC(year, month, day);
    }
    var last = new Date(Date.UTC(year, month + 1, 0));
    return Date.UTC(year, month, last.getUTCDate() - ((last.getUTCDay() - weekday + 7) % 7));
  }
  App.holidays = function (year) {
    return [Date.UTC(year, 0, 1), nthWeekday(year, 0, 1, 3), nthWeekday(year, 1, 1, 3),
      nthWeekday(year, 4, 1, -1), Date.UTC(year, 6, 4), nthWeekday(year, 8, 1, 1),
      nthWeekday(year, 9, 1, 2), Date.UTC(year, 10, 11), nthWeekday(year, 10, 4, 4), Date.UTC(year, 11, 25)]
      .concat(year >= 2021 ? [Date.UTC(year, 5, 19)] : []);          // Juneteenth, as in features.py
  };
  App.daysToHoliday = function (utcMs) {
    var y = new Date(utcMs).getUTCFullYear();
    return Math.min.apply(null, App.holidays(y).map(function (h) { return Math.round(Math.abs(utcMs - h) / 864e5); }));
  };

  /* Dew point (°F) from temperature (°F) and relative humidity (%), Magnus formula. */
  App.dewPoint = function (tempF, rh) {
    var t = (tempF - 32) * 5 / 9, g = Math.log(Math.max(rh, 1) / 100) + (17.62 * t) / (243.12 + t);
    return (243.12 * g / (17.62 - g)) * 9 / 5 + 32;
  };

  /* ---------- charts ---------- */
  App.chart = function (id, config) {
    if (App.charts[id]) App.charts[id].destroy();
    var el = document.getElementById(id);
    App.charts[id] = new Chart(el, config);
    return App.charts[id];
  };
  App.pctAxis = function (max) {
    return { beginAtZero: true, max: max, ticks: { callback: function (v) { return Math.round(v * 100) + "%"; } }, grid: { color: "#e6eaf0" } };
  };
  function chartDefaults() {
    Chart.defaults.font.family = "Barlow, Arial, sans-serif";
    Chart.defaults.font.size = 13;
    Chart.defaults.color = App.COLORS.muted;
    Chart.defaults.plugins.legend.labels.boxWidth = 12;
    Chart.defaults.plugins.tooltip.backgroundColor = App.COLORS.ink;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.animation.duration = 300;
    Chart.defaults.scale.grid.color = "#e6eaf0";
  }

  /* ---------- routing ---------- */
  function show(view) {
    if (!App.views[view]) view = "overview";
    document.querySelectorAll(".view").forEach(function (s) { s.hidden = s.id !== "view-" + view; });
    document.querySelectorAll(".tabs button").forEach(function (b) {
      var on = b.dataset.view === view;
      b.setAttribute("aria-selected", on ? "true" : "false");
      b.tabIndex = on ? 0 : -1;
    });
    if (!App.started[view]) { App.started[view] = true; App.views[view].init(); }
    else if (App.views[view].show) App.views[view].show();
  }
  function route() { show((location.hash || "#overview").slice(1)); }

  function wireTabs() {
    var tabs = Array.prototype.slice.call(document.querySelectorAll(".tabs button"));
    tabs.forEach(function (b, i) {
      b.addEventListener("click", function () {
        if (location.hash === "#" + b.dataset.view) route(); else location.hash = b.dataset.view;
      });
      b.addEventListener("keydown", function (e) {
        var j = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : null;
        if (j === null) return;
        var t = tabs[(j + tabs.length) % tabs.length]; t.focus(); t.click();
      });
    });
    window.addEventListener("hashchange", route);
  }

  /* ---------- shared fill-ins ---------- */
  function fillStats() {
    var s = App.data.summary, base = s.results[0];
    App.year = s.dataset.year;
    var fills = {
      year: String(s.dataset.year), flights: App.int(s.dataset.flights), auc: s.headline.auc.toFixed(3), recall: App.pct(s.headline.recall),
      delayrate: App.pct(s.dataset.delay_rate), trees: String(App.model.trees.length),
      testn: App.int(s.dataset.test), baseacc: App.pct(base.accuracy), threshold: s.threshold.toFixed(2),
      replayn: App.int(App.data.replay.meta.length)
    };
    document.querySelectorAll("[data-fill]").forEach(function (el) {
      if (fills[el.dataset.fill] !== undefined) el.textContent = fills[el.dataset.fill];
    });
  }

  /* Score every replay flight once; used by Overview and Replay. */
  function scoreReplay() {
    var r = App.data.replay, f = r.features;
    App.replay = r.meta.map(function (m, i) {
      var p = App.model.predictRow(f, r.rows[i]);
      return { date: m[0], carrier: m[1], flight: m[2], origin: m[3], dest: m[4], sched: m[5],
        delay: m[6], prob: p, outcome: App.outcome(p, m[6]) };
    });
  }

  function fetchJSON(name) {
    return fetch("data/" + name).then(function (r) {
      if (!r.ok) throw new Error(name + " returned HTTP " + r.status);
      return r.json();
    });
  }

  App.start = function () {
    var status = document.getElementById("load-status");
    if (typeof Chart === "undefined") {
      status.textContent = "The charting library didn't load. Check your internet connection and reload the page.";
      status.classList.add("status--error");
      return;
    }
    chartDefaults();
    var files = ["model", "summary", "explore", "lookup", "replay"];
    Promise.all(files.map(function (n) { return fetchJSON(n + ".json"); }))
      .then(function (res) {
        files.forEach(function (n, i) { App.data[n] = res[i]; });
        App.model = new DelayModel(App.data.model);
        scoreReplay();
        fillStats();
        status.hidden = true;
        wireTabs();
        route();
      })
      .catch(function (err) {
        status.textContent = "Couldn't load the model data (" + err.message + "). If you opened index.html straight from disk, serve the docs folder instead: python -m http.server --directory docs";
        status.classList.add("status--error");
        console.error(err);
      });
  };

  window.App = App;
})();
