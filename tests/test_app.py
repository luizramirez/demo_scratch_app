"""
Test suite for the METAR Reader Flask application.

Organised into four sections:
  1. Fixtures            — reusable mock METAR records for each weather scenario
  2. Route tests         — HTTP behaviour of / and /api/metar/<code>
  3. Decoder unit tests  — each decoding helper tested in isolation
  4. Scenario tests      — full build_friendly_summary output for realistic METARs
  5. Edge case tests     — missing / None / extreme field values
"""

import json
from unittest.mock import patch, MagicMock
import pytest

from app import (
    app,
    degrees_to_compass,
    celsius_to_fahrenheit,
    knots_to_mph,
    decode_visibility,
    decode_clouds,
    decode_weather,
    overall_condition,
    condition_emoji,
    build_headline,
    build_friendly_summary,
)


# ---------------------------------------------------------------------------
# 1. Fixtures — mock METAR records
# ---------------------------------------------------------------------------

def metar(overrides=None):
    """Return a minimal valid METAR dict, with optional field overrides."""
    base = {
        "icaoId": "KXXX",
        "name": "Test Airport, US",
        "obsTime": 1776516660,
        "temp": 20.0,
        "dewp": 10.0,
        "wdir": 270,
        "wspd": 10,
        "wgst": None,
        "visib": "10+",
        "altim": 1013.2,
        "wxString": None,
        "clouds": [],
        "rawOb": "METAR KXXX 010000Z 27010KT 10SM SKC 20/10 A2992",
    }
    if overrides:
        base.update(overrides)
    return base


CLEAR_CALM = metar({
    "wdir": 0, "wspd": 0,
    "clouds": [{"cover": "SKC", "base": None}],
})

PARTLY_CLOUDY = metar({
    "wdir": 180, "wspd": 8,
    "clouds": [{"cover": "FEW", "base": 3000}, {"cover": "SCT", "base": 8000}],
})

OVERCAST_IFR = metar({
    "temp": 5.0, "dewp": 4.0,
    "wdir": 90, "wspd": 15, "wgst": 25,
    "visib": "1",
    "clouds": [{"cover": "OVC", "base": 400}],
})

THUNDERSTORM = metar({
    "temp": 28.0, "dewp": 22.0,
    "wdir": 220, "wspd": 20, "wgst": 35,
    "visib": "2",
    "wxString": "TSRA",
    "clouds": [{"cover": "BKN", "base": 1500}, {"cover": "OVC", "base": 3000}],
})

SNOW = metar({
    "temp": -3.0, "dewp": -5.0,
    "wdir": 340, "wspd": 12,
    "visib": "1.5",
    "wxString": "SN",
    "clouds": [{"cover": "OVC", "base": 800}],
})

FREEZING_FOG = metar({
    "temp": -1.0, "dewp": -1.0,
    "wdir": None, "wspd": 0,
    "visib": "0.25",
    "wxString": "FZFG",
    "clouds": [{"cover": "OVC", "base": 100}],
})

LIGHT_RAIN = metar({
    "wdir": 135, "wspd": 6,
    "visib": "5",
    "wxString": "-RA",
    "clouds": [{"cover": "BKN", "base": 2500}],
})

GUSTING_CROSSWIND = metar({
    "wdir": 45, "wspd": 18, "wgst": 32,
    "clouds": [{"cover": "FEW", "base": 5000}],
})


# ---------------------------------------------------------------------------
# 2. Route tests
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def mock_api(data):
    """Return a mock requests.get return value that yields the given data."""
    m = MagicMock()
    m.json.return_value = [data] if isinstance(data, dict) else data
    m.raise_for_status = lambda: None
    return m


def test_homepage_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"METAR" in r.data


def test_metar_endpoint_success(client):
    with patch("app.requests.get", return_value=mock_api(CLEAR_CALM)):
        r = client.get("/api/metar/KXXX")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["icao"] == "KXXX"


def test_metar_endpoint_not_found(client):
    with patch("app.requests.get", return_value=mock_api([])):
        r = client.get("/api/metar/ZZZZ")
    assert r.status_code == 404
    assert b"No METAR data found" in r.data


def test_metar_endpoint_invalid_code_digits(client):
    r = client.get("/api/metar/123")
    assert r.status_code == 400


def test_metar_endpoint_invalid_code_too_long(client):
    r = client.get("/api/metar/TOOLONG")
    assert r.status_code == 400


