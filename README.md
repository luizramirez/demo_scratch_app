# METAR Reader

A Flask web application that translates live airport weather reports (METARs) into plain English. Type any airport code and instantly get a friendly, readable weather summary — no aviation knowledge required.

![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![Flask](https://img.shields.io/badge/flask-3.x-lightgrey) ![CI](https://github.com/luizramirez/demo_scratch_app/actions/workflows/ci.yml/badge.svg)

---

## What is a METAR?

A METAR (Meteorological Aerodrome Report) is the standard format used worldwide for reporting current airport weather conditions. They look like this:

```
METAR KJFK 181251Z 10011KT 10SM FEW009 SCT250 16/09 A3008
```

METAR Reader decodes that into:

> ☀️ **Mostly clear, 60°F, winds 13 mph from the East**
>
> Temperature: 60°F / 15.6°C · Dew Point: 48°F · Visibility: 10+ miles (excellent)  
> Clouds: a few clouds at 900 ft; scattered clouds at 25,000 ft · Altimeter: 1018.70 inHg

---

## Features

- Live data from [aviationweather.gov](https://aviationweather.gov) — updated every 20–60 minutes
- Supports ICAO codes (`KJFK`) and most IATA codes (`LAX`)
- Translates wind direction, speed, gusts, visibility, cloud layers, and weather events
- Emoji-based condition at a glance (☀️ ⛅ 🌧️ ❄️ ⛈️ …)
- Raw METAR string shown alongside the plain-English summary
- Clean, mobile-friendly dark UI

---

## Installation

### Requirements

- Python 3.11 or higher
- pip

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/luizramirez/demo_scratch_app.git
cd demo_scratch_app
```

**2. Create and activate a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the app**

```bash
python app.py
```

Open your browser to [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Usage

1. Type an airport code into the search box (e.g. `KJFK`, `KLAX`, `EGLL`)
2. Press **Check Weather** or hit Enter
3. Read your plain-English weather report

You can also call the API directly:

```
GET /api/metar/<code>
```

Example:

```bash
curl http://127.0.0.1:5000/api/metar/KJFK
```

```json
{
  "icao": "KJFK",
  "airport_name": "New York/JF Kennedy Intl, NY, US",
  "headline": "Mostly clear, 60°F, winds 13 mph from the East",
  "temperature": "60°F / 15.6°C",
  "wind": "From the East at 13 mph",
  "visibility": "more than 10 miles",
  "clouds": "a few clouds at 900 ft; scattered clouds at 25,000 ft",
  "altimeter": "1018.70 inHg",
  "raw": "METAR KJFK 181251Z 10011KT 10SM FEW009 SCT250 16/09 A3008 RMK AO2"
}
```

---

## Running Tests

Install the development dependencies, then run pytest:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

The test suite uses mocked API responses so it runs offline with no external calls.

---

## Project Structure

```
.
├── app.py                  # Flask application and METAR decoding logic
├── templates/
│   └── index.html          # Frontend UI
├── tests/
│   └── test_app.py         # Unit tests
├── conftest.py             # pytest path configuration
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Development/test dependencies
└── .github/
    └── workflows/
        └── ci.yml          # GitHub Actions CI pipeline
```

---

## Data Source

Weather data is fetched from the [Aviation Weather Center API](https://aviationweather.gov/api/data/metar) operated by NOAA. No API key is required.

---

## License

MIT
