# Near-Earth Asteroids Explorer (NeoWs)

[Leer en español](README.md)

Look up asteroids that pass close to Earth using NASA's **NeoWs** API. The project ships in three forms, all sharing the same core logic: a **web app** (works on desktop and phone browsers), a **desktop GUI**, and a **console menu**. Responses are cached locally and results can be exported to CSV.

> Independent personal project. Not affiliated with or endorsed by NASA.

**Live demo:** [https://YOUR-APP.onrender.com](https://YOUR-APP.onrender.com)
*(Hosted on a free tier: if nobody has used it recently, the first load can take about a minute while the server wakes up. See [Using the web app](#using-the-web-app).)*

<!-- Screenshots: add them under docs/img/ and uncomment.
![Web app](docs/img/web.png)
![Desktop GUI](docs/img/gui.png)
-->

## Features

- Query by date range (7 days maximum, the limit of NeoWs' *Feed* endpoint). Longer ranges are trimmed automatically to 7 days from the start date.
- Results as a table (cards on narrow screens) with name, estimated diameter, hazard flag, approach distance and velocity.
- Three charts: objects per day, approach distance vs. size, and potentially hazardous vs. non-hazardous objects.
- Disk cache: a range you already queried is not requested again (see [How the cache works](#how-the-cache-works)).
- CSV export of the results.
- Date validation, network error handling and a specific message when NASA rate-limits you (HTTP 429).
- API key handling that never displays the key and never stores it in the cache.
- Unit tests for the API layer, cache, dates, charts, data processing, export and the app controllers.

## Ways to use it

| Option | Best for | How |
|---|---|---|
| **Web app** | Trying it in one click, including from a phone | Open the [live demo](https://YOUR-APP.onrender.com) |
| **Portable desktop app** | Using it without installing Python | Download from [Releases](https://github.com/San-0731/NeoWs-asteroides/releases/latest) |
| **From source** | Development, console menu | See [Installation](#installation-from-source) |

### Using the web app

- Every visitor should enter **their own NASA API key** with **Configure API Key**. Without one, the app falls back to `DEMO_KEY`.
- `DEMO_KEY` is limited to **30 requests per hour and 50 per day per IP address**, and on the web all visitors share the server's IP, so the limit is reached quickly. When that happens the app tells you and suggests using your own key. Get one for free at [api.nasa.gov](https://api.nasa.gov/); a registered key allows 1,000 requests per hour.
- Your key is sent to the app's server only to make your request. It is kept **in memory for that session** and is not written to disk or to the cache. The server's own settings are never used for web visitors.
- Queries answered from the cache don't use any API quota.
- On the free hosting tier the server sleeps after 15 minutes without traffic and the first request afterwards takes around a minute. The server's disk is also temporary, so the cache is emptied whenever the server restarts.
- Exporting CSV from the browser downloads a file with the results of your current query.

### Portable desktop app

Each release contains one package per operating system, built automatically with PyInstaller and GitHub Actions:

| File | System | Status |
|---|---|---|
| `NeoWs-Asteroides-Windows.zip` | Windows | Tested on a clean machine without Python |
| `NeoWs-Asteroides-Linux.tar.gz` | Linux | Tested on Debian 13.6 and Ubuntu, both without Python |
| `NeoWs-Asteroides-macOS.tar.gz` | macOS (Apple Silicon build) | **Experimental, not verified on a real Mac** |

The tests above don't guarantee compatibility with every Linux distribution or version. The packages are unsigned, so Windows SmartScreen or macOS Gatekeeper may warn you the first time you open them. Keep the whole extracted folder together, not just the executable. No API key is bundled: set your own from inside the app.

## Requirements (from source)

- Tested with **Python 3.14** on **Ubuntu 26.04 LTS**.
- Internet connection for new queries.
- On Ubuntu, two system packages for the desktop GUI and the chart windows of the console version:

```bash
sudo apt update
sudo apt install python3-venv python3-tk
```

## Installation (from source)

```bash
git clone https://github.com/San-0731/NeoWs-asteroides.git
cd NeoWs-asteroides

python3 -m venv venv
source venv/bin/activate
```

Then install the dependencies for the version you want to run:

```bash
# Desktop GUI and console
pip install -r requirements.txt

# Web app
pip install -r requirements_web.txt
```

Remember to activate the virtual environment (`source venv/bin/activate`) in every new terminal.

## Usage

### Web app (local)

```bash
flet run --web --port 8000 app_flet.py
```

Open the address it prints in your browser. To run it as a server without opening a browser (for example in a container or on a hosting service):

```bash
FLET_FORCE_WEB_SERVER=true FLET_SERVER_PORT=8000 python app_flet.py
```

It listens on all network interfaces, so it can be reached from another device on your network (for example, a phone). When you deploy it to a hosting provider, make sure the platform:

- provides HTTPS (the API key travels from the browser to the server),
- allows WebSocket connections (Flet uses `/ws`),
- tells the app which port to use through `FLET_SERVER_PORT`.

The live demo runs on Render with `pip install -r requirements_web.txt` as the build command and `FLET_SERVER_PORT=$PORT python app_flet.py` as the start command.

### Desktop GUI

```bash
python app.py
```

Enter a start date and, optionally, an end date, then press **Consultar** (Query). While it runs, the status area animates `Consultando.` → `Consultando..` → `Consultando...`. Results appear in the table; each chart has its own tab. **Exportar CSV** saves the results of the last successful query. Queries already in the cache can be served offline. If something unexpected fails, the app reports it, logs the error type and re-enables the button.

### Console

```bash
python Neows.py
```

| Option | What it does |
|---|---|
| 1. Make the NASA API request | Asks for the dates and queries NeoWs, or uses the cache if that query exists. |
| 2. Build data and show results | Processes the response and prints one record per asteroid. |
| 3. Build charts | Opens a submenu to pick and display one of the three charts. |
| 4. Save results to CSV | Appends the results to the CSV file in the user data folder. |
| 5. Exit | Closes the program. |

**Order matters:** options 3 and 4 need options 1 and 2 to have run first.

### Dates

- Format `YYYY-MM-DD`, for example `2026-08-01`.
- If the end date is left empty, only the start date is queried.
- The end date cannot be earlier than the start date.
- Ranges longer than 7 days are trimmed to 7 days from the start date.

## Configuring the API key (desktop and console)

The desktop and console versions read the key from `settings.json` in the user data folder. If there is no personal key there, they use `DEMO_KEY`. The app does **not** read keys from `.env` files or from a `NASA_API_KEY` environment variable.

On first start the app creates `settings.json` with an empty key. In the GUI, press **Configurar API Key**, type your key and save it. The field is masked by default, and a reveal button lets you check what you typed. The status bar shows whether the active key is personal or `DEMO_KEY`, and never shows the key itself.

Changes are written to a temporary file first and then replace `settings.json`, so an interrupted save keeps your previous settings. If the file contains invalid JSON, the app reports a clear error and does not overwrite it; fix it by hand using this format:

```json
{
  "NASA_API_KEY": "your_key_here"
}
```

### Where the data lives

Cache, CSV and settings are stored in the per-user data folder determined by `platformdirs`, under the application name `NeoWs-Asteroides`. On Linux that is usually `~/.local/share/NeoWs-Asteroides`; on Windows and macOS the platform's standard user data location is used. The folder holds `settings.json`, `cache_neows.json` and `Historial_Consultas.csv`.

## Example record

```json
{
    "Fecha": "2026-08-06",
    "Name": "136770 (1996 PC1)",
    "Estimated_Diameter_(Km)": 0.459240286,
    "Threat_Level": false,
    "Close_Approach_Distance_(km)": 61668127.54939708,
    "Close_Approach_Velocity_(km/h)": 83073.9012659539
}
```

| Field | Meaning |
|---|---|
| `Fecha` | Date of the closest approach to Earth. |
| `Name` | Object designation according to NASA/JPL. |
| `Estimated_Diameter_(Km)` | Estimated maximum diameter, in kilometers. It is an estimate. |
| `Threat_Level` | Whether NASA classifies it as "potentially hazardous" (`is_potentially_hazardous_asteroid`). This is a classification based on size and orbit; it does not mean the object will hit Earth. |
| `Close_Approach_Distance_(km)` | Distance from Earth at closest approach, in kilometers. |
| `Close_Approach_Velocity_(km/h)` | Relative velocity at closest approach, in km/h. |

If a value is missing from the API response, the field is `null` and that record is skipped only in the chart that needs it. (Field names are kept in Spanish, as in the original version of the project.)

## How the cache works

Responses are stored in `cache_neows.json`, keyed by the exact date range. If you repeat a range that is still valid, the app loads it from the cache with no API request and no internet connection needed.

Before returning or saving a response, the app strips the `api_key` parameter from the links NASA includes in it. When it loads a cache created by an older version, it cleans those links too and rewrites the file.

If the cache file contains invalid JSON or malformed records, it is moved to `cache_neows.json.bak` (or a numbered name if a backup already exists) before continuing with an empty cache, so a new query never destroys the original file.

Expiry is computed in UTC and depends on the end date of the range:

- **Permanent:** the query was saved after the range's end date (a range that has already finished).
- **12 hours:** the query was saved before the range ended, i.e. ranges that reach today or the future. NASA can add new objects or correct orbits, so these are refreshed.
- **Each range is independent:** `2026-08-01 – 2026-08-07` and `2026-08-01 – 2026-08-05` are different queries and each makes its own request.

## Project structure

```
.
├── Neows.py                     # Entry point: console menu
├── app.py                       # Entry point: CustomTkinter desktop GUI
├── app_flet.py                  # Entry point: Flet web app
├── neo_app/
│   ├── api.py                   # NeoWs request and API key handling
│   ├── cache.py                 # JSON cache with expiry and safe writes
│   ├── config.py                # User data paths and settings
│   ├── consulta.py              # Data retrieval from cache or API
│   ├── consulta_flet.py         # Background query helper for the web app
│   ├── fechas.py                # Date input and validation
│   ├── procesamiento.py         # Turns the API response into records
│   ├── graficas.py              # The three charts (matplotlib)
│   ├── presentacion_flet.py     # Tables, cards and chart images for the web app
│   ├── sanitizacion.py          # Removes API keys from stored responses
│   └── exportacion.py           # CSV export
├── tests/                       # Unit tests
├── .github/workflows/build.yml  # Portable builds and releases
├── NeoWs-Asteroides.spec        # PyInstaller configuration
├── requirements.txt             # Desktop GUI, console and build dependencies
└── requirements_web.txt         # Web app dependencies
```

## Tests

From the project root, with the virtual environment active:

```bash
python -m unittest discover -s tests
```

The tests don't use the internet and don't touch your cache or CSV.

## Known limitations

- Only the NeoWs *Feed* endpoint (query by date) is used; *Lookup* and *Browse* are not.
- The CSV avoids duplicate rows based on the asteroid date + name pair. If either is missing, the row is kept because it can't be identified as a duplicate with certainty.
- Running the desktop GUI from source requires Tkinter to be available on the system.
- The web app is a responsive website, not a native mobile app.
- On the free hosting tier the server sleeps when idle and its cache is not preserved between restarts.
- Windows and Linux packages were verified on clean machines; the macOS package was not.

## Credits

Data from NASA's **NeoWs** (Near Earth Object Web Service) API, available at [api.nasa.gov](https://api.nasa.gov/). Built with Python, matplotlib, CustomTkinter and [Flet](https://flet.dev/).
