# Flight Delay Prediction

Predicts whether a flight leaving New York will depart **15 minutes or more late**, the U.S. Department of
Transportation's definition of a delay, using only information known about an hour before departure.

**Live dashboard:** https://akwasinyarko.github.io/Flight_Delay_Prediction/

The dashboard runs the trained XGBoost model directly in the browser. There's no server and nothing to install.

![Dashboard overview](reports/screenshots/1-overview.png)

Built by Setornam Anyormi and Akwasi Nyarko for Intro. to A.I.

## Results

Scored on 101,328 test flights (days 22–31 of every month) that no model saw during training or tuning.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline (always "on time") | 0.771 | 0.000 | 0.000 | 0.000 | 0.500 |
| Logistic Regression | 0.695 | 0.399 | 0.664 | 0.499 | 0.750 |
| Random Forest | 0.737 | 0.446 | 0.615 | 0.517 | 0.764 |
| **XGBoost** | **0.733** | **0.442** | **0.629** | **0.519** | **0.765** |
| XGBoost, schedule + weather only | 0.694 | 0.393 | 0.619 | 0.480 | 0.733 |

- The baseline has the highest accuracy and catches no delays, which is why we judge on F1 and ROC-AUC.
- Recent delays at the airport (the last row removes them) add about 0.03 AUC.
- The strongest signals are the departure hour, recent airport delays, and the airline.

## The dashboard

| Tab | What it does |
| --- | --- |
| Overview | A departures board of real test flights: the model's live risk next to what actually happened |
| Predict a flight | Pick a route, airline, date, time, weather and airport conditions; see the delay probability, risk by hour and what-if comparisons |
| Explore the data | Delay rates by hour, month, weekday, visibility, precipitation and airline, filterable by airport and airline |
| Model results | Metrics table, ROC curves, confusion matrix, permutation feature importance |
| Replay test flights | 2,000 test flights, searchable and filterable by result (delay caught, false alarm, and so on) |

## How it works

1. **Data** (`data/`): every 2013 domestic departure from JFK, LGA and EWR ([nycflights13](https://github.com/hadley/nycflights13):
   U.S. BTS on-time data, NOAA hourly weather, FAA aircraft registry). Cancelled flights are excluded.
2. **Features** (`flight_delay/features.py`): 22 inputs known before departure. They cover the schedule (hour, weekday, month,
   days to a holiday), the flight (airline, destination, distance, aircraft age and seats), the weather at the origin
   that hour, airport congestion, and the average delay of flights scheduled 2–3 hours earlier at the same airport.
3. **Split** (time-based, inside every month): train on days 1–17, tune the decision threshold on days 18–21, and
   test on days 22–31. Every season is in training, and every test flight comes after its training data.
4. **Models** (`flight_delay/models.py`): Logistic Regression, Random Forest and XGBoost (400 trees, depth 7),
   with class weighting for the 22% delay rate and an F1-tuned threshold.
5. **Export** (`flight_delay/export.py`): writes the XGBoost trees and small summary files to `docs/data/`.
   `docs/js/model.js` re-implements the preprocessing and tree evaluation in JavaScript. A test checks that it
   matches Python to within 0.0001 on 1,000 test flights.

## Run it yourself

```bash
pip install -r requirements.txt
python -m flight_delay.train            # about 1 minute: trains, evaluates, writes figures and dashboard data
python -m http.server --directory docs  # then open http://localhost:8000
```

Run the tests (feature checks, JavaScript-vs-Python parity, headless-browser dashboard test):

```bash
python -m playwright install chromium   # once
python -m pytest
```

## Publishing on GitHub Pages

In the repository, open **Settings → Pages**. Under **Build and deployment**, choose **Deploy from a branch**, then
the **main** branch and the **/docs** folder, and click **Save**. The site appears at the link above within a minute
or two. After retraining, commit the updated `docs/data/` folder to refresh the live site.

## Repository layout

```
data/                 raw CSVs (flights zipped)
flight_delay/         Python package: config, data, features, models, charts, export, train
tests/                pytest suite + parity.js (Node runner for the browser model)
docs/                 the GitHub Pages site (index.html, css/, js/, data/, vendor/Chart.js)
docs/superpowers/specs/  design spec for this project
reports/              figures and model_results.csv from the last training run, dashboard screenshots
```

## Limitations

- One year (2013) and three airports. Patterns may have shifted since.
- Weather is measured at the departure airport only, not along the route or at the destination.
- About 24% of flights that leave on time still get a delay warning (false alarms), so it suits early warnings,
  not automatic decisions.
- In the predictor, unset inputs use the typical 2013 value for that airport, hour and month.

## Sources

- Carvalho, L., Sternberg, A., et al. (2020). On the relevance of data science for flight delay research: a systematic review. *Transport Reviews*. doi:10.1080/01441647.2020.1861123
- Hatıpoğlu, I., & Tosun, Ö. (2024). Predictive modeling of flight delays at an airport using machine learning methods. *Applied Sciences*, 14(13), 5472.
- Kiliç, K., & Sallan, J. M. (2023). Study of delay prediction in the US airport network. *Aerospace*, 10(4), 342. doi:10.3390/aerospace10040342
- Ball, M., et al. (2010). *Total Delay Impact Study*. NEXTOR, for the FAA.
- Chen, T., & Guestrin, C. (2016). XGBoost: a scalable tree boosting system. *KDD ’16*.
- Chart.js 4.4.1 (MIT), bundled in `docs/vendor/`.
