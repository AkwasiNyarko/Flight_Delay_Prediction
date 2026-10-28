/* Model results: metrics table, ROC curves, confusion matrix, feature importance. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };

  function table(s) {
    var cols = [["model", "Model"], ["threshold", "Threshold"], ["accuracy", "Accuracy"], ["precision", "Precision"],
      ["recall", "Recall"], ["f1", "F1"], ["roc_auc", "ROC-AUC"]];
    $("m-table").innerHTML = "<thead><tr>" + cols.map(function (c, i) {
      return "<th" + (i ? ' class="num"' : "") + ">" + c[1] + "</th>";
    }).join("") + "</tr></thead><tbody>" + s.results.map(function (r) {
      return "<tr" + (r.model === "XGBoost" ? ' class="is-best"' : "") + ">" + cols.map(function (c, i) {
        var v = r[c[0]];
        if (i === 0) return "<td>" + App.esc(v) + (r.model === "XGBoost" ? " (best)" : "") + "</td>";
        return '<td class="num">' + (c[0] === "threshold" ? v.toFixed(2) : v.toFixed(3)) + "</td>";
      }).join("") + "</tr>";
    }).join("") + "</tbody>";
  }

  function roc(s) {
    var c = App.COLORS, colors = { "XGBoost": c.blue, "Random Forest": c.amber, "Logistic Regression": c.grey };
    var auc = {};
    s.results.forEach(function (r) { auc[r.model] = r.roc_auc; });
    var sets = Object.keys(s.roc.curves).map(function (name) {
      return { label: name + " (AUC " + auc[name].toFixed(3) + ")", borderColor: colors[name] || c.ink, borderWidth: name === "XGBoost" ? 3 : 2,
        pointRadius: 0, data: s.roc.fpr.map(function (x, i) { return { x: x, y: s.roc.curves[name][i] }; }) };
    });
    sets.push({ label: "Random guessing", borderColor: c.ink, borderDash: [5, 4], borderWidth: 1, pointRadius: 0, data: [{ x: 0, y: 0 }, { x: 1, y: 1 }] });
    App.chart("c-roc", {
      type: "line", data: { datasets: sets },
      options: {
        parsing: false,
        scales: {
          x: { type: "linear", min: 0, max: 1, title: { display: true, text: "False alarm rate (on-time flights flagged)" } },
          y: { min: 0, max: 1, title: { display: true, text: "Share of delays caught" } }
        },
        plugins: { legend: { position: "bottom" }, tooltip: { enabled: false } }
      }
    });
  }

  function cm(s) {
    var m = s.confusion, total = m.tn + m.fp + m.fn + m.tp;
    function cell(cls, n, label) {
      return '<div class="cm__cell ' + cls + '"><b>' + App.int(n) + "</b><span>" + label + " (" + App.pct(n / total, 1) + ")</span></div>";
    }
    $("cm").innerHTML = '<span></span><span class="cm__h">Predicted on time</span><span class="cm__h">Predicted delayed</span>' +
      '<span class="cm__r">Left on time</span>' + cell("cm__tn", m.tn, "correctly on time") + cell("cm__fp", m.fp, "false alarms") +
      '<span class="cm__r">Left 15+ min late</span>' + cell("cm__fn", m.fn, "delays missed") + cell("cm__tp", m.tp, "delays caught") +
      '<span></span><p class="hint" style="grid-column: 2 / -1; margin-top: 6px">The model catches ' + App.pct(m.tp / (m.tp + m.fn)) +
      " of delays. When it warns of a delay it is right " + App.pct(m.tp / (m.tp + m.fp)) + " of the time.</p>";
  }

  function importance(s) {
    var imp = s.importance.slice(0, 10);
    App.chart("c-imp", {
      type: "bar",
      data: { labels: imp.map(function (d) { return d.label; }),
        datasets: [{ data: imp.map(function (d) { return d.value; }), backgroundColor: App.COLORS.blue, borderRadius: 2, maxBarThickness: 26 }] },
      options: {
        indexAxis: "y",
        scales: { x: { beginAtZero: true, title: { display: true, text: "Drop in ROC-AUC" } }, y: { grid: { display: false } } },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (ctx) { return "AUC drops by " + ctx.parsed.x.toFixed(4); } } } }
      }
    });
  }

  App.views.model = {
    init: function () {
      var s = App.data.summary;
      table(s); roc(s); cm(s); importance(s);
    }
  };
})();