def test_metar_endpoint_lowercase_code_accepted(client):
    """Airport codes should be case-insensitive."""
    with patch("app.requests.get", return_value=mock_api(CLEAR_CALM)):
        r = client.get("/api/metar/kxxx")
    assert r.status_code == 200


def test_metar_endpoint_timeout(client):
    import requests as req
    with patch("app.requests.get", side_effect=req.exceptions.Timeout):
        r = client.get("/api/metar/KXXX")
    assert r.status_code == 504


def test_metar_endpoint_connection_error(client):
    import requests as req
    with patch("app.requests.get", side_effect=req.exceptions.ConnectionError):
        r = client.get("/api/metar/KXXX")
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# 3. Decoder unit tests
# ---------------------------------------------------------------------------

class TestDegreesToCompass:
    def test_cardinal_north(self):
        assert degrees_to_compass(0) == "North"

    def test_cardinal_north_360(self):
        assert degrees_to_compass(360) == "North"

    def test_cardinal_east(self):
        assert degrees_to_compass(90) == "East"

    def test_cardinal_south(self):
        assert degrees_to_compass(180) == "South"

    def test_cardinal_west(self):
        assert degrees_to_compass(270) == "West"

    def test_intercardinal_northeast(self):
        assert degrees_to_compass(45) == "Northeast"

    def test_intercardinal_southwest(self):
        assert degrees_to_compass(225) == "Southwest"

    def test_none_returns_variable(self):
        assert degrees_to_compass(None) == "variable"


class TestCelsiusToFahrenheit:
    def test_freezing_point(self):
        assert celsius_to_fahrenheit(0) == 32

    def test_boiling_point(self):
        assert celsius_to_fahrenheit(100) == 212

    def test_body_temperature(self):
        assert celsius_to_fahrenheit(37) == 99

    def test_negative_temperature(self):
        assert celsius_to_fahrenheit(-40) == -40

    def test_none_returns_none(self):
        assert celsius_to_fahrenheit(None) is None


class TestKnotsToMph:
    def test_ten_knots(self):
        assert knots_to_mph(10) == 12

    def test_zero_knots(self):
        assert knots_to_mph(0) == 0

    def test_none_returns_none(self):
        assert knots_to_mph(None) is None


class TestDecodeVisibility:
    def test_greater_than_ten(self):
        assert "more than" in decode_visibility("10+")

    def test_ten_miles(self):
        assert "excellent" in decode_visibility(10)

    def test_good_visibility(self):
        assert "good" in decode_visibility(6)

    def test_moderate_visibility(self):
        assert "moderate" in decode_visibility(4)

    def test_reduced_visibility(self):
        assert "reduced" in decode_visibility(1.5)

    def test_poor_visibility(self):
        assert "poor" in decode_visibility(0.25)

    def test_none_returns_unknown(self):
        assert decode_visibility(None) == "unknown"


class TestDecodeClouds:
    def test_no_layers_is_clear(self):
        assert decode_clouds([], None) == "clear skies"

    def test_sky_clear_code(self):
        assert "clear" in decode_clouds([{"cover": "SKC", "base": None}], None)

    def test_few_clouds_with_base(self):
        result = decode_clouds([{"cover": "FEW", "base": 3000}], None)
        assert "a few clouds" in result
        assert "3,000 ft" in result

    def test_overcast_with_base(self):
        result = decode_clouds([{"cover": "OVC", "base": 400}], None)
        assert "overcast" in result
        assert "400 ft" in result

    def test_multiple_layers(self):
        layers = [{"cover": "FEW", "base": 2000}, {"cover": "BKN", "base": 8000}]
        result = decode_clouds(layers, None)
        assert "a few clouds" in result
        assert "mostly cloudy" in result
        assert "2,000 ft" in result
        assert "8,000 ft" in result


class TestDecodeWeather:
    def test_none_returns_none(self):
        assert decode_weather(None) is None

    def test_empty_string_returns_none(self):
        assert decode_weather("") is None

    def test_rain(self):
        assert "rain" in decode_weather("RA")

    def test_snow(self):
        assert "snow" in decode_weather("SN")

    def test_thunderstorm_with_rain(self):
        result = decode_weather("TSRA")
        assert "thunderstorm" in result
        assert "rain" in result

    def test_freezing_rain(self):
        assert "freezing rain" in decode_weather("FZRA")

    def test_fog(self):
        assert "fog" in decode_weather("FG")

    def test_light_rain_prefix(self):
        result = decode_weather("-RA")
        assert "rain" in result

    def test_no_duplicates_in_output(self):
        result = decode_weather("TSRA")
        parts = result.split(", ")
        assert len(parts) == len(set(parts))


