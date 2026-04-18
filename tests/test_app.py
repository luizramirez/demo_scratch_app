import json
from unittest.mock import patch
import pytest
from app import app, degrees_to_compass, celsius_to_fahrenheit, knots_to_mph, decode_visibility

SAMPLE_METAR = [{
    "icaoId": "KJFK",
    "name": "New York/JF Kennedy Intl, NY, US",
    "obsTime": 1776516660,
    "temp": 15.6,
    "dewp": 8.9,
    "wdir": 100,
    "wspd": 11,
    "wgst": None,
    "visib": "10+",
    "altim": 1018.7,
    "wxString": None,
    "clouds": [{"cover": "FEW", "base": 900}, {"cover": "SCT", "base": 25000}],
    "rawOb": "METAR KJFK 181251Z 10011KT 10SM FEW009 SCT250 16/09 A3008",
}]


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_homepage(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"METAR" in r.data


def test_metar_success(client):
    with patch("app.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = SAMPLE_METAR
        mock_get.return_value.raise_for_status = lambda: None

        r = client.get("/api/metar/KJFK")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["icao"] == "KJFK"
        assert "60" in data["temperature"]
        assert "East" in data["wind"]


def test_metar_not_found(client):
    with patch("app.requests.get") as mock_get:
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status = lambda: None

        r = client.get("/api/metar/ZZZZ")
        assert r.status_code == 404
        assert b"No METAR data found" in r.data


def test_invalid_code(client):
    r = client.get("/api/metar/123")
    assert r.status_code == 400


def test_degrees_to_compass():
    assert degrees_to_compass(0) == "North"
    assert degrees_to_compass(90) == "East"
    assert degrees_to_compass(180) == "South"
    assert degrees_to_compass(270) == "West"
    assert degrees_to_compass(None) == "variable"


def test_celsius_to_fahrenheit():
    assert celsius_to_fahrenheit(0) == 32
    assert celsius_to_fahrenheit(100) == 212
    assert celsius_to_fahrenheit(None) is None


def test_knots_to_mph():
    assert knots_to_mph(10) == 12
    assert knots_to_mph(None) is None


def test_decode_visibility():
    assert "more than" in decode_visibility("10+")
    assert "excellent" in decode_visibility(10)
    assert "poor" in decode_visibility(0.5)
