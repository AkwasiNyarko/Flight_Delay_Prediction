/* Explore: delay rates from precomputed counts, filtered by airport and airline. */
(function () {
  "use strict";
  var E, F = { origin: "", carrier: "" };
  var $ = function (id) { return document.getElementById(id); };

  /* Sum [n, late] per value of one dimension under the current filters. */
  function tally(dim, ignoreCarrier) {
    var d = E.dims[dim], oi = E.origins.indexOf(F.origin), ci = E.carriers.indexOf(F.carrier), out = {};
    d.rows.forEach(function (r) {
      if (F.origin && r[0] !== oi) return;
      if (!ignoreCarrier && F.carrier && r[1] !== ci) return;
      var k = r[2]; out[k] = out[k] || [0, 0]; out[k][0] += r[3]; out[k][1] += r[4];
    });
    return out;
  }
  function overall() {
    var t = tally("month"), n = 0, late = 0;
    Object.keys(t).forEach(function (k) { n += t[k][0]; late += t[k][1]; });
    return { n: n, rate: n ? late / n : 0 };
  }

  function bar(id, labels, values, ns, avg, opts) {
    opts = opts || {};
    var c = App.COLORS;
    var data = {
      labels: labels,
      datasets: [{ type: "bar", label: "Share delayed 15+ min", data: values, backgroundColor: opts.colors || c.blue, borderRadius: 2, maxBarThickness: 46 },
        { type: "line", label: "Average for this selection", data: labels.map(function () { return avg; }),
          borderColor: c.ink, borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0 }]
    };
    var horizontal = !!opts.horizontal;
    var valueAxis = App.pctAxis(opts.max);
    var cfg = {
      type: "bar", data: data,
      options: {
        indexAxis: horizontal ? "y" : "x",
        scales: horizontal ? { x: valueAxis, y: { grid: { display: false } } } : { y: valueAxis, x: { grid: { display: false } } },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function (ctx) {
            if (ctx.datasetIndex === 1) return "Average: " + App.pct(avg, 1);
            return App.pct(horizontal ? ctx.parsed.x : ctx.parsed.y, 1) + " delayed (" + App.int(ns[ctx.dataIndex]) + " flights)";
          } } }
        }
      }
    };
    if (horizontal) data.datasets.pop();      // a flat line doesn't read well on a horizontal bar chart
    App.chart(id, cfg);
  }

  function series(dim, labelFn, ignoreCarrier) {
    var t = tally(dim, ignoreCarrier), values = E.dims[dim].values.filter(function (v) { return t[v] && t[v][0] > 0; });
    return { labels: values.map(labelFn), rates: values.map(function (v) { return t[v][1] / t[v][0]; }),
      ns: values.map(function (v) { return t[v][0]; }), values: values };
  }

  function render() {
    var o = overall();
    var who = (F.carrier ? App.carrierName(F.carrier) : "All airlines") + " from " + (F.origin ? App.airportName(F.origin) : "all three New York airports");
    if (!o.n) {
      $("x-summary").textContent = App.carrierName(F.carrier) + " didn't fly from " + F.origin + " in " + App.year + ". Choose another airport or airline.";
      return;
    }
    $("x-summary").innerHTML = App.esc(who) + ": <strong>" + App.int(o.n) + "</strong> departures, <strong>" + App.pct(o.rate, 1) + "</strong> left 15+ min late.";

    var h = series("hour", App.hourLabel);
    bar("c-x-hour", h.labels, h.rates, h.ns, o.rate, { max: 0.6 });
    var m = series("month", function (v) { return App.MONTHS[v - 1]; });
    bar("c-x-month", m.labels, m.rates, m.ns, o.rate, { max: 0.45 });
    var d = series("dow", function (v) { return App.DOW[v]; });
    bar("c-x-dow", d.labels, d.rates, d.ns, o.rate, { max: 0.45 });
    var v = series("vis", function (x) { return E.dims.vis.labels[x]; });
    bar("c-x-vis", v.labels, v.rates, v.ns, o.rate, { max: 0.6, colors: App.COLORS.amber });
    var p = series("precip_flag", function (x) { return E.dims.precip_flag.labels[x]; });
    bar("c-x-precip", p.labels, p.rates, p.ns, o.rate, { max: 0.6, colors: [App.COLORS.grey, App.COLORS.amber] });

    // airlines: compare all airlines at the chosen airport (ignores the airline filter)
    var byC = {}, oi = E.origins.indexOf(F.origin);
    E.dims.month.rows.forEach(function (r) {
      if (F.origin && r[0] !== oi) return;
      var c = E.carriers[r[1]]; byC[c] = byC[c] || [0, 0]; byC[c][0] += r[3]; byC[c][1] += r[4];
    });
    var carriers = Object.keys(byC).filter(function (c) { return byC[c][0] >= 50; })
      .sort(function (a, b) { return byC[b][1] / byC[b][0] - byC[a][1] / byC[a][0]; });
    $("x-airline-note").textContent = "All airlines " + (F.origin ? "at " + F.origin : "across the three airports") +
      " with at least 50 departures" + (F.carrier ? "; " + App.carrierName(F.carrier) + " is highlighted." : ".");
    bar("c-x-airline", carriers.map(function (c) { return App.carrierName(c) + " (" + c + ")"; }),
      carriers.map(function (c) { return byC[c][1] / byC[c][0]; }), carriers.map(function (c) { return byC[c][0]; }), o.rate,
      { horizontal: true, max: 0.4, colors: carriers.map(function (c) { return c === F.carrier ? App.COLORS.amber : App.COLORS.blue; }) });
  }

  App.views.explore = {
    init: function () {
      E = App.data.explore;
      $("x-origin").innerHTML = '<option value="">All airports</option>' + E.origins.map(function (o) {
        return '<option value="' + o + '">' + o + " – " + App.esc(App.airportName(o)) + "</option>";
      }).join("");
      $("x-carrier").innerHTML = '<option value="">All airlines</option>' + E.carriers.map(function (c) {
        return '<option value="' + c + '">' + App.esc(App.carrierName(c)) + " (" + c + ")</option>";
      }).join("");
      $("x-origin").addEventListener("change", function (e) { F.origin = e.target.value; render(); });
      $("x-carrier").addEventListener("change", function (e) { F.carrier = e.target.value; render(); });
      render();
    }
  };
})();
