import pytest

from flight_delay.data import load_data
from flight_delay.features import engineer_features


@pytest.fixture(scope="session")
def raw():
    return load_data()


@pytest.fixture(scope="session")
def featured(raw):
    return engineer_features(raw)
