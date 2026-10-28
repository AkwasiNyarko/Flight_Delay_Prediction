/*
 * DelayModel — runs the exported XGBoost model in the browser (or Node).
 *
 * Reproduces the scikit-learn pipeline used in training:
 *   1. numeric features: missing -> training median (SimpleImputer)
 *   2. categorical features: one-hot in the fitted category order; unknown -> all zeros
 *   3. XGBoost: inputs and split values compared as float32, leaf values summed onto the
 *      base margin, then a sigmoid.
 */
(function (root) {
  "use strict";

  function sigmoid(z) { return 1 / (1 + Math.exp(-z)); }

  function DelayModel(spec) {
    this.numeric = spec.numeric;
    this.medians = spec.medians;
    this.categorical = spec.categorical;
    this.baseMargin = spec.base_margin;
    this.threshold = spec.threshold;
    this.catIndex = spec.categorical.map(function (c) {
      var m = Object.create(null);
      c.categories.forEach(function (v, i) { m[v] = i; });
      return m;
    });
    this.nFeatures = spec.numeric.length +
      spec.categorical.reduce(function (s, c) { return s + c.categories.length; }, 0);
    this.trees = spec.trees.map(function (t) {
      return {
        f: Int32Array.from(t.f), t: Float32Array.from(t.t),
        y: Int32Array.from(t.y), n: Int32Array.from(t.n), v: Float64Array.from(t.v)
      };
    });
  }

  /* record: object keyed by feature name (null/undefined/NaN numeric = missing). */
  DelayModel.prototype.vectorize = function (record) {
    var x = new Float32Array(this.nFeatures);
    var i, v;
    for (i = 0; i < this.numeric.length; i++) {
      v = record[this.numeric[i]];
      v = (v === null || v === undefined || v === "" || isNaN(+v)) ? this.medians[i] : +v;
      x[i] = v;
    }
    var offset = this.numeric.length;
    for (i = 0; i < this.categorical.length; i++) {
      var c = this.categorical[i];
      var idx = this.catIndex[i][String(record[c.name])];
      if (idx !== undefined) x[offset + idx] = 1;
      offset += c.categories.length;
    }
    return x;
  };

  DelayModel.prototype.margin = function (x) {
    var s = this.baseMargin;
    for (var k = 0; k < this.trees.length; k++) {
      var t = this.trees[k], node = 0;
      while (t.f[node] >= 0) {
        node = x[t.f[node]] < t.t[node] ? t.y[node] : t.n[node];
      }
      s += t.v[node];
    }
    return s;
  };

  DelayModel.prototype.predict = function (record) {
    return sigmoid(this.margin(this.vectorize(record)));
  };

  /* rows: arrays in `features` order, as stored in replay.json. */
  DelayModel.prototype.predictRow = function (features, row) {
    var rec = {};
    for (var i = 0; i < features.length; i++) rec[features[i]] = row[i];
    return this.predict(rec);
  };

  root.DelayModel = DelayModel;
  if (typeof module !== "undefined" && module.exports) module.exports = DelayModel;
})(typeof globalThis !== "undefined" ? globalThis : this);
