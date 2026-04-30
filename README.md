# Electronic Design Automation (EDA) Hall of Fame

A static GitHub Pages site recognising researchers with sustained, prolific
contributions to the four premier EDA venues:

| Venue | Type | DBLP key |
|---|---|---|
| [DAC](https://dblp.org/db/conf/dac/) | Conference | `dac` |
| [ICCAD](https://dblp.org/db/conf/iccad/) | Conference | `iccad` |
| [TCAD](https://dblp.org/db/journals/tcad/) | Journal | `tcad` |
| [TODAES](https://dblp.org/db/journals/todaes/) | Journal | `todaes` |

**Live site:** `https://<your-github-username>.github.io/EDA-HallOfFame/`

---

## Hall of Fame Criteria

| Tier | Venues | Threshold |
|---|---|---|
| **Conference HoF** | DAC + ICCAD (combined) | ≥ 20 papers (all-time) |
| **Journal HoF** | TCAD + TODAES (combined) | ≥ 10 papers (all-time) |

A researcher qualifies for the Combined view if they meet **either** threshold.

---

## Repository Layout

```
EDA-HallOfFame/
├── index.html   # Static site — no build step needed
├── data.js      # Generated — commit this after each refresh
├── run.py       # ← Single script that does everything
└── README.md
```

---

## First-Time Setup

### Prerequisites

- Python 3.10+
- Internet access (DBLP and Semantic Scholar public APIs — **no API keys needed**)
- No third-party packages — only Python stdlib

```bash
python --version   # confirm 3.10+
```

### Clone & deploy

```bash
git clone https://github.com/<you>/EDA-HallOfFame.git
cd EDA-HallOfFame
```

Enable GitHub Pages in your repo settings:
`Settings → Pages → Source: Deploy from branch → Branch: main / root`

---

## Data Pipeline (Manual Refresh)

Everything is one command:

```bash
python run.py
```

That's it. It runs all three stages internally with a live progress bar,
then tells you what to commit.

**What it does internally:**
1. Fetches all papers from DBLP for DAC, ICCAD, TCAD, TODAES → `dblp_data.json`
2. Enriches every author with h-index & citations from Semantic Scholar → `enriched_data.json`
3. Applies HoF thresholds and writes → `data.js`

**Expected time:**
| Stage | Time |
|---|---|
| DBLP fetch | ~10–20 min (DAC alone has 20k+ papers) |
| Semantic Scholar enrichment | ~1–3 h (rate-limited to ~92 req/min) |
| Generate data.js | < 5 s |

A progress bar shows exactly where you are at all times.

### Useful flags

```bash
# Skip enrichment for a fast refresh (no h-index/citations, but much quicker)
python run.py --skip-enrich

# Re-generate data.js from already-fetched data (instant)
python run.py --skip-fetch --skip-enrich

# Preview the site locally after generation (opens browser automatically)
python run.py --skip-fetch --skip-enrich --serve

# Full pipeline + open browser when done
python run.py --serve
```

### Commit and push

After `run.py` finishes:

```bash
git add data.js
git commit -m "Data refresh $(date +%Y-%m-%d)"
git push
```

GitHub Pages auto-deploys within ~60 s.

---

## How the Site Works

`index.html` is a fully self-contained static page — no frameworks, no build
step. It loads `data.js` (a plain JS file that sets global variables) and
renders everything client-side with vanilla JS.

**Tabs:** Combined · DAC · ICCAD · TCAD · TODAES  
**Sorting:** Click any column header to sort ascending/descending.  
**Search:** Filters by researcher name in real time.  
**Row highlighting:**
- 🟣 Purple — qualifies in **both** Conference and Journal HoF
- 🟡 Gold   — Conference HoF only (DAC+ICCAD ≥ 20)
- 🔵 Blue   — Journal HoF only (TCAD+TODAES ≥ 10)

Researcher names link to their DBLP profile page.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `dblp_data.json` is small / missing venue | DBLP API timeout | Re-run `python run.py` |
| All `hindex`/`citations` are 0 | Skipped enrichment step | Re-run `python run.py` (without `--skip-enrich`) |
| Wrong author merged (name collision) | DBLP disambiguation issue | Edit `dblp_data.json` manually, then `python run.py --skip-fetch --skip-enrich` |
| Site shows "Run pipeline" placeholder | `data.js` is stub | Run `python run.py` |

### Author disambiguation

DBLP uses persistent PIDs to disambiguate authors with identical names
(e.g. `48/389`). The fetch script stores these PIDs. When two different
researchers share a name and DBLP has *not* yet disambiguated them, their
paper counts will be merged.

To manually correct a PID collision:
1. Open `dblp_data.json`
2. Find the merged entry under `dblp_data.<venue>.authors`
3. Split it into two entries with distinct keys and corrected paper counts
4. Re-run `generate_data_js.py`

---

## Data Sources

- **Publication data:** [DBLP](https://dblp.org) public search API — free,
  no authentication required. Please respect their [terms of use](https://dblp.org/faq/How+can+I+download+the+whole+dblp+dataset.html) and the
  built-in rate limiting in `fetch_dblp.py`.
- **Citation metrics:** [Semantic Scholar](https://api.semanticscholar.org)
  public API — free, no key required for the author-search endpoint used here.

---

## Updating Thresholds

Edit the constants near the top of `run.py`:

```python
CONF_THRESHOLD    = 20   # DAC + ICCAD combined
JOURNAL_THRESHOLD = 10   # TCAD + TODAES combined
```

Then re-generate instantly without re-fetching:

```bash
python run.py --skip-fetch --skip-enrich
```

---

## Contributing

- **Data corrections:** Open a PR editing `dblp_data.json` or `enriched_data.json`
- **UI improvements:** Edit `index.html` (self-contained, no build step)
- **New venues:** Add to the `VENUES` dict in `fetch_dblp.py` and update `generate_data_js.py`

---

## License

Data: derived from [DBLP](https://dblp.org) (CC0) and
[Semantic Scholar](https://www.semanticscholar.org).  
Code: MIT.
