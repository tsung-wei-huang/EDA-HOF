#!/usr/bin/env python3
"""
EDA Hall of Fame — Data Pipeline
=================================
Run this once to fetch, enrich, and generate the site data:

    python run.py

Options:
    --skip-enrich   Skip Semantic Scholar enrichment (faster, no citations/h-index)
    --skip-download Skip the 700MB download, re-parse existing ./tmp/dblp.xml.gz
    --skip-fetch    Skip DBLP fetch entirely (reuse existing dblp_data.json)
    --serve         Start a local HTTP server after generation to preview the site
    --port 8000     Port for the local server (default 8000)

Examples:
    python run.py                                    # Full pipeline
    python run.py --skip-enrich                      # Quick run, no citation data
    python run.py --skip-fetch --skip-enrich         # Regenerate data.js only
    python run.py --skip-fetch --skip-enrich --serve # Regenerate + preview

Intermediate files (dblp_data.json, enriched_data.json) are written to a
temporary directory under /tmp and deleted automatically when the pipeline
finishes. Only data.js is written to the repo directory.
"""

import sys
import os
import re
import json
import time
import argparse
import random
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

# ── Run from the script's own directory ─────────────────────────────────────
REPO_DIR = Path(__file__).parent.resolve()
os.chdir(REPO_DIR)

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG  —  edit these to change thresholds or venues
# ─────────────────────────────────────────────────────────────────────────────
COMBINED_THRESHOLD = 50  # DAC + ICCAD + TCAD + TODAES combined

