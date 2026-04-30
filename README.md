# Electronic Design Automation (EDA) Hall of Fame

A static GitHub Pages site recognising researchers with the most prolific
all-time publication records across the four premier EDA venues:

| Venue | Full Name | Type | DBLP |
|---|---|---|---|
| [DAC](https://dblp.org/db/conf/dac/) | Design Automation Conference | Conference | `conf/dac` |
| [ICCAD](https://dblp.org/db/conf/iccad/) | International Conference on Computer-Aided Design | Conference | `conf/iccad` |
| [TCAD](https://dblp.org/db/journals/tcad/) | IEEE Transactions on Computer-Aided Design | Journal | `journals/tcad` |
| [TODAES](https://dblp.org/db/journals/todaes/) | ACM Transactions on Design Automation of Electronic Systems | Journal | `journals/todaes` |

**Live site:** `https://<your-github-username>.github.io/EDA-HallOfFame/`

---

## Hall of Fame Criteria

A single combined threshold across all four venues:

> **DAC + ICCAD + TCAD + TODAES ≥ 50 papers (all-time)**

Click any column header on the site to re-sort by that venue.

---

## Repository Layout

```
EDA-HallOfFame/
├── index.html   # Static site — no build step needed
├── data.js      # Generated — commit this after each refresh
├── run.py       # Single script that runs the full pipeline
├── .gitignore
└── README.md

tmp/             # Intermediate files — created by run.py, not committed
├── dblp.xml.gz        # DBLP bulk XML dump (~1 GB)
├── dblp_data.json     # Parsed paper/author data per venue
└── enriched_data.json # Same + h-index & citations from Semantic Scholar
```

---

## First-Time Setup

### Prerequisites

- Python 3.10+
- Internet access (DBLP and Semantic Scholar public APIs — **no API keys needed**)
- No third-party packages required — pure Python stdlib
- Optional: `pip install lxml` for ~4x faster XML parsing

```bash
python --version   # confirm 3.10+
pip install lxml   # optional but recommended
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

It runs all three stages internally with live progress bars, then tells you
what to commit. All intermediate files go into `./tmp/` and are never committed.

### What it does

| Stage | Output | Time |
|---|---|---|
| Download DBLP XML dump (~1 GB) | `tmp/dblp.xml.gz` | ~10–20 min |
| Parse XML, extract venue papers | `tmp/dblp_data.json` | ~2–5 min |
| Enrich HoF qualifiers via Semantic Scholar | `tmp/enriched_data.json` | ~5 min |
| Apply threshold, generate site data | `data.js` | < 5 s |

The DBLP dump is a one-time download. On subsequent refreshes use
`--skip-download` to reuse it (see flags below).

### Flags

```bash
# Re-parse XML without re-downloading (most common refresh)
python run.py --skip-download

# Skip download AND parse — reuse existing tmp/dblp_data.json
python run.py --skip-fetch

# Regenerate data.js only — no network requests at all
python run.py --skip-fetch --skip-enrich

# Any of the above + open browser preview when done
python run.py --skip-fetch --skip-enrich --serve
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
step, no server. It loads `data.js` and renders everything client-side.

- **Sorting:** Click any column header (Total, DAC, ICCAD, TCAD, TODAES, h, Cites)
  to sort. Click again to reverse. The active sort column highlights in gold.
- **Search:** Filters by researcher name in real time.
- **Name links:** Each researcher name links to their DBLP profile page.
- DBLP disambiguation suffixes (e.g. "Wei Li 0001") are stripped from display names.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `503 Service Unavailable` during download | DBLP server blip | Wait a minute and re-run |
| Paper counts look too high | Cached `dblp_data.json` from old version | `rm tmp/dblp_data.json && python run.py --skip-download` |
| All `hindex`/`citations` are 0 | Skipped enrichment | Re-run without `--skip-enrich` |
| Same person appears twice | Name variant with no DBLP PID | See author disambiguation below |
| Site shows placeholder data | `data.js` is the stub file | Run `python run.py` |

### Author disambiguation

DBLP assigns a persistent PID (e.g. `w/MartinDFWong`) to each researcher.
The pipeline uses PIDs as the primary identity key, so name variants like
"Martin D. F. Wong" and "D. F. Wong" merge automatically when DBLP gives
them the same PID.

For the rare case where a researcher has no PID in the XML (very old papers),
the pipeline falls back to a normalised name key (last name + first initial).

If you still see a duplicate after re-running, it means both records genuinely
lack a PID. Fix it by editing `tmp/dblp_data.json`: find the two entries,
merge their paper counts into one, then re-run:

```bash
python run.py --skip-fetch --skip-enrich
```

---

## Updating the Threshold

Edit the constant near the top of `run.py`:

```python
COMBINED_THRESHOLD = 50  # DAC + ICCAD + TCAD + TODAES combined
```

Then regenerate instantly — no re-fetching needed:

```bash
python run.py --skip-fetch --skip-enrich
```

---

## Data Sources

- **Publication data:** [DBLP](https://dblp.org) bulk XML dump
  (`dblp.org/xml/dblp.xml.gz`) — free, no authentication required.
  Please respect their [terms of use](https://dblp.org/faq/How+can+I+download+the+whole+dblp+dataset.html).
- **Citation metrics:** [Semantic Scholar](https://api.semanticscholar.org)
  public API — free, no key required. Only HoF-qualifying researchers are
  looked up (not all 30k+ authors in the dump).

---

## Contributing

- **Data corrections:** Open a PR editing `tmp/dblp_data.json`, then re-run
  `python run.py --skip-fetch --skip-enrich` and commit `data.js`
- **UI improvements:** Edit `index.html` — fully self-contained, no build step
- **New venues:** Add an entry to the `VENUES` and `VENUE_PREFIXES` dicts
  in `run.py`, then re-run the full pipeline

---

## License

Data derived from [DBLP](https://dblp.org) (CC0) and
[Semantic Scholar](https://www.semanticscholar.org).  
Code: MIT.
