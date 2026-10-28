# Flight Delay Prediction — End-to-End Project and Dashboard

Date: 2026-10-27 · Authors: Setornam Anyormi, Akwasi Nyarko · Course: Intro. to A.I.

## Goal

Ship the course project as one reproducible repository with a public dashboard on GitHub Pages,
ready before the presentation on 2026-10-29. Anyone with the link can explore the data, see the
model's results, and get live predictions with nothing to install.

## Success criteria

- `python -m flight_delay.train` rebuilds every number in the slides from the raw data
  (XGBoost test AUC 0.765, recall 0.63, F1 0.52 on days 22–31 of every month).
- The dashboard loads from GitHub Pages with no server and no build step.
- Predictions in the browser come from the trained XGBoost model itself, not a lookup table,
  and match Python to within 0.0001 on 1,000 test flights.
- All tests pass, and a headless-browser test opens every tab without console errors.

## Constraints

- GitHub Pages serves static files only, so Python cannot run on the site.
- Data: nycflights13 (2013 departures from JFK, LGA and EWR; BTS, NOAA and FAA data), committed
  to the repo (about 11 MB).
- Only information known before departure may be a model input.

## Architecture

```
data/ (raw CSV) ──► flight_delay/ (Python package)
                     data.py      load + join flights, weather, planes
                     features.py  22 features, 15-min label, time split
                     models.py    LR / RF / XGBoost, threshold tuning, metrics
                     train.py     train, evaluate, save figures + model
                     export.py    write docs/data/*.json for the site
                         │
                         ▼
docs/ (GitHub Pages root)
  index.html, css/, js/app.js     dashboard UI, Chart.js from CDN
  js/model.js                     XGBoost tree evaluator (browser + Node)
  data/model.json                 trees, medians, one-hot categories, threshold
  data/summary.json               metrics, ROC, confusion matrix, importance
  data/explore.json               delay counts by airport × airline × dimension
  data/lookup.json                routes, names, typical airport state and weather
  data/replay.json                ~2,000 real test flights with their features
```

### Key decision: run the real model in the browser

The XGBoost trees are exported as compact JSON. `model.js` reproduces the scikit-learn
preprocessing (median imputation, one-hot encoding in the same column order) and walks each
tree the way XGBoost does: inputs and split values are compared as 32-bit floats, leaf values
are summed onto the base margin, and a sigmoid gives the probability. The preprocessor emits a
dense matrix, so zeros are real zeros, not missing values. A parity test is the safeguard.

Rejected alternatives: a precomputed lookup table (not the real model, can't cover every input
combination); a Python backend (GitHub Pages can't host one).

## Dashboard tabs

1. **Overview** — headline numbers and a short explanation of the project.
2. **Explore** — delay rate by hour, month, weekday, airline and weather, filterable by airport
   and airline. Computed in the browser from precomputed counts.
3. **Model results** — metrics table for all models and the baseline, ROC curves, confusion
   matrix, permutation feature importance.
4. **Predictor** — choose origin, destination (served routes only), airline, date, departure
   hour, weather and the airport's current delay level. Shows the probability, the verdict at
   the tuned threshold, and the risk across departure hours. Unset values default to the
   typical value for that airport, hour and month.
5. **Replay** — searchable test flights, each scored live and shown next to what happened.

## Error handling

- Missing JSON or a failed fetch shows a clear message on the page instead of a blank tab.
- An unknown category (e.g. a destination outside the top 30) maps to the same all-zero
  one-hot vector scikit-learn produces.
- Blank numeric inputs fall back to the training medians, as in Python.

## Testing

- `pytest`: label threshold, split has no overlapping days, no post-departure columns among
  model inputs, recent-delay features only use earlier hours.
- Parity: Python vs Node on 1,000 test flights, max difference < 1e-4.
- Smoke: Playwright opens each tab, makes a prediction, fails on any console error.

## Out of scope

Backend, user accounts, live flight feeds, retraining from the browser.