# ── Affiliation overrides ────────────────────────────────────────────────────
# Manually curated affiliations. Key = author name WITHOUT DBLP number suffix.
# These take priority over anything returned by Semantic Scholar or DBLP API.
# Add or correct entries here as needed.
AFFILIATION_OVERRIDES: dict[str, str] = {
    "A. Richard Newton":                  "University of California, Berkeley",
    "Alan Mishchenko":                    "University of California, Berkeley",
    "Alberto L. Sangiovanni-Vincentelli": "University of California, Berkeley",
    "Anand Raghunathan":                  "Purdue University",
    "Andrew B. Kahng":                    "University of California, San Diego",
    "Ankur Srivastava":                   "University of Maryland",
    "Bei Yu":                             "Chinese University of Hong Kong",
    "Bing Li":                            "Technical University of Munich",
    "Charles J. Alpert":                  "Cadence Design Systems",
    "Cheng Zhuo":                         "Zhejiang University",
    "Cheng-Kok Koh":                      "Purdue University",
    "Chun Jason Xue":                     "City University of Hong Kong",
    "Chung-Kuan Cheng":                   "University of California, San Diego",
    "D. F. Wong":                         "Hong Kong Baptist University",
    "David T. Blaauw":                    "University of Michigan",
    "David Z. Pan":                       "University of Texas at Austin",
    "Deming Chen":                        "University of Illinois Urbana-Champaign",
    "Dennis Sylvester":                   "University of Michigan",
    "Dian Zhou":                          "University of Texas at Dallas",
    "Diana Marculescu":                   "University of Texas at Austin",
    "Enrico Macii":                       "Politecnico di Torino",
    "Evangeline F. Y. Young":             "Chinese University of Hong Kong",
    "Fabio Somenzi":                      "University of Colorado Boulder",
    "Fan Yang":                           "Fudan University",
    "Farid N. Najm":                      "University of Toronto",
    "Farinaz Koushanfar":                 "University of California, San Diego",
    "Francky Catthoor":                   "KU Leuven",
    "Gang Qu":                            "University of Maryland",
    "Georges G. E. Gielen":               "KU Leuven",
    "Giovanni De Micheli":                "EPFL",
    "Hai Zhou":                           "Northwestern University",
    "Haoxing Ren":                        "NVIDIA",
    "Huawei Li":                          "Chinese Academy of Sciences",
    "Huazhong Yang":                      "Tsinghua University",
    "Igor L. Markov":                     "University of Michigan",
    "Iris Hui-Ru Jiang":                  "National Taiwan University",
    "Irith Pomeranz":                     "Purdue University",
    "Jacob A. Abraham":                   "University of Texas at Austin",
    "Jaijeet S. Roychowdhury":            "University of California, Berkeley",
    "Janusz Rajski":                      "Siemens EDA",
    "Jason Cong":                         "University of California, Los Angeles",
    "Jiang Hu":                           "Texas A&M University",
    "Jianli Chen":                        "Fudan University",
    "Jie-Hong R. Jiang":                  "National Taiwan University",
    "Jingtong Hu":                        "University of Pittsburgh",
    "Jinjun Xiong":                       "University at Buffalo",
    "John P. Hayes":                      "University of Michigan",
    "Jordi Cortadella":                   "Universitat Politècnica de Catalunya",
    "Jörg Henkel":                   "Karlsruhe Institute of Technology",
    "Kaushik Roy":                        "Purdue University",
    "Krishnendu Chakrabarty":             "Arizona State University",
    "Kurt Keutzer":                       "University of California, Berkeley",
    "Kwang-Ting Cheng":                   "Hong Kong University of Science and Technology",
    "Lawrence T. Pileggi":                "Carnegie Mellon University",
    "Lei He":                             "University of California, Los Angeles",
    "Leibo Liu":                          "Tsinghua University",
    "Luca Benini":                        "ETH Zurich",
    "Luciano Lavagno":                    "Politecnico di Torino",
    "Mahmut T. Kandemir":                 "Pennsylvania State University",
    "Majid Sarrafzadeh":                  "University of California, Los Angeles",
    "Malgorzata Marek-Sadowska":          "University of California, Santa Barbara",
    "Martin D. F. Wong":                  "Hong Kong Baptist University",
    "Massoud Pedram":                     "University of Southern California",
    "Miodrag Potkonjak":                  "University of California, Los Angeles",
    "Mohsen Imani":                       "University of California, Irvine",
    "Muhammad Shafique":                  "New York University Abu Dhabi",
    "Nikil D. Dutt":                      "University of California, Irvine",
    "Niraj K. Jha":                       "Princeton University",
    "Ozgur Sinanoglu":                    "New York University Abu Dhabi",
    "Peng Li":                            "Texas A&M University",
    "Puneet Gupta":                       "University of California, Los Angeles",
    "Qiang Xu":                           "Chinese University of Hong Kong",
    "Radu Marculescu":                    "University of Texas at Austin",
    "Ramesh Karri":                       "New York University",
    "Rob A. Rutenbar":                    "University of Illinois Urbana-Champaign",
    "Robert K. Brayton":                  "University of California, Berkeley",
    "Robert Wille":                       "Technical University of Munich",
    "Rolf Drechsler":                     "University of Bremen",
    "Ru Huang":                           "Peking University",
    "Runsheng Wang":                      "Peking University",
    "Ryan Kastner":                       "University of California, San Diego",
    "Sachin S. Sapatnekar":               "University of Minnesota",
    "Sarma B. K. Vrudhula":               "Arizona State University",
    "Shaojun Wei":                        "Tsinghua University",
    "Sharad Malik":                       "Princeton University",
    "Sheldon X.-D. Tan":                  "University of California, Riverside",
    "Shih-Chieh Chang":                   "National Tsing Hua University",
    "Shouyi Yin":                         "Tsinghua University",
    "Srinivas Devadas":                   "Massachusetts Institute of Technology",
    "Subhasish Mitra":                    "Stanford University",
    "Sudhakar M. Reddy":                  "University of Iowa",
    "Sujit Dey":                          "University of California, San Diego",
    "Sung Kyu Lim":                       "Georgia Institute of Technology",
    "Sung-Mo Kang":                       "University of California, Santa Cruz",
    "Taewhan Kim":                        "Seoul National University",
    "Tei-Wei Kuo":                        "National Taiwan University",
    "Tsung-Wei Huang":                    "University of Wisconsin-Madison",
    "Tsung-Yi Ho":                        "Chinese University of Hong Kong",
    "Ulf Schlichtmann":                   "Technical University of Munich",
    "Valeria Bertacco":                   "University of Michigan",
    "Vladimir Zolotov":                   "IBM Research",
    "Xiaobo Sharon Hu":                   "University of Notre Dame",
    "Xiaowei Li":                         "Chinese Academy of Sciences",
    "Xin Li":                             "Duke University",
    "Xuan Zeng":                          "Fudan University",
    "Yanzhi Wang":                        "Northeastern University",
    "Yao-Wen Chang":                      "National Taiwan University",
    "Yibo Lin":                           "Peking University",
    "Ying Wang":                          "Chinese Academy of Sciences",
    "Yinhe Han":                          "Chinese Academy of Sciences",
    "Yiran Chen":                         "Duke University",
    "Yiyu Shi":                           "University of Notre Dame",
    "Yu Wang":                            "Tsinghua University",
    "Yuan Xie":                           "University of California, Santa Barbara",
    "Yuan-Hao Chang":                     "National Yang Ming Chiao Tung University",
    "Yun Liang":                          "Peking University",
    "Yuzhe Ma":                           "Hong Kong University of Science and Technology",
}

# ── Manual name overrides ─────────────────────────────────────────────────────
# Use this table to fix cases where the same researcher appears under two
# different name strings in the DBLP XML, both without a PID.
#
# Key:   exact name string as it appears in the XML (check tmp/dblp_data.json)
# Value: the DBLP PID  (e.g. "w/MartinDFWong") OR another name string that
#        already has a PID — either way it becomes the identity key.
#
# To find a researcher's PID: visit their DBLP page and copy the path after
# https://dblp.org/pid/  e.g. https://dblp.org/pid/w/MartinDFWong -> w/MartinDFWong
#
# Example:
#   "D. F. Wong":        "w/MartinDFWong",
#   "D.F. Wong":         "w/MartinDFWong",
#   "Andrew Kahng":      "k/AndrewBKahng",
NAME_OVERRIDES: dict[str, str] = {
    # "D. F. Wong" and "Martin D. F. Wong" are the same person —
    # both lack a DBLP PID so we pin them to the same canonical key
    "D. F. Wong":        "w/MartinDFWong",
    "D.F. Wong":         "w/MartinDFWong",
}

