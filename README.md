# Instagram Analyzer

Instagram Analyzer is a production-style Streamlit dashboard for exploring
Instagram export ZIP files without sharing credentials or manually unpacking
archives.

# Live Demo

https://instagram-analyzer-followers.streamlit.app/

Upload one or more Instagram export ZIP files and analyze followers, following, mutuals, fans, recently unfollowed accounts, and historical follower changes directly in your browser.

## Highlights

- Upload one or more Instagram export ZIP files directly in the app
- Analyze followers, following, mutuals, fans, and not-following-back accounts
- Read `recently_unfollowed_profiles.json` when it exists
- Compare multiple exports to track new followers, lost followers, and net change
- Explore account lists with search, sorting, and interactive tables
- Download `mutuals.csv`, `fans.csv`, `not_following_back.csv`,
  `recently_unfollowed.csv`, and `unfollowers.csv` from the browser
- Auto-detect local exports under `data/` for development and testing

## Privacy

- The app never asks for Instagram credentials
- ZIP uploads are processed in memory whenever possible
- Uploaded files are not permanently stored by the application
- Analysis remains within the active app session and is discarded afterward

## Project structure

```text
instagram-analyzer/
├── app.py
├── data/
├── outputs/
├── src/
│   ├── analyzer.py
│   ├── dashboard.py
│   ├── parser.py
│   ├── utils.py
│   └── main.py
├── tests/
├── .github/workflows/ci.yml
├── README.md
└── requirements.txt
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the Streamlit app

```bash
streamlit run app.py
```

The app opens in wide mode and includes these sections:

- `Home`: upload ZIP files, review privacy guidance, confirm detected exports
- `Dashboard`: KPI metrics and growth cards
- `Analytics`: Plotly charts for relationship and historical insights
- `Explore Data`: searchable tabs for relationship lists
- `Exports`: download CSV outputs
- `Advanced Insights`: ratios, percentages, and a plain-English summary

## ZIP requirements

The uploader accepts Instagram export ZIP files containing:

- `followers_1.json`
- `following.json`
- `recently_unfollowed_profiles.json` when available

Multiple ZIP uploads are supported. When several exports are available for the
same account, the newest export is treated as current and the previous one is
used for comparison.

## Local development data

For convenience, the app also auto-detects extracted exports and ZIP files
inside `data/`. This is helpful for local testing, but the primary workflow is
ZIP upload through the UI.

## Optional CLI

The legacy CLI remains available for quick CSV generation from exports already
present in `data/`:

```bash
python -m src.main --data-dir data --output-dir outputs
```

## Testing

```bash
pytest
```

GitHub Actions runs the test suite on Python 3.11 and 3.12 for every push and
pull request.
