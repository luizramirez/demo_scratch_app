"""
METAR Reader — Flask web application that fetches live METAR weather reports
from aviationweather.gov and translates them into plain English.
"""

from flask import Flask, render_template, jsonify
import requests
from datetime import datetime, timezone

app = Flask(__name__)

METAR_API = "https://aviationweather.gov/api/data/metar"

# 16-point compass rose, each segment covers 22.5 degrees
WIND_DIRS = [
    "North", "North-Northeast", "Northeast", "East-Northeast",
    "East", "East-Southeast", "Southeast", "South-Southeast",
    "South", "South-Southwest", "Southwest", "West-Southwest",
    "West", "West-Northwest", "Northwest", "North-Northwest"
]

CLOUD_DESCRIPTIONS = {
    "SKC": "clear skies",
    "CLR": "clear skies",
    "CAVOK": "clear skies, excellent visibility",
    "FEW": "a few clouds",
    "SCT": "scattered clouds",
    "BKN": "mostly cloudy (broken)",
    "OVC": "overcast (completely cloudy)",
    "VV": "sky obscured",
}

# Standard METAR present weather codes (WMO and FAA)
WEATHER_CODES = {
    "RA": "rain", "SN": "snow", "DZ": "drizzle", "GR": "hail",
    "GS": "small hail", "IC": "ice crystals", "PL": "ice pellets",
    "SG": "snow grains", "UP": "unknown precipitation",
    "FG": "fog", "BR": "mist", "HZ": "haze", "FU": "smoke",
    "DU": "dust", "SA": "sand", "VA": "volcanic ash",
    "SQ": "squalls", "PO": "dust whirls", "DS": "duststorm",
    "SS": "sandstorm", "FC": "funnel cloud / tornado",
    "TS": "thunderstorm", "SHRA": "rain showers", "SHSN": "snow showers",
    "TSRA": "thunderstorm with rain", "FZRA": "freezing rain",
    "FZDZ": "freezing drizzle", "FZFG": "freezing fog",
    "RASN": "rain and snow mix", "-": "light", "+": "heavy",
}


def degrees_to_compass(degrees):
    """Convert a wind direction in degrees to a compass direction string.

    Args:
        degrees: Wind direction in degrees (0–360), or None for variable winds.

    Returns:
        A compass direction string such as "North" or "Southwest",
        or "variable" if degrees is None.
    """
    if degrees is None:
        return "variable"
    idx = round(degrees / 22.5) % 16
    return WIND_DIRS[idx]


def celsius_to_fahrenheit(c):
    """Convert a Celsius temperature to Fahrenheit, rounded to the nearest degree.

    Args:
        c: Temperature in Celsius, or None.

    Returns:
        Temperature in Fahrenheit as an integer, or None if input is None.
    """
    if c is None:
        return None
    return round(c * 9 / 5 + 32)


def knots_to_mph(knots):
    """Convert a wind speed in knots to miles per hour, rounded to the nearest integer.

    Args:
        knots: Wind speed in knots, or None.

    Returns:
        Wind speed in mph as an integer, or None if input is None.
    """
    if knots is None:
        return None
    return round(knots * 1.15078)


def decode_visibility(vis_str):
    """Convert a raw METAR visibility value to a human-readable string.

    Visibility in METARs is reported in statute miles. A trailing "+"
    means the actual visibility exceeds the reported value (e.g. "10+").

    Args:
        vis_str: Visibility string from the API (e.g. "10+", "2.5"), or None.

    Returns:
        A descriptive string such as "more than 10 miles" or "2.5 miles (reduced)".
    """
    if vis_str is None:
        return "unknown"
    if str(vis_str).endswith("+"):
        return f"more than {vis_str[:-1]} miles"
    try:
        val = float(vis_str)
        if val >= 10:
            return "10+ miles (excellent)"
        elif val >= 5:
            return f"{val} miles (good)"
        elif val >= 3:
            return f"{val} miles (moderate)"
        elif val >= 1:
            return f"{val} miles (reduced)"
        else:
            return f"{val} miles (poor)"
    except (ValueError, TypeError):
        return str(vis_str) + " miles"


