/* Overview: a departures board of real test flights, one airport-day at a time. */
(function () {
  "use strict";
  var days = [], idx = 0;

  function buildDays() {
    var groups = {};
    App.replay.forEach(function (f) {
      var k = f.date + "|" + f.origin;
      (groups[k] = groups[k] || []).push(f);
    });
    // airport-days with enough flights and at least one real delay make an honest, lively board
    days = Object.keys(groups).map(function (k) { return { key: k, flights: groups[k] }; })
      .filter(function (d) { return d.flights.length >= 7 && d.flights.some(function (f) { return f.delay >= 15; }); })
      .sort(function (a, b) { return a.key < b.key ? -1 : 1; });
    // start on the busiest pre-Christmas day if there is one
    var start = days.findIndex(function (d) { return d.key.indexOf(App.year + "-12-2") === 0; });
    idx = start >= 0 ? start : 0;
  }

  function render() {
    var day = days[idx];
    if (!day) return;
    var parts = day.key.split("|"), d = new Date(parts[0] + "T00:00:00Z");
    document.getElementById("board-airport").textContent = parts[1];
    document.getElementById("board-date").textContent =
      d.toLocaleDateString("en-US", { weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
    var flights = day.flights.slice().sort(function (a, b) { return a.sched - b.sched; });
    // keep the board compact: up to 8 rows spread over the day
    if (flights.length > 8) {
      var step = flights.length / 8, pick = [];
      for (var i = 0; i < 8; i++) pick.push(flights[Math.floor(i * step)]);
      flights = pick;
    }
    document.getElementById("board-rows").innerHTML = flights.map(function (f, i) {
      var risky = f.prob >= App.model.threshold;
      return '<tr style="animation-delay:' + (i * 45) + 'ms">' +
        "<td>" + App.hhmm(f.sched) + "</td>" +
        "<td>" + App.esc(f.carrier + " " + f.flight) + "</td>" +
        '<td title="' + App.esc(App.airportName(f.dest)) + '">' + App.esc(f.dest) + "</td>" +
        '<td class="num' + (risky ? " risk-hi" : "") + '">' + App.pct(f.prob) + "</td>" +
        '<td><span class="flag ' + (risky ? "flag--risk" : "flag--ok") + '">' + (risky ? "Delay likely" : "On time") + "</span></td>" +
        '<td class="num' + (f.delay >= 15 ? " late" : "") + '">' + (f.delay >= 15 ? App.delayText(f.delay) : (f.delay <= 0 ? "On time" : App.delayText(f.delay))) + "</td></tr>";
    }).join("");
  }

  App.views.overview = {
    init: function () {
      buildDays();
      render();
      document.getElementById("board-next").addEventListener("click", function () {
        idx = (idx + 1) % days.length; render();
      });
    }
  };
})();