class TestOverallCondition:
    def test_clear_no_clouds(self):
        assert overall_condition([], None, "10+") == "Clear"

    def test_clear_skc_code(self):
        assert overall_condition([{"cover": "SKC", "base": None}], None, "10+") == "Clear"

    def test_mostly_clear_few(self):
        assert overall_condition([{"cover": "FEW", "base": 3000}], None, "10+") == "Mostly clear"

    def test_partly_cloudy_sct(self):
        assert overall_condition([{"cover": "SCT", "base": 5000}], None, "10+") == "Partly cloudy"

    def test_mostly_cloudy_bkn(self):
        assert overall_condition([{"cover": "BKN", "base": 2000}], None, "10+") == "Mostly cloudy"

    def test_overcast_ovc(self):
        assert overall_condition([{"cover": "OVC", "base": 800}], None, "10+") == "Overcast"

    def test_weather_code_overrides_clouds(self):
        """Active precipitation takes priority over the cloud description."""
        result = overall_condition([{"cover": "OVC", "base": 800}], "TSRA", "2")
        assert "thunder" in result.lower() or "rain" in result.lower()


class TestConditionEmoji:
    def test_thunderstorm(self):
        assert condition_emoji("Thunderstorm with rain", "TSRA") == "⛈️"

    def test_snow(self):
        assert condition_emoji("Snow", "SN") == "❄️"

    def test_freezing(self):
        assert condition_emoji("Freezing rain", "FZRA") == "🌨️"

    def test_rain(self):
        assert condition_emoji("Rain", "RA") == "🌧️"

    def test_fog(self):
        assert condition_emoji("Fog", "FG") == "🌫️"

    def test_overcast(self):
        assert condition_emoji("Overcast", None) == "☁️"

    def test_mostly_cloudy(self):
        assert condition_emoji("Mostly cloudy", None) == "🌥️"

    def test_partly_cloudy(self):
        assert condition_emoji("Partly cloudy", None) == "⛅"

    def test_clear(self):
        assert condition_emoji("Clear", None) == "☀️"


class TestBuildHeadline:
    def test_includes_condition(self):
        assert "Clear" in build_headline("Clear", 72, 10, "West", None)

    def test_includes_temperature(self):
        assert "72°F" in build_headline("Clear", 72, 10, "West", None)

    def test_includes_wind(self):
        result = build_headline("Clear", 72, 10, "West", None)
        assert "10 mph" in result
        assert "West" in result

    def test_calm_winds(self):
        assert "calm" in build_headline("Clear", 72, 0, "North", None).lower()

    def test_weather_overrides_condition(self):
        result = build_headline("Rain", 65, 8, "South", "rain")
        assert result.startswith("Rain")

    def test_missing_temperature(self):
        result = build_headline("Clear", None, 10, "West", None)
        assert "°F" not in result


# ---------------------------------------------------------------------------
# 4. Scenario tests — full METAR interpretation
# ---------------------------------------------------------------------------

class TestClearCalmScenario:
    """Clear sky, no wind — a perfect VFR day."""

    def setup_method(self):
        self.result = build_friendly_summary(CLEAR_CALM)

    def test_condition_is_clear(self):
        assert "clear" in self.result["condition"].lower()

    def test_wind_is_calm(self):
        assert self.result["wind"].lower() == "calm"

    def test_emoji_is_sunny(self):
        assert self.result["emoji"] == "☀️"

    def test_no_weather_event(self):
        assert self.result["weather"] is None

    def test_temperature_in_fahrenheit(self):
        assert "68°F" in self.result["temperature"]


class TestThunderstormScenario:
    """Active thunderstorm with rain, gusty winds, reduced visibility."""

    def setup_method(self):
        self.result = build_friendly_summary(THUNDERSTORM)

    def test_weather_mentions_thunderstorm(self):
        assert "thunderstorm" in self.result["weather"].lower()

    def test_weather_mentions_rain(self):
        assert "rain" in self.result["weather"].lower()

    def test_emoji_is_storm(self):
        assert self.result["emoji"] == "⛈️"

    def test_wind_mentions_gusts(self):
        assert "gusting" in self.result["wind"].lower()

    def test_visibility_is_reduced(self):
        assert "reduced" in self.result["visibility"]

    def test_headline_leads_with_weather(self):
        assert "thunderstorm" in self.result["headline"].lower()