def decode_clouds(clouds, wx_string):
    """Convert a list of cloud layer objects into a readable sky condition string.

    Args:
        clouds: List of dicts with "cover" (e.g. "FEW") and "base" (feet AGL).
        wx_string: Raw weather string (unused here, reserved for future use).

    Returns:
        A string describing all cloud layers, e.g.
        "a few clouds at 2,500 ft; scattered clouds at 10,000 ft".
    """
    if not clouds:
        return "clear skies"
    parts = []
    for layer in clouds:
        cover = layer.get("cover", "")
        base = layer.get("base")
        desc = CLOUD_DESCRIPTIONS.get(cover, cover)
        if base:
            parts.append(f"{desc} at {base:,} ft")
        else:
            parts.append(desc)
    return "; ".join(parts) if parts else "clear skies"


def decode_weather(wx_string):
    """Translate a METAR present-weather string into plain English.

    Scans the raw weather string for known METAR codes and returns
    a comma-separated list of matching descriptions.

    Args:
        wx_string: Raw present-weather string (e.g. "TSRA", "-SN"), or None.

    Returns:
        A readable string such as "thunderstorm, rain", the original
        wx_string if no codes matched, or None if wx_string is falsy.
    """
    if not wx_string:
        return None
    result = []
    for code, meaning in WEATHER_CODES.items():
        if code in wx_string:
            result.append(meaning)
    if result:
        seen = []
        for r in result:
            if r not in seen:
                seen.append(r)
        return ", ".join(seen)
    return wx_string


def overall_condition(clouds, wx_string, vis_str):
    """Derive a one-phrase sky condition summary from clouds and weather codes.

    Args:
        clouds: List of cloud layer dicts (see decode_clouds).
        wx_string: Raw present-weather string, or None.
        vis_str: Visibility string (currently unused, reserved for future use).

    Returns:
        A short condition label such as "Clear", "Partly cloudy", or "Overcast".
    """
    wx = decode_weather(wx_string)
    if wx:
        return wx.capitalize()
    if not clouds:
        return "Clear"
    top_cover = clouds[0].get("cover", "") if clouds else ""
    if top_cover in ("SKC", "CLR", "CAVOK"):
        return "Clear"
    elif top_cover == "FEW":
        return "Mostly clear"
    elif top_cover == "SCT":
        return "Partly cloudy"
    elif top_cover == "BKN":
        return "Mostly cloudy"
    elif top_cover == "OVC":
        return "Overcast"
    return "Mixed conditions"


def condition_emoji(condition, wx_string):
    """Pick a weather emoji that best represents the current conditions.

    Args:
        condition: Condition label returned by overall_condition().
        wx_string: Raw present-weather string, or None.

    Returns:
        A single emoji string.
    """
    wx = (wx_string or "").upper()
    cond = condition.lower()
    if "thunder" in cond or "TS" in wx:
        return "⛈️"
    if "snow" in cond or "SN" in wx:
        return "❄️"
    if "freezing" in cond or "FZ" in wx:
        return "🌨️"
    if "rain" in cond or "RA" in wx or "DZ" in wx:
        return "🌧️"
    if "fog" in cond or "FG" in wx or "mist" in cond or "BR" in wx:
        return "🌫️"
    if "haze" in cond or "HZ" in wx:
        return "😶‍🌫️"
    if "overcast" in cond:
        return "☁️"
    if "mostly cloudy" in cond:
        return "🌥️"
    if "partly cloudy" in cond or "scattered" in cond:
        return "⛅"
    return "☀️"


def format_time(obs_time):
    """Format a Unix timestamp as a readable UTC date-time string.

    Args:
        obs_time: Unix timestamp (integer), or None.

    Returns:
        A string like "April 18, 2026 at 12:51z (UTC)", or "Unknown time".
    """
    try:
        dt = datetime.fromtimestamp(obs_time, tz=timezone.utc)
        return dt.strftime("%B %d, %Y at %H:%Mz (UTC)")
    except Exception:
        return "Unknown time"


