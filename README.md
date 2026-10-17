# CodeAlpha_URLShortener

**CodeAlpha Backend Development Internship, Task 1: Simple URL Shortener**

A small URL shortener built with **Flask** and **SQLite**. Send it a long URL and it returns a short link; opening the short link redirects to the original URL. Includes a simple web page, click counting and automated tests.

## Features

- `POST /api/shorten` creates a unique 6-character short code (random, collision-checked)
- Short link redirect (`GET /<code>`, HTTP 302) to the original URL
- SQLite storage of the code → URL mapping, created automatically on first run
- Same long URL always returns the same short code (no duplicates)
- Optional custom code (3-32 chars: letters, digits, `-`, `_`)
- Click counter and stats endpoint
- Input validation: only absolute `http://` / `https://` URLs (blocks `javascript:` etc.), max 2048 chars
- Simple frontend at `/` with recent links and a copy button

## Setup

Requires Python 3.9+.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

Optional environment variables: `PORT` (default 5000), `DATABASE_PATH` (default `urls.db` next to `app.py`), `FLASK_DEBUG=1`.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/shorten` | Create a short link. Body: `{"url": "...", "custom_code": "optional"}` |
| GET | `/<code>` | Redirect to the original URL (increments click count) |
| GET | `/api/urls/<code>` | Stats for one short code |
| GET | `/api/urls` | 20 most recent links |
| GET | `/health` | Health check |

### Example

```bash
curl -X POST http://127.0.0.1:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.python.org/about/"}'
```

```json
{
  "short_code": "9LYgRH",
  "short_url": "http://127.0.0.1:5000/9LYgRH",
  "original_url": "https://www.python.org/about/",
  "created_at": "2026-10-16T15:42:57+00:00",
  "clicks": 0
}
```

Status codes: `201` created, `200` existing URL reused, `400` invalid input, `404` unknown code, `409` custom code already taken.

## Tests

```bash
python -m unittest discover -s tests -v
```

13 tests cover shortening, redirects, validation, custom codes, conflicts, click counting, persistence and the frontend.

## Project structure

```
app.py              Flask app (routes, validation, SQLite access)
templates/          index.html (frontend), 404.html
static/             style.css, app.js
tests/test_app.py   Automated tests
requirements.txt
```

## Author

Anish Gupta, CodeAlpha Backend Development Intern (October-November 2026)