class TestSnowScenario:
    """Snowfall with below-freezing temperatures."""

    def setup_method(self):
        self.result = build_friendly_summary(SNOW)

    def test_weather_mentions_snow(self):
        assert "snow" in self.result["weather"].lower()

    def test_emoji_is_snow(self):
        assert self.result["emoji"] == "❄️"

    def test_temperature_is_below_freezing(self):
        temp_f = int(self.result["temperature"].split("°F")[0])
        assert temp_f < 32

    def test_visibility_is_reduced(self):
        assert "reduced" in self.result["visibility"]


class TestFreezingFogScenario:
    """Freezing fog, variable winds, near-zero visibility."""

    def setup_method(self):
        self.result = build_friendly_summary(FREEZING_FOG)

    def test_weather_mentions_freezing_fog(self):
        assert "freezing fog" in self.result["weather"].lower()

    def test_emoji_is_fog(self):
        assert self.result["emoji"] in ("🌫️", "🌨️")

    def test_wind_is_calm_or_variable(self):
        wind = self.result["wind"].lower()
        assert "calm" in wind or "variable" in wind

    def test_visibility_is_poor(self):
        assert "poor" in self.result["visibility"]


class TestOvercastIFRScenario:
    """Low overcast, reduced visibility, strong gusty winds — IFR conditions."""

    def setup_method(self):
        self.result = build_friendly_summary(OVERCAST_IFR)

    def test_condition_is_overcast(self):
        assert "overcast" in self.result["condition"].lower()

    def test_cloud_base_is_low(self):
        assert "400 ft" in self.result["clouds"]

    def test_emoji_is_cloudy(self):
        assert self.result["emoji"] == "☁️"

    def test_wind_mentions_gusts(self):
        assert "gusting" in self.result["wind"].lower()

    def test_visibility_is_reduced(self):
        assert "reduced" in self.result["visibility"] or "poor" in self.result["visibility"]


class TestGustingCrosswindScenario:
    """Clear sky but strong gusting winds from the northeast."""

    def setup_method(self):
        self.result = build_friendly_summary(GUSTING_CROSSWIND)

    def test_wind_direction_is_northeast(self):
        assert "Northeast" in self.result["wind"]

    def test_wind_mentions_gusts(self):
        assert "gusting" in self.result["wind"].lower()

    def test_gust_speed_in_mph(self):
        assert "37 mph" in self.result["wind"]

    def test_emoji_is_sunny(self):
        assert self.result["emoji"] == "☀️"


class TestPartlyCloudyScenario:
    """Few and scattered clouds, mild southerly breeze."""

    def setup_method(self):
        self.result = build_friendly_summary(PARTLY_CLOUDY)

    def test_condition_is_mostly_clear(self):
        assert "clear" in self.result["condition"].lower()

    def test_clouds_describe_both_layers(self):
        assert "3,000 ft" in self.result["clouds"]
        assert "8,000 ft" in self.result["clouds"]

    def test_wind_is_from_south(self):
        assert "South" in self.result["wind"]

    def test_emoji_is_partly_cloudy(self):
        assert self.result["emoji"] in ("⛅", "🌥️", "☀️")


# ---------------------------------------------------------------------------
# 5. Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_missing_temperature_shows_unknown(self):
        result = build_friendly_summary(metar({"temp": None, "dewp": None}))
        assert result["temperature"] == "Unknown"
        assert result["dewpoint"] == "Unknown"

    def test_missing_altimeter_shows_unknown(self):
        result = build_friendly_summary(metar({"altim": None}))
        assert result["altimeter"] == "Unknown"

    def test_zero_wind_speed_is_calm(self):
        result = build_friendly_summary(metar({"wspd": 0}))
        assert result["wind"].lower() == "calm"

    def test_variable_wind_direction(self):
        result = build_friendly_summary(metar({"wdir": None, "wspd": 5}))
        assert "variable" in result["wind"].lower()

    def test_no_clouds_field_defaults_to_clear(self):
        result = build_friendly_summary(metar({"clouds": []}))
        assert "clear" in result["clouds"].lower()

    def test_unknown_cloud_cover_code_passes_through(self):
        result = build_friendly_summary(metar({"clouds": [{"cover": "XYZ", "base": 1000}]}))
        assert "XYZ" in result["clouds"]

    def test_airport_name_in_summary(self):
        result = build_friendly_summary(metar({"name": "My Test Airport"}))
        assert result["airport_name"] == "My Test Airport"

    def test_raw_metar_preserved(self):
        raw = "METAR KXXX 010000Z 27010KT 10SM SKC 20/10 A2992"
        result = build_friendly_summary(metar({"rawOb": raw}))
        assert result["raw"] == raw