# dblp_path must match the path under https://dblp.org/db/
VENUES = {
    "dac":    {"label": "DAC",    "type": "conf",    "dblp_path": "conf/dac"},
    "iccad":  {"label": "ICCAD",  "type": "conf",    "dblp_path": "conf/iccad"},
    "tcad":   {"label": "TCAD",   "type": "journal", "dblp_path": "journals/tcad"},
    "todaes": {"label": "TODAES", "type": "journal", "dblp_path": "journals/todaes"},
}

DBLP_BASE = "https://dblp.org"
# Use a real browser UA — DBLP's CDN blocks custom/partial UA strings
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ─────────────────────────────────────────────────────────────────────────────
#  TEMP DIRECTORY  — created once, cleaned up on any exit
# ─────────────────────────────────────────────────────────────────────────────
TMP_DIR: Path = REPO_DIR / "tmp"  # fixed location, always overwritten

def setup_tmpdir() -> Path:
    """Create (or reuse) the ./tmp working directory."""
    TMP_DIR.mkdir(exist_ok=True)
    return TMP_DIR


def tmpfile(name: str) -> Path:
    """Return a fixed path inside ./tmp."""
    return TMP_DIR / name


# ─────────────────────────────────────────────────────────────────────────────
#  PRETTY PRINTING
# ─────────────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def banner(text):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")

def info(text):  print(f"  {CYAN}→{RESET}  {text}")
def ok(text):    print(f"  {GREEN}✓{RESET}  {text}")
def warn(text):  print(f"  {YELLOW}⚠{RESET}  {text}")
def err(text):   print(f"  {RED}✗{RESET}  {text}")

def progress(i, total, label=""):
    pct = int(i / max(total, 1) * 40)
    bar = "█" * pct + "░" * (40 - pct)
    print(f"\r  [{bar}] {i}/{total}  {label:<35}", end="", flush=True)

# =============================================================================
#  HTTP helper
# =============================================================================
def fetch_url(url: str, retries: int = 5) -> bytes | None:
    """Fetch with exponential backoff. Connection resets start at 15s."""
    import errno as errno_mod
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                import gzip as _gz
                raw = _gz.decompress(raw)
            return raw
        except Exception as e:
            if attempt == retries - 1:
                err(f"Failed ({url.split('/')[-1]}): {e}")
                return None
            is_reset = isinstance(e, ConnectionResetError) or (
                hasattr(e, "errno") and e.errno in (
                    getattr(errno_mod, "ECONNRESET", 104),
                    getattr(errno_mod, "EPIPE", 32),
                )
            )
            base = 15.0 if is_reset else 2.0
            wait = base * (2 ** attempt)
            warn(f"  Attempt {attempt+1} failed ({type(e).__name__}), retrying in {wait:.0f}s ...")
            time.sleep(wait)
    return None


# =============================================================================
#  STEP 1 — Fetch DBLP via official bulk XML dump
#
#  DBLP publishes a complete XML dump at https://dblp.org/xml/
#  This is their recommended bulk-data approach — no per-page scraping,
#  no CDN rate-limiting, no connection resets.
#
#  dblp.xml.gz is ~700 MB compressed. We stream-parse with iterparse
#  so the full tree is never held in memory.
# =============================================================================

DBLP_XML_GZ = "https://dblp.org/xml/dblp.xml.gz"

VENUE_PREFIXES = {
    "dac":    ["conf/dac/"],
    "iccad":  ["conf/iccad/"],
    "tcad":   ["journals/tcad/"],
    "todaes": ["journals/todaes/"],
}

PAPER_TAGS = {"inproceedings", "article"}


def download_dblp_dump(dest: Path) -> bool:
    """Stream-download dblp.xml.gz with a progress bar."""
    info(f"Downloading DBLP dump (~700 MB) ...")
    info(f"Saving to: {dest}")
    info("This is a one-time download; reuse with --skip-fetch next time.")
    print()
    try:
        req = urllib.request.Request(DBLP_XML_GZ, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=120) as r:
            total = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as out:
                while True:
                    buf = r.read(256 * 1024)
                    if not buf:
                        break
                    out.write(buf)
                    downloaded += len(buf)
                    if total:
                        progress(downloaded // (1024 * 1024),
                                 total     // (1024 * 1024),
                                 f"{downloaded/1024/1024:.0f}/{total/1024/1024:.0f} MB")
        print()
        return True
    except Exception as e:
        err(f"Download failed: {e}")
        return False


