"""
Tests for EDA Hall of Fame pipeline (run.py).

Run with:
    pytest tests/ -v
    pytest tests/test_pipeline.py -v
    pytest tests/test_pipeline.py::TestProcessPapers -v
"""

import sys
import os
import importlib
import types
import unittest

# ── Import run.py as a module ────────────────────────────────────────────────
# run.py is a script, not a package. We load it dynamically and patch the
# globals that require network access or file I/O so tests are self-contained.

def _load_run() -> types.ModuleType:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run",
        os.path.join(os.path.dirname(__file__), "..", "run.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

RUN = _load_run()

# Convenience aliases
process_papers          = RUN.process_papers
build_researcher_table  = RUN.build_researcher_table
hof_qualifying_pids     = RUN.hof_qualifying_pids
COMBINED_THRESHOLD      = RUN.COMBINED_THRESHOLD
VENUES                  = RUN.VENUES


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_author(name, pid="", total=10, years=None):
    """Build a minimal author record as stored in dblp_data."""
    return {
        "name": name,
        "pid":  pid,
        "years": years or {2020: total},
        "total": total,
        "hindex": 0, "citations": 0, "ss_papers": 0, "ss_id": "",
        "affiliation": "",
    }


def _make_dblp_data(venue_authors: dict) -> dict:
    """
    Build a minimal dblp_data dict.
    venue_authors: {venue_key: [(name, pid, total), ...]}
    """
    data = {}
    for vk in VENUES:
        entries = venue_authors.get(vk, [])
        authors = {}
        yearly  = {}
        for name, pid, total in entries:
            key = pid if pid else name
            authors[key] = _make_author(name, pid, total)
            yearly[2020]  = yearly.get(2020, 0) + total
        data[vk] = {"authors": authors, "yearly": yearly}
    return data


# ─────────────────────────────────────────────────────────────────────────────
#  TestProcessPapers
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessPapers(unittest.TestCase):

    def _paper(self, key, year, authors):
        return {
            "key":     key,
            "year":    year,
            "title":   "Test Paper",
            "authors": [{"name": n, "pid": p} for n, p in authors],
        }

    def test_basic_count(self):
        papers = [
            self._paper("conf/dac/A2020", 2020, [("Alice", "p1")]),
            self._paper("conf/dac/B2020", 2020, [("Bob",   "p2")]),
            self._paper("conf/dac/A2021", 2021, [("Alice", "p1")]),
        ]
        result = process_papers(papers)
        self.assertEqual(result["yearly"][2020], 2)
        self.assertEqual(result["yearly"][2021], 1)
        self.assertEqual(result["authors"]["p1"]["total"], 2)
        self.assertEqual(result["authors"]["p2"]["total"], 1)

    def test_dedup_by_key(self):
        """Duplicate record keys must be counted only once."""
        papers = [
            self._paper("conf/dac/A2020", 2020, [("Alice", "p1")]),
            self._paper("conf/dac/A2020", 2020, [("Alice", "p1")]),  # duplicate
        ]
        result = process_papers(papers)
        self.assertEqual(result["yearly"][2020], 1)
        self.assertEqual(result["authors"]["p1"]["total"], 1)

    def test_dedup_author_within_paper(self):
        """Same author listed twice on one paper should count once."""
        papers = [
            self._paper("conf/dac/A2020", 2020, [("Alice", "p1"), ("Alice", "p1")]),
        ]
        result = process_papers(papers)
        self.assertEqual(result["authors"]["p1"]["total"], 1)

    def test_no_pid_falls_back_to_name(self):
        """Authors without PID use name as key."""
        papers = [
            self._paper("conf/dac/A2020", 2020, [("Alice", "")]),
        ]
        result = process_papers(papers)
        self.assertIn("Alice", result["authors"])
        self.assertEqual(result["authors"]["Alice"]["total"], 1)

    def test_yearly_breakdown(self):
        papers = [
            self._paper("conf/dac/A2020", 2020, [("Alice", "p1")]),
            self._paper("conf/dac/A2021", 2021, [("Alice", "p1")]),
            self._paper("conf/dac/A2022", 2022, [("Alice", "p1")]),
        ]
        result = process_papers(papers)
        self.assertEqual(result["authors"]["p1"]["years"][2020], 1)
        self.assertEqual(result["authors"]["p1"]["years"][2021], 1)
        self.assertEqual(result["authors"]["p1"]["years"][2022], 1)
        self.assertEqual(result["authors"]["p1"]["total"], 3)

    def test_empty_input(self):
        result = process_papers([])
        self.assertEqual(result["yearly"], {})
        self.assertEqual(result["authors"], {})

    def test_no_key_still_counts(self):
        """Papers with no key should not be deduplicated against each other."""
        papers = [
            {"key": "", "year": 2020, "title": "T1", "authors": [{"name": "Alice", "pid": "p1"}]},
            {"key": "", "year": 2020, "title": "T2", "authors": [{"name": "Alice", "pid": "p1"}]},
        ]
        result = process_papers(papers)
        self.assertEqual(result["authors"]["p1"]["total"], 2)


# ─────────────────────────────────────────────────────────────────────────────
#  TestBuildResearcherTable
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildResearcherTable(unittest.TestCase):

    def test_basic_threshold(self):
        """Researcher below threshold should not appear."""
        data = _make_dblp_data({
            "dac": [("Alice", "p1", 60)],  # above threshold
            "iccad": [("Bob",  "p2", 10)],  # below threshold
        })
        rows = build_researcher_table(data)
        names = [r["name"] for r in rows]
        self.assertIn("Alice", names)
        self.assertNotIn("Bob", names)

    def test_combined_threshold_across_venues(self):
        """Papers summed across venues must meet threshold."""
        # 25 DAC + 26 ICCAD = 51 >= 50 — should qualify
        data = _make_dblp_data({
            "dac":   [("Alice", "p1", 25)],
            "iccad": [("Alice", "p1", 26)],
        })
        rows = build_researcher_table(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total"], 51)

    def test_combined_threshold_not_met(self):
        """Papers just below threshold should be excluded."""
        data = _make_dblp_data({
            "dac":   [("Alice", "p1", 24)],
            "iccad": [("Alice", "p1", 25)],
        })
        rows = build_researcher_table(data)
        self.assertEqual(len(rows), 0)

    def test_pid_merges_same_person(self):
        """Two entries with same PID must merge into one researcher."""
        data = _make_dblp_data({
            "dac":   [("Alice Smith", "p1", 30)],
            "iccad": [("A. Smith",    "p1", 25)],
        })
        rows = build_researcher_table(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total"], 55)

    def test_name_override_merges_wong(self):
        """NAME_OVERRIDES must merge D. F. Wong and Martin D. F. Wong."""
        data = _make_dblp_data({
            "dac": [
                ("Martin D. F. Wong", "", 39),
                ("D. F. Wong 0001",   "", 30),
            ],
            "iccad": [
                ("Martin D. F. Wong", "", 51),
                ("D. F. Wong 0001",   "", 35),
            ],
        })
        rows = build_researcher_table(data)
        # Should be exactly ONE researcher (merged), not two
        wong_rows = [r for r in rows if "Wong" in r["name"]]
        self.assertEqual(len(wong_rows), 1, 
            f"Expected 1 Wong entry, got {len(wong_rows)}: {[r['name'] for r in wong_rows]}")
        self.assertEqual(wong_rows[0]["dac"],   39 + 30)
        self.assertEqual(wong_rows[0]["iccad"], 51 + 35)

    def test_name_override_suffix_stripped(self):
        """NAME_OVERRIDES must match names with DBLP number suffix stripped."""
        # "D. F. Wong 0001" should match override for "D. F. Wong"
        self.assertIn("D. F. Wong 0001", RUN.NAME_OVERRIDES)

    def test_sorted_by_total_descending(self):
        """Output must be sorted by total papers descending."""
        data = _make_dblp_data({
            "dac": [
                ("Alice", "p1", 60),
                ("Bob",   "p2", 80),
                ("Carol", "p3", 70),
            ],
        })
        rows = build_researcher_table(data)
        totals = [r["total"] for r in rows]
        self.assertEqual(totals, sorted(totals, reverse=True))

    def test_venue_counts_correct(self):
        """Per-venue counts must be accurate in output."""
        data = _make_dblp_data({
            "dac":    [("Alice", "p1", 20)],
            "iccad":  [("Alice", "p1", 15)],
            "tcad":   [("Alice", "p1", 10)],
            "todaes": [("Alice", "p1", 6)],
        })
        rows = build_researcher_table(data)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["dac"],    20)
        self.assertEqual(r["iccad"],  15)
        self.assertEqual(r["tcad"],   10)
        self.assertEqual(r["todaes"],  6)
        self.assertEqual(r["total"],  51)

    def test_affiliation_override_applied(self):
        """AFFILIATION_OVERRIDES must be applied to matching researchers."""
        data = _make_dblp_data({
            "dac": [("Tsung-Wei Huang", "p_twh", 51)],
        })
        rows = build_researcher_table(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["affiliation"], "University of Wisconsin-Madison")

    def test_affiliation_suffix_stripped_for_match(self):
        """Affiliation override must match even when name has DBLP number suffix."""
        data = _make_dblp_data({
            "dac": [("Bei Yu 0001", "p_by", 51)],
        })
        rows = build_researcher_table(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["affiliation"], "Chinese University of Hong Kong")

    def test_prefer_longer_name(self):
        """When two entries share a PID, the longer name is preferred for display."""
        data = _make_dblp_data({
            "dac":   [("A. Smith",    "p1", 30)],
            "iccad": [("Alice Smith", "p1", 25)],
        })
        rows = build_researcher_table(data)
        self.assertEqual(rows[0]["name"], "Alice Smith")


# ─────────────────────────────────────────────────────────────────────────────
#  TestHofQualifyingPids
# ─────────────────────────────────────────────────────────────────────────────

class TestHofQualifyingPids(unittest.TestCase):

    def test_qualifies_above_threshold(self):
        data = _make_dblp_data({"dac": [("Alice", "p1", 60)]})
        pids = hof_qualifying_pids(data)
        self.assertTrue(len(pids) > 0)

    def test_does_not_qualify_below_threshold(self):
        data = _make_dblp_data({"dac": [("Bob", "p2", 10)]})
        pids = hof_qualifying_pids(data)
        self.assertEqual(len(pids), 0)

    def test_qualifies_combined_across_venues(self):
        """Papers spread across venues must be summed for qualifying check."""
        data = _make_dblp_data({
            "dac":   [("Alice", "p1", 25)],
            "iccad": [("Alice", "p1", 26)],
        })
        pids = hof_qualifying_pids(data)
        self.assertTrue(len(pids) > 0)

    def test_name_override_applied_in_qualifying(self):
        """NAME_OVERRIDES must be applied during qualifying check too."""
        data = _make_dblp_data({
            "dac": [
                ("Martin D. F. Wong", "", 39),
                ("D. F. Wong 0001",   "", 30),
            ],
        })
        pids = hof_qualifying_pids(data)
        # Both entries belong to same person — both pairs should be included
        self.assertEqual(len(pids), 2)


# ─────────────────────────────────────────────────────────────────────────────
#  TestNameOverrides
# ─────────────────────────────────────────────────────────────────────────────

class TestNameOverrides(unittest.TestCase):

    def test_wong_variants_all_present(self):
        """All known D. F. Wong name variants must be in NAME_OVERRIDES."""
        for name in ["D. F. Wong", "D. F. Wong 0001", "D.F. Wong", "Martin D. F. Wong"]:
            self.assertIn(name, RUN.NAME_OVERRIDES,
                f"'{name}' missing from NAME_OVERRIDES")

    def test_wong_all_map_to_same_key(self):
        """All Wong variants must map to the same canonical identity."""
        keys = {RUN.NAME_OVERRIDES[n] for n in RUN.NAME_OVERRIDES
                if "Wong" in n}
        self.assertEqual(len(keys), 1, f"Wong variants map to different keys: {keys}")

    def test_end_to_end_wong_merge(self):
        """Full pipeline: two Wong entries must produce exactly one row."""
        data = _make_dblp_data({
            "dac":    [("Martin D. F. Wong", "", 39), ("D. F. Wong 0001", "", 30)],
            "iccad":  [("Martin D. F. Wong", "", 51), ("D. F. Wong 0001", "", 35)],
            "tcad":   [("Martin D. F. Wong", "", 92)],
            "todaes": [("Martin D. F. Wong", "", 13), ("D. F. Wong 0001", "", 7)],
        })
        rows = build_researcher_table(data)
        wong = [r for r in rows if "Wong" in r["name"]]
        self.assertEqual(len(wong), 1)
        self.assertEqual(wong[0]["dac"],    69)
        self.assertEqual(wong[0]["iccad"],  86)
        self.assertEqual(wong[0]["tcad"],   92)
        self.assertEqual(wong[0]["todaes"], 20)
        self.assertEqual(wong[0]["total"], 267)


# ─────────────────────────────────────────────────────────────────────────────
#  TestThresholdConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestThresholdConfig(unittest.TestCase):

    def test_combined_threshold_is_50(self):
        self.assertEqual(COMBINED_THRESHOLD, 50)

    def test_exactly_at_threshold_qualifies(self):
        data = _make_dblp_data({"dac": [("Alice", "p1", 50)]})
        rows = build_researcher_table(data)
        self.assertEqual(len(rows), 1)

    def test_one_below_threshold_excluded(self):
        data = _make_dblp_data({"dac": [("Alice", "p1", 49)]})
        rows = build_researcher_table(data)
        self.assertEqual(len(rows), 0)

    def test_venues_are_correct(self):
        self.assertEqual(set(VENUES.keys()), {"dac", "iccad", "tcad", "todaes"})


if __name__ == "__main__":
    unittest.main()
