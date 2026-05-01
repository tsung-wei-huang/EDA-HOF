# Electronic Design Automation (EDA) Hall of Fame

A static GitHub Pages site recognising researchers with the most prolific
all-time publication records across the four premier EDA venues:

| Venue | Full Name | Type | DBLP |
|---|---|---|---|
| [DAC](https://dblp.org/db/conf/dac/) | Design Automation Conference | Conference | `conf/dac` |
| [ICCAD](https://dblp.org/db/conf/iccad/) | International Conference on Computer-Aided Design | Conference | `conf/iccad` |
| [TCAD](https://dblp.org/db/journals/tcad/) | IEEE Transactions on Computer-Aided Design | Journal | `journals/tcad` |
| [TODAES](https://dblp.org/db/journals/todaes/) | ACM Transactions on Design Automation of Electronic Systems | Journal | `journals/todaes` |

**Live site:** https://tsung-wei-huang.github.io/EDA-HOF/index.html

**GitHub:** https://github.com/tsung-wei-huang/EDA-HOF

---

## Hall of Fame Criteria

A single combined threshold across all four venues:

> **DAC + ICCAD + TCAD + TODAES ≥ 50 papers (all-time)**

Click any column header on the site to re-sort by that venue. Use the venue
toggle buttons to filter the ranking to a subset of venues.

---

## Repository Layout

```
EDA-HallOfFame/
├── index.html   # Static site — no build step needed
├── data.js      # Generated — commit this after each refresh
├── favicon.svg  # Site favicon
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

- **Sorting:** Click any column header (Total, DAC, ICCAD, TCAD, TODAES) to
  sort. Click again to reverse. The active sort column highlights in gold.
- **Venue filter:** Toggle the DAC / ICCAD / TCAD / TODAES buttons to include
  or exclude venues from the Total and ranking.
- **Search:** Filters by researcher name in real time.
- **Name links:** Each researcher name links to their DBLP profile page.
- DBLP disambiguation suffixes (e.g. "Wei Li 0001") are stripped from display names.

---

## Affiliations

Affiliations are **not fetched automatically** — automated API lookups
(Semantic Scholar, DBLP) proved too unreliable for this data. Instead, they
are maintained manually in the `AFFILIATION_OVERRIDES` table near the top of
`run.py`, and applied at `data.js` generation time.

The table ships with affiliations pre-filled for the initial set of 118
researchers. When new researchers appear after a data refresh, `run.py` will
print a reminder like:

```
Affiliation tip:
N researchers are missing affiliations in data.js.
Tip: paste the RESEARCHERS array into an AI assistant and ask:
'Fill in the affiliation field with the university name for each
 researcher based on your knowledge. Leave blank if unsure.'
Then add the results to AFFILIATION_OVERRIDES in run.py.
```

To add or correct an affiliation, edit `AFFILIATION_OVERRIDES` in `run.py`:

```python
AFFILIATION_OVERRIDES: dict[str, str] = {
    "Tsung-Wei Huang": "University of Wisconsin-Madison",
    "Jason Cong":       "University of California, Los Angeles",
    # Add entries here — key is the name WITHOUT DBLP number suffix
}
```

Then regenerate instantly:

```bash
python run.py --skip-fetch --skip-enrich
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `503 Service Unavailable` during download | DBLP server blip | Wait a minute and re-run |
| Paper counts look too high | Cached `dblp_data.json` from old version | `rm tmp/dblp_data.json && python run.py --skip-download` |
| All `hindex`/`citations` are 0 | Skipped enrichment | Re-run without `--skip-enrich` |
| Same person appears twice | Name variant with no DBLP PID | See author disambiguation below |
| Affiliation shows blank | Not yet in `AFFILIATION_OVERRIDES` | Add it manually (see Affiliations section) |
| Site shows placeholder data | `data.js` is the stub file | Run `python run.py` |

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
- **Affiliations:** Manually curated in `AFFILIATION_OVERRIDES` in `run.py`.

---

## License

MIT License

Copyright (c) 2026 [Tsung-Wei Huang](https://tsung-wei-huang.github.io)

Built with the assistance of [Anthropic Claude](https://claude.ai).

Data derived from [DBLP](https://dblp.org) (CC0) and
[Semantic Scholar](https://www.semanticscholar.org).