# HTML entities that DBLP uses in author names but aren't defined in plain XML.
# ElementTree refuses to load the external DTD, so we inject them inline.
# Source: https://www.w3.org/TR/html4/sgml/entities.html (Latin-1 + special chars)
_HTML_ENTITIES = """<!DOCTYPE dblp [
  <!ENTITY nbsp   "&#160;"> <!ENTITY iexcl  "&#161;"> <!ENTITY cent   "&#162;">
  <!ENTITY pound  "&#163;"> <!ENTITY curren "&#164;"> <!ENTITY yen    "&#165;">
  <!ENTITY brvbar "&#166;"> <!ENTITY sect   "&#167;"> <!ENTITY uml    "&#168;">
  <!ENTITY copy   "&#169;"> <!ENTITY ordf   "&#170;"> <!ENTITY laquo  "&#171;">
  <!ENTITY not    "&#172;"> <!ENTITY shy    "&#173;"> <!ENTITY reg    "&#174;">
  <!ENTITY macr   "&#175;"> <!ENTITY deg    "&#176;"> <!ENTITY plusmn "&#177;">
  <!ENTITY sup2   "&#178;"> <!ENTITY sup3   "&#179;"> <!ENTITY acute  "&#180;">
  <!ENTITY micro  "&#181;"> <!ENTITY para   "&#182;"> <!ENTITY middot "&#183;">
  <!ENTITY cedil  "&#184;"> <!ENTITY sup1   "&#185;"> <!ENTITY ordm   "&#186;">
  <!ENTITY raquo  "&#187;"> <!ENTITY frac14 "&#188;"> <!ENTITY frac12 "&#189;">
  <!ENTITY frac34 "&#190;"> <!ENTITY iquest "&#191;"> <!ENTITY Agrave "&#192;">
  <!ENTITY Aacute "&#193;"> <!ENTITY Acirc  "&#194;"> <!ENTITY Atilde "&#195;">
  <!ENTITY Auml   "&#196;"> <!ENTITY Aring  "&#197;"> <!ENTITY AElig  "&#198;">
  <!ENTITY Ccedil "&#199;"> <!ENTITY Egrave "&#200;"> <!ENTITY Eacute "&#201;">
  <!ENTITY Ecirc  "&#202;"> <!ENTITY Euml   "&#203;"> <!ENTITY Igrave "&#204;">
  <!ENTITY Iacute "&#205;"> <!ENTITY Icirc  "&#206;"> <!ENTITY Iuml   "&#207;">
  <!ENTITY ETH    "&#208;"> <!ENTITY Ntilde "&#209;"> <!ENTITY Ograve "&#210;">
  <!ENTITY Oacute "&#211;"> <!ENTITY Ocirc  "&#212;"> <!ENTITY Otilde "&#213;">
  <!ENTITY Ouml   "&#214;"> <!ENTITY times  "&#215;"> <!ENTITY Oslash "&#216;">
  <!ENTITY Ugrave "&#217;"> <!ENTITY Uacute "&#218;"> <!ENTITY Ucirc  "&#219;">
  <!ENTITY Uuml   "&#220;"> <!ENTITY Yacute "&#221;"> <!ENTITY THORN  "&#222;">
  <!ENTITY szlig  "&#223;"> <!ENTITY agrave "&#224;"> <!ENTITY aacute "&#225;">
  <!ENTITY acirc  "&#226;"> <!ENTITY atilde "&#227;"> <!ENTITY auml   "&#228;">
  <!ENTITY aring  "&#229;"> <!ENTITY aelig  "&#230;"> <!ENTITY ccedil "&#231;">
  <!ENTITY egrave "&#232;"> <!ENTITY eacute "&#233;"> <!ENTITY ecirc  "&#234;">
  <!ENTITY euml   "&#235;"> <!ENTITY igrave "&#236;"> <!ENTITY iacute "&#237;">
  <!ENTITY icirc  "&#238;"> <!ENTITY iuml   "&#239;"> <!ENTITY eth    "&#240;">
  <!ENTITY ntilde "&#241;"> <!ENTITY ograve "&#242;"> <!ENTITY oacute "&#243;">
  <!ENTITY ocirc  "&#244;"> <!ENTITY otilde "&#245;"> <!ENTITY ouml   "&#246;">
  <!ENTITY divide "&#247;"> <!ENTITY oslash "&#248;"> <!ENTITY ugrave "&#249;">
  <!ENTITY uacute "&#250;"> <!ENTITY ucirc  "&#251;"> <!ENTITY uuml   "&#252;">
  <!ENTITY yacute "&#253;"> <!ENTITY thorn  "&#254;"> <!ENTITY yuml   "&#255;">
  <!ENTITY Alpha  "&#913;"> <!ENTITY Beta   "&#914;"> <!ENTITY Gamma  "&#915;">
  <!ENTITY Delta  "&#916;"> <!ENTITY Epsilon "&#917;"> <!ENTITY Zeta  "&#918;">
  <!ENTITY Eta    "&#919;"> <!ENTITY Theta  "&#920;"> <!ENTITY Iota   "&#921;">
  <!ENTITY Kappa  "&#922;"> <!ENTITY Lambda "&#923;"> <!ENTITY Mu     "&#924;">
  <!ENTITY Nu     "&#925;"> <!ENTITY Xi     "&#926;"> <!ENTITY Omicron "&#927;">
  <!ENTITY Pi     "&#928;"> <!ENTITY Rho    "&#929;"> <!ENTITY Sigma  "&#931;">
  <!ENTITY Tau    "&#932;"> <!ENTITY Upsilon "&#933;"> <!ENTITY Phi   "&#934;">
  <!ENTITY Chi    "&#935;"> <!ENTITY Psi    "&#936;"> <!ENTITY Omega  "&#937;">
  <!ENTITY alpha  "&#945;"> <!ENTITY beta   "&#946;"> <!ENTITY gamma  "&#947;">
  <!ENTITY delta  "&#948;"> <!ENTITY epsilon "&#949;"> <!ENTITY zeta  "&#950;">
  <!ENTITY eta    "&#951;"> <!ENTITY theta  "&#952;"> <!ENTITY iota   "&#953;">
  <!ENTITY kappa  "&#954;"> <!ENTITY lambda "&#955;"> <!ENTITY mu     "&#956;">
  <!ENTITY nu     "&#957;"> <!ENTITY xi     "&#958;"> <!ENTITY omicron "&#959;">
  <!ENTITY pi     "&#960;"> <!ENTITY rho    "&#961;"> <!ENTITY sigma  "&#963;">
  <!ENTITY tau    "&#964;"> <!ENTITY upsilon "&#965;"> <!ENTITY phi   "&#966;">
  <!ENTITY chi    "&#967;"> <!ENTITY psi    "&#968;"> <!ENTITY omega  "&#969;">
  <!ENTITY amp    "&#38;" > <!ENTITY lt     "&#60;" > <!ENTITY gt     "&#62;" >
  <!ENTITY apos   "&#39;" > <!ENTITY quot   "&#34;" >
]>
"""

