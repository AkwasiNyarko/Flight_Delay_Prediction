"""The browser model (docs/js/model.js) must match the trained Python model."""
import json
import shutil
import subprocess

import joblib
import numpy as np
import pytest

from flight_delay.config import MODEL_FEATURES, MODELS_DIR, ROOT, SITE_DATA_DIR
from flight_delay.export import feature_records
from flight_delay.features import time_split

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def test_js_model_matches_python(featured, tmp_path):
    bundle_path = MODELS_DIR / "xgb_delay_model.joblib"
    if not bundle_path.exists():
        pytest.skip("run `python -m flight_delay.train` first")
    model = joblib.load(bundle_path)["model"]
    _, _, test = time_split(featured)
    sample = test.sample(1000, random_state=1)
    expected = model.predict_proba(sample[MODEL_FEATURES])[:, 1]

    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps({"features": MODEL_FEATURES, "rows": feature_records(sample)}))
    out = subprocess.run(["node", str(ROOT / "tests" / "parity.js"),
                          str(SITE_DATA_DIR / "model.json"), str(rows)],
                         capture_output=True, text=True, check=True)
    got = np.array(json.loads(out.stdout))
    diff = np.abs(got - expected)
    assert diff.max() < 1e-4, f"max diff {diff.max():.2e}"
    # same yes/no decisions at the tuned threshold
    t = json.loads((SITE_DATA_DIR / "model.json").read_text())["threshold"]
    assert ((got >= t) == (expected >= t)).mean() > 0.999
