/* Replay: real test-set flights, each scored live, set against what happened. */
(function () {
  "use strict";
  var PAGE = 20, page = 0, rows = [];
  var F = { origin: "", carrier: "", outcome: "", q: "" };
  var $ = function (id) { return document.getElementById(id); };

  function filter() {
    var q = F.q.trim().toUpperCase().replace(/\s+/g, "");
    rows = App.replay.filter(function (f) {
      if (F.origin && f.origin !== F.origin) return false;
      if (F.carrier && f.carrier !== F.carrier) return false;
      if (F.outcome && f.outcome.key !== F.outcome) return false;
      if (q && (f.carrier + f.flight).indexOf(q) < 0 && f.dest.indexOf(q) < 0) return false;
      return true;
    });
    page = 0;
    summary();
    render();
  }

  function summary() {
    if (!rows.length) { $("r-summary").textContent = "No flights match these filters. Clear a filter to see more."; return; }
    var c = { tp: 0, tn: 0, fp: 0, fn: 0 };
    rows.forEach(function (f) { c[f.outcome.key]++; });
    var correct = c.tp + c.tn, delays = c.tp + c.fn;
    $("r-summary").innerHTML = "<strong>" + App.int(rows.length) + "</strong> flights. The model got <strong>" + App.pct(correct / rows.length) +
      "</strong> right" + (delays ? ", catching " + c.tp + " of " + delays + " delays" : "") + " with " + c.fp + " false alarm" + (c.fp === 1 ? "" : "s") + ".";
  }

  function render() {
    var start = page * PAGE, slice = rows.slice(start, start + PAGE), thr = App.model.threshold;
    $("r-rows").innerHTML = slice.map(function (f) {
      var risky = f.prob >= thr, d = new Date(f.date + "T00:00:00Z");
      return "<tr><td>" + d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" }) + "</td>" +
        "<td>" + App.esc(f.carrier + " " + f.flight) + "</td>" +
        '<td title="' + App.esc(App.airportName(f.dest)) + '">' + f.origin + " → " + App.esc(f.dest) + "</td>" +
        "<td>" + App.hhmm(f.sched) + "</td>" +
        '<td class="num"><span class="riskbar"><i><b class="' + (risky ? "is-risk" : "") + '" style="width:' + (f.prob * 100).toFixed(0) + '%"></b></i>' + App.pct(f.prob) + "</span></td>" +
        "<td>" + (risky ? "Delay likely" : "On time") + "</td>" +
        '<td class="num">' + App.delayText(f.delay) + "</td>" +
        '<td class="outcome ' + (f.outcome.good ? "outcome--good" : "outcome--bad") + '">' + (f.outcome.good ? "✓ " : "✗ ") + f.outcome.label + "</td></tr>";
    }).join("");
    var pages = Math.max(1, Math.ceil(rows.length / PAGE));
    $("r-page").textContent = "Page " + (page + 1) + " of " + pages;
    $("r-prev").disabled = page === 0;
    $("r-next").disabled = page >= pages - 1;
  }

  App.views.replay = {
    init: function () {
      var origins = {}, carriers = {};
      App.replay.forEach(function (f) { origins[f.origin] = 1; carriers[f.carrier] = 1; });
      $("r-origin").innerHTML = '<option value="">All airports</option>' + Object.keys(origins).sort().map(function (o) {
        return '<option value="' + o + '">' + o + "</option>"; }).join("");
      $("r-carrier").innerHTML = '<option value="">All airlines</option>' + Object.keys(carriers).sort().map(function (c) {
        return '<option value="' + c + '">' + App.esc(App.carrierName(c)) + " (" + c + ")</option>"; }).join("");
      ["origin", "carrier", "outcome"].forEach(function (k) {
        $("r-" + k).addEventListener("change", function (e) { F[k] = e.target.value; filter(); });
      });
      $("r-search").addEventListener("input", function (e) { F.q = e.target.value; filter(); });
      $("r-prev").addEventListener("click", function () { if (page > 0) { page--; render(); } });
      $("r-next").addEventListener("click", function () { page++; render(); });
      filter();
    }
  };
})();