class _EntityFixStream:
    """
    Wrap a gzip file object and inject our DOCTYPE/entity declarations
    right after the XML declaration so ElementTree can parse DBLP's
    HTML entities (&uuml; etc.) without loading the external DTD.
    """
    def __init__(self, gz_path: Path):
        import gzip
        self._fh     = gzip.open(gz_path, "rb")
        self._buf    = b""
        self._done   = False   # True once we've injected the DOCTYPE

    def read(self, size: int = -1) -> bytes:
        chunk = self._fh.read(size if size > 0 else 65536)
        if not chunk:
            return b""
        if not self._done:
            # The DBLP XML starts with <?xml ...?> then <!DOCTYPE dblp ...>
            # We replace the existing DOCTYPE line with our own that
            # contains full entity definitions.
            combined = self._buf + chunk
            decl_end = combined.find(b"?>")
            if decl_end != -1:
                # Find and drop the original <!DOCTYPE ...> line
                after_decl = combined[decl_end + 2:]
                dt_start   = after_decl.find(b"<!DOCTYPE")
                dt_end     = after_decl.find(b">", dt_start) + 1 if dt_start != -1 else 0
                if dt_start != -1:
                    after_decl = after_decl[dt_end:]
                # Splice in our entity-rich DOCTYPE
                combined = (combined[:decl_end + 2]
                            + b"\n" + _HTML_ENTITIES.encode()
                            + after_decl)
                self._done = True
                return combined
            else:
                self._buf = combined
                return b""
        return chunk

    def close(self):
        self._fh.close()

    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def stream_parse_dblp_xml(gz_path: Path) -> dict:
    """
    Stream-parse dblp.xml.gz and collect papers for our four venues.

    Optimisations:
    - Uses lxml.etree if installed (3-5x faster C parser); falls back to stdlib.
    - Skips non-venue records entirely on the start event — no child elements
      are inspected for the ~99% of records that don't belong to our venues.
    - Clears each element after processing to keep memory flat.
    """
    try:
        from lxml import etree as _ET
        info("Parser: lxml (fast)")
    except ImportError:
        import xml.etree.ElementTree as _ET
        info("Parser: stdlib ElementTree  (install lxml for ~4x speedup: pip install lxml)")

    import gzip

    prefix_map = {p: vk for vk, ps in VENUE_PREFIXES.items() for p in ps}
    # Pre-sort prefixes longest-first so more-specific ones match before shorter ones
    sorted_prefixes = sorted(prefix_map, key=len, reverse=True)

    result       = {k: [] for k in VENUES}
    found        = {k: 0  for k in VENUES}
    total_parsed = 0

    info("Parsing XML dump ...")
    print()

    current_vk      = None   # venue key for the record being parsed, or None to skip
    current_rec_key = ""     # DBLP record key e.g. conf/dac/Chang2020a
    current_year    = 0
    current_title   = ""
    current_authors: list = []

    with _EntityFixStream(gz_path) as fh:
        for event, elem in _ET.iterparse(fh, events=("start", "end")):

            if event == "start":
                if elem.tag in PAPER_TAGS:
                    key      = elem.get("key", "")
                    publtype = elem.get("publtype", "")

                    # Skip non-refereed content:
                    # "informal"  = arXiv / informal notes
                    # "editor"    = proceedings front matter / edited volumes
                    # "survey"    = invited survey (usually not a regular submission)
                    # "withdrawn" = retracted papers
                    if publtype in ("informal", "editor", "survey", "withdrawn"):
                        current_vk = None
                        continue

                    # Check venue membership on the opening tag — skip immediately
                    # if this record doesn't belong to any of our four venues.
                    current_vk = next(
                        (prefix_map[p] for p in sorted_prefixes if key.startswith(p)),
                        None
                    )
                    if current_vk:
                        current_rec_key = key
                        current_year    = 0
                        current_title   = ""
                        current_authors = []

            elif event == "end":
                if elem.tag in PAPER_TAGS:
                    if current_vk and current_authors and current_year > 0:
                        result[current_vk].append({
                            "key":     current_rec_key,
                            "year":    current_year,
                            "title":   current_title,
                            "authors": current_authors,
                        })
                        found[current_vk] += 1
                    elem.clear()
                    current_vk = None
                    total_parsed += 1
                    if total_parsed % 500_000 == 0:
                        counts = "  ".join(
                            f"{VENUES[k]['label']}:{found[k]}" for k in VENUES
                        )
                        print(f"\r  {total_parsed/1_000_000:.1f}M records  |  {counts}      ",
                              end="", flush=True)

                elif current_vk is not None:
                    # We are inside a venue record — collect child elements
                    tag = elem.tag
                    if tag == "year":
                        try:
                            current_year = int(elem.text or 0)
                        except ValueError:
                            pass
                    elif tag == "title":
                        current_title = elem.text or ""
                    elif tag == "author":
                        name = (elem.text or "").strip()
                        if name:
                            current_authors.append({
                                "name": name,
                                "pid":  elem.get("pid", ""),
                            })

    print()
    return result