def build_friendly_summary(data):
    """Build a complete plain-English weather summary from a raw METAR data dict.

    Converts all numeric and coded fields into human-readable values and
    assembles them into a structured dict suitable for JSON serialization.

    Args:
        data: A single METAR record dict as returned by aviationweather.gov.

    Returns:
        A dict with keys: airport_name, icao, observed, emoji, condition,
        temperature, dewpoint, wind, visibility, clouds, weather, altimeter,
        raw, headline.
    """
    temp_c = data.get("temp")
    dewp_c = data.get("dewp")
    wdir = data.get("wdir")
    wspd = data.get("wspd")
    wgst = data.get("wgst")
    visib = data.get("visib")
    altim = data.get("altim")
    wx_string = data.get("wxString")
    clouds = data.get("clouds", [])
    obs_time = data.get("obsTime")
    name = data.get("name", "Unknown Airport")
    icao = data.get("icaoId", "")

    temp_f = celsius_to_fahrenheit(temp_c)
    dewp_f = celsius_to_fahrenheit(dewp_c)
    wspd_mph = knots_to_mph(wspd)
    wgst_mph = knots_to_mph(wgst)
    compass = degrees_to_compass(wdir)
    condition = overall_condition(clouds, wx_string, visib)
    emoji = condition_emoji(condition, wx_string)

    wind_desc = "Calm"
    if wspd and wspd > 0:
        wind_desc = f"From the {compass} at {wspd_mph} mph"
        if wgst_mph:
            wind_desc += f", gusting to {wgst_mph} mph"

    summary = {
        "airport_name": name,
        "icao": icao,
        "observed": format_time(obs_time),
        "emoji": emoji,
        "condition": condition,
        "temperature": f"{temp_f}°F / {temp_c}°C" if temp_f is not None else "Unknown",
        "dewpoint": f"{dewp_f}°F / {dewp_c}°C" if dewp_f is not None else "Unknown",
        "wind": wind_desc,
        "visibility": decode_visibility(visib),
        "clouds": decode_clouds(clouds, wx_string),
        "weather": decode_weather(wx_string),
        "altimeter": f"{altim:.2f} inHg" if altim else "Unknown",
        "raw": data.get("rawOb", ""),
        "headline": build_headline(condition, temp_f, wspd_mph, compass, decode_weather(wx_string)),
    }
    return summary


def build_headline(condition, temp_f, wspd_mph, compass, wx_desc):
    """Build a one-line weather summary sentence for display at the top of the card.

    Args:
        condition: Short condition label (e.g. "Partly cloudy").
        temp_f: Temperature in Fahrenheit, or None.
        wspd_mph: Wind speed in mph, or None.
        compass: Compass direction string (e.g. "Southwest").
        wx_desc: Decoded present-weather string, or None.

    Returns:
        A comma-separated summary string such as
        "Partly cloudy, 72°F, winds 10 mph from the Southwest".
    """
    parts = []
    if wx_desc:
        parts.append(wx_desc.capitalize())
    else:
        parts.append(condition)
    if temp_f is not None:
        parts.append(f"{temp_f}°F")
    if wspd_mph and wspd_mph > 0:
        parts.append(f"winds {wspd_mph} mph from the {compass}")
    elif wspd_mph == 0:
        parts.append("calm winds")
    return ", ".join(parts)


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/metar/<code>")
def get_metar(code):
    """Fetch and decode a METAR report for the given airport code.

    Accepts 2–4 letter ICAO or IATA codes (e.g. KJFK, LAX).
    Returns a JSON object with plain-English weather fields on success,
    or a JSON error object with an appropriate HTTP status code on failure.
    """
    code = code.upper().strip()
    if not (2 <= len(code) <= 4 and code.isalpha()):
        return jsonify({
            "error": "Please enter a valid 3- or 4-letter airport code (e.g. KJFK or LAX)."
        }), 400

    try:
        resp = requests.get(
            METAR_API,
            params={"ids": code, "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return jsonify({"error": "The weather service took too long to respond. Try again."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not reach the weather service: {str(e)}"}), 502

    try:
        results = resp.json()
    except ValueError:
        return jsonify({"error": "Received an unexpected response from the weather service."}), 502

    if not results:
        return jsonify({
            "error": f"No METAR data found for '{code}'. Check the airport code and try again."
        }), 404

    return jsonify(build_friendly_summary(results[0]))


if __name__ == "__main__":
    app.run(debug=True)