def process_papers(papers: list) -> dict:
    year_counts: dict = {}
    author_data: dict = {}

    # Deduplicate papers by DBLP record key first.
    # The XML dump can contain the same record more than once (e.g. a paper
    # listed under two different DAC volume keys in different years of the dump).
    seen_keys: set = set()
    deduped = []
    for p in papers:
        k = p.get("key", "")
        if k and k in seen_keys:
            continue
        if k:
            seen_keys.add(k)
        deduped.append(p)

    for p in deduped:
        y = p["year"]
        year_counts[y] = year_counts.get(y, 0) + 1
        # Deduplicate authors within a single paper — DBLP occasionally lists
        # the same person twice under different name variants on the same record.
        seen_in_paper: set = set()
        for a in p["authors"]:
            name = a["name"]
            pid  = a["pid"] or name
            if pid in seen_in_paper:
                continue
            seen_in_paper.add(pid)
            if pid not in author_data:
                author_data[pid] = {"name": name, "pid": a["pid"], "years": {}, "total": 0}
            author_data[pid]["years"][y] = author_data[pid]["years"].get(y, 0) + 1
            author_data[pid]["total"]   += 1
    return {
        "yearly":  dict(sorted(year_counts.items())),
        "authors": dict(sorted(author_data.items(), key=lambda kv: -kv[1]["total"])),
    }


def step_fetch(skip_download: bool = False) -> dict:
    banner("STEP 1 / 3  —  Fetching publication data from DBLP")

    gz_path = tmpfile("dblp.xml.gz")
    if skip_download:
        if not gz_path.exists():
            err(f"No dblp.xml.gz found at {gz_path}")
            err("Remove --skip-download to re-download it.")
            sys.exit(1)
        ok(f"Reusing existing dump  ({gz_path.stat().st_size / 1024 / 1024:.0f} MB)")
    else:
        if not download_dblp_dump(gz_path):
            sys.exit(1)
        ok(f"Download complete  ({gz_path.stat().st_size / 1024 / 1024:.0f} MB)")

    venue_papers = stream_parse_dblp_xml(gz_path)

    all_data = {}
    for key in VENUES:
        all_data[key] = process_papers(venue_papers[key])
        total_papers = sum(all_data[key]["yearly"].values())
        n_authors    = len(all_data[key]["authors"])
        ok(f"{VENUES[key]['label']}: {total_papers:,} papers  {n_authors:,} unique authors")

    out = tmpfile("dblp_data.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    ok(f"Saved -> {out}  (temp)")
    return all_data

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — ENRICH WITH SEMANTIC SCHOLAR
# ─────────────────────────────────────────────────────────────────────────────
SS_SEARCH  = "https://api.semanticscholar.org/graph/v1/author/search"
SS_FIELDS  = "name,hIndex,citationCount,paperCount"
RATE_SLEEP = 0.65   # ~92 req/min, under the 100/min free limit


def ss_lookup(name: str) -> dict | None:
    params = urllib.parse.urlencode({"query": name, "fields": SS_FIELDS, "limit": 1})
    url    = f"{SS_SEARCH}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EDA-HallOfFame"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        results = data.get("data", [])
        return results[0] if results else None
    except Exception:
        return None



def hof_qualifying_pids(dblp_data: dict) -> set:
    """
    Return (venue_key, pid_key) pairs for researchers who already qualify
    for at least one HoF tier. Only these get enriched via Semantic Scholar.
    """
    totals: dict = {}
    for vk in VENUES:
        for pid_key, ainfo in dblp_data[vk]["authors"].items():
            pid      = ainfo.get("pid", "")
            name     = ainfo["name"]
            # Apply manual override if present
            if name in NAME_OVERRIDES:
                pid = NAME_OVERRIDES[name]
            identity = pid if pid else name
            if identity not in totals:
                totals[identity] = {"dac": 0, "iccad": 0, "tcad": 0, "todaes": 0, "pairs": []}
            totals[identity][vk] += ainfo["total"]
            totals[identity]["pairs"].append((vk, pid_key))

    qualifying: set = set()
    for t in totals.values():
        if t["dac"] + t["iccad"] + t["tcad"] + t["todaes"] >= COMBINED_THRESHOLD:
            for pair in t["pairs"]:
                qualifying.add(pair)
    return qualifying


def step_enrich(dblp_data: dict) -> dict:
    banner("STEP 2 / 3  —  Enriching with h-index & citations (Semantic Scholar)")

    qualifying = hof_qualifying_pids(dblp_data)

    # Deduplicate by name (same person appears in multiple venues)
    name_to_locs: dict = {}
    for vk, pid_key in qualifying:
        ainfo = dblp_data[vk]["authors"][pid_key]
        name_to_locs.setdefault(ainfo["name"], []).append((vk, pid_key))

    unique_names = list(name_to_locs.keys())
    total = len(unique_names)
    info(f"{total:,} HoF-qualifying authors to enrich  (~{total * RATE_SLEEP / 60:.1f} min)")
    print()

    cache: dict = {}
    for i, name in enumerate(unique_names, 1):
        if i % 5 == 0 or i == total:
            progress(i, total, name[:33])
        cache[name] = ss_lookup(name) or {}
        time.sleep(RATE_SLEEP)

    print()

    for name, locs in name_to_locs.items():
        ss = cache[name]
        for vk, pid_key in locs:
            a = dblp_data[vk]["authors"][pid_key]
            a["hindex"]      = ss.get("hIndex",        0)
            a["citations"]   = ss.get("citationCount", 0)
            a["ss_papers"]   = ss.get("paperCount",    0)
            a["ss_id"]       = ss.get("authorId",      "")
            a["affiliation"] = ""   # set via AFFILIATION_OVERRIDES in build_researcher_table
    print()

    out = tmpfile("enriched_data.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dblp_data, f, ensure_ascii=False, indent=2)
    ok(f"Saved -> {out}  (temp)")
    return dblp_data


def build_researcher_table(enriched: dict) -> list[dict]:
    researchers: dict = {}

    def upsert(identity, name, pid, venue, ainfo):
        if identity not in researchers:
            researchers[identity] = {
                "name": name, "pid": pid, "ss_id": ainfo.get("ss_id", ""),
                "dac": 0, "iccad": 0, "tcad": 0, "todaes": 0,
                "hindex": ainfo.get("hindex", 0),
                "citations": ainfo.get("citations", 0),
                "affiliation": "",
                "years": {},  # {year: {dac,iccad,tcad,todaes}}
            }
        researchers[identity][venue] += ainfo["total"]
        # Accumulate per-year counts for sparkline
        for yr, cnt in ainfo.get("years", {}).items():
            yr_str = str(yr)
            if yr_str not in researchers[identity]["years"]:
                researchers[identity]["years"][yr_str] = {"dac":0,"iccad":0,"tcad":0,"todaes":0}
            researchers[identity]["years"][yr_str][venue] = \
                researchers[identity]["years"][yr_str].get(venue, 0) + cnt
        # Prefer the longer/fuller name for display
        if len(name) > len(researchers[identity]["name"]):
            researchers[identity]["name"] = name
        # Prefer non-empty PID
        if pid and not researchers[identity]["pid"]:
            researchers[identity]["pid"] = pid
        if ainfo.get("hindex", 0) > researchers[identity]["hindex"]:
            researchers[identity]["hindex"]    = ainfo["hindex"]
            researchers[identity]["citations"] = ainfo.get("citations", 0)
            researchers[identity]["ss_id"]     = ainfo.get("ss_id", "")
    # Apply manual affiliation overrides (strips DBLP number suffix for matching)
    import re as _re
    for r in researchers.values():
        clean = _re.sub(r"\\s+\\d{4}$", "", r["name"]).strip()
        r["affiliation"] = AFFILIATION_OVERRIDES.get(clean, "")

    for vk in VENUES:
        for pid_key, ainfo in enriched[vk]["authors"].items():
            pid = ainfo.get("pid", "")
            # Primary identity: DBLP PID (globally unique, best)
            # Fallback: normalised name key (handles variants like "D. F. Wong"
            # vs "Martin D. F. Wong" when DBLP hasn't assigned a PID)
            identity = pid if pid else ainfo["name"]
            upsert(identity, ainfo["name"], pid, vk, ainfo)

    rows = []
    for r in researchers.values():
        conf_total    = r["dac"] + r["iccad"]
        journal_total = r["tcad"] + r["todaes"]
        total         = conf_total + journal_total
        if total < COMBINED_THRESHOLD:
            continue
        rows.append({**r,
            "conf_total": conf_total, "journal_total": journal_total,
            "total": total,
        })

    rows.sort(key=lambda x: -x["total"])
    return rows


def step_generate(enriched: dict):
    banner("STEP 3 / 3  —  Generating data.js")

    researchers = build_researcher_table(enriched)
    yearly = {
        vk: {str(y): c for y, c in enriched[vk]["yearly"].items()}
        for vk in VENUES
    }
    today = date.today().isoformat()

    js = f"""// Auto-generated by run.py on {today}
// DO NOT EDIT MANUALLY — re-run: python run.py --skip-fetch --skip-enrich

const LAST_UPDATED = "{today}";
const COMBINED_THRESHOLD = {COMBINED_THRESHOLD};

const RESEARCHERS = {json.dumps(researchers, ensure_ascii=False, indent=2)};

const YEARLY = {json.dumps(yearly, ensure_ascii=False, indent=2)};
"""
    out = REPO_DIR / "data.js"
    with open(out, "w", encoding="utf-8") as f:
        f.write(js)

    ok(f"Saved → {out}  ({len(researchers)} researchers inducted into Hall of Fame)")

    missing_affil = sum(1 for r in researchers if not r.get("affiliation"))
    if missing_affil:
        print()
        print(f"  {YELLOW}Affiliation tip:{RESET}")
        print(f"  {missing_affil} researchers are missing affiliations in data.js.")
        print(f"  Tip: paste the RESEARCHERS array into an AI assistant and ask:")
        print(f"  'Fill in the affiliation field with the university name for each")
        print(f"   researcher based on your knowledge. Leave blank if unsure.'")
        print(f"  Then add the results to AFFILIATION_OVERRIDES in run.py.")


def serve(port: int):
    import http.server, threading, webbrowser

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass

    with http.server.HTTPServer(("", port), QuietHandler) as httpd:
        url = f"http://localhost:{port}"
        banner("Preview server")
        ok(f"Open → {BOLD}{url}{RESET}")
        info("Press Ctrl+C to stop.")
        threading.Thread(target=lambda: (time.sleep(0.4), webbrowser.open(url)),
                         daemon=True).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n{YELLOW}  Server stopped.{RESET}")

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    global TMP_DIR

    parser = argparse.ArgumentParser(
        description="EDA Hall of Fame — data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--skip-download", action="store_true",
                        help="Reuse ./tmp/dblp.xml.gz and re-parse it (skip download only)")
    parser.add_argument("--skip-fetch",  action="store_true",
                        help="Reuse existing dblp_data.json (skip download AND parse)")
    parser.add_argument("--skip-enrich", action="store_true",
                        help="Skip Semantic Scholar (no h-index/citations)")
    parser.add_argument("--serve",       action="store_true",
                        help="Open browser preview after generation")
    parser.add_argument("--port",        type=int, default=8000)
    args = parser.parse_args()

    # Ensure ./tmp exists
    setup_tmpdir()
    info(f"Working directory: {TMP_DIR}")

    print(f"\n{BOLD}EDA Hall of Fame — Data Pipeline{RESET}")
    print(f"Venues     : {', '.join(v['label'] for v in VENUES.values())}")
    print(f"Threshold  : Combined (DAC+ICCAD+TCAD+TODAES) ≥ {COMBINED_THRESHOLD}")

    # ── Step 1 ───────────────────────────────────────────────────────────────
    if args.skip_fetch:
        # Look for dblp_data.json in the temp dir or fall back to repo dir
        # (useful if re-running after a partial run in the same session)
        candidates = [
            tmpfile("dblp_data.json"),
            REPO_DIR / "dblp_data.json",
        ]
        src = next((p for p in candidates if p.exists()), None)
        if src is None:
            err("No dblp_data.json found anywhere — cannot use --skip-fetch.")
            err("Run without --skip-fetch first to download the DBLP dump.")
            sys.exit(1)
        warn(f"Skipping DBLP fetch — loading {src}")
        with open(src, encoding="utf-8") as f:
            dblp_data = json.load(f)

        # Sanity check — print paper counts so you can spot an empty/stale file
        for vk, meta in VENUES.items():
            n = sum(dblp_data.get(vk, {}).get("yearly", {}).values())
            n_authors = len(dblp_data.get(vk, {}).get("authors", {}))
            if n == 0:
                warn(f"{meta['label']}: 0 papers — this looks wrong! "
                     f"Re-run without --skip-fetch to re-download.")
            else:
                ok(f"{meta['label']}: {n:,} papers  {n_authors:,} authors  (from cache)")

        total_papers = sum(
            sum(dblp_data.get(vk, {}).get("yearly", {}).values())
            for vk in VENUES
        )
        if total_papers == 0:
            err("Cached dblp_data.json has 0 papers across all venues.")
            err("This was likely saved by an older broken version of the script.")
            err("Delete it and re-run without --skip-fetch:")
            err(f"  rm {src} && python run.py")
            sys.exit(1)
    else:
        dblp_data = step_fetch(skip_download=args.skip_download)

    # ── Step 2 ───────────────────────────────────────────────────────────────
    if args.skip_enrich:
        warn("Skipping Semantic Scholar — h-index and citations will be 0")
        enriched = dblp_data
    else:
        enriched = step_enrich(dblp_data)

    # ── Step 3 ───────────────────────────────────────────────────────────────
    step_generate(enriched)

    print(f"\n{BOLD}{GREEN}  ✓  All done!  Temp files in {TMP_DIR} will be deleted now.{RESET}")
    print(f"  Commit and push:")
    print(f"  {CYAN}git add data.js && git commit -m 'Data refresh' && git push{RESET}\n")

    if args.serve:
        serve(args.port)


if __name__ == "__main__":
    main()
