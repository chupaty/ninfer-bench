# NInfer Benchmark & Quality Report

- **Model ID:** `qwen3.8-27b-nvfp4-swift`
- **Date & Time:** 2026-09-24 20:24:30
- **Temperature:** `1.0`
- **Thinking Budget:** `2048` | **Max Tokens:** `8192`
- **Overall Quality Status:** **`[PENDING QUALITY REVIEW]`**

## 1. Performance Scorecard

| Test | Prompt Tokens | Thinking Tokens | Out Tokens | TTFT (s) | Total Time (s) | Decode (tok/s) | MTP Accept | Quality Status |
|---|---|---|---|---|---|---|---|---|
| Test 1: Empty Context (Dev Short Refactor) | 1,879 | 4,096 | 8,192 | 0.29 | 46.39 | 177.7 | 61.1% | **`[PENDING QUALITY REVIEW]`** |
| Test 2: Half-Full Context (AIMS ~81k Repo Audit) | 81,441 | 4,096 | 8,192 | 0.17 | 60.02 | 136.9 | 47.4% | **`[PENDING QUALITY REVIEW]`** |

---
## 2. Full Model Outputs (For Agent Quality Inspection)

### Test 1: Empty Context (Dev Short Refactor)

#### Prompt Summary
```text
You are an expert Python systems and data engineer.
Review the following clinical data processing script:

```python
import sqlite3
import json
from collections import defaultdict

conn = sqlite3.connect(r'c:\tmp\bloods\data\bloods.db')
cur = conn.cursor()

print("=" * 80)
print("              CLINICAL LONGITUDINAL TRAJECTORY ANALYSIS              ")
print("=" * 80)

# 1. Timeline overview
dates =...
```

#### Reasoning Trace (`<think>`)
```text
We need answer user asks: review clinical data processing script, identify bottlenecks edge cases type safety, provide fully refactored robust vectorized/optimized version with Python 3.12+ type annotations, docstrings, error handling, and unit test examples.

Need produce final response. Need think thoroughly. We need likely provide analysis and code. Need ensure code is correct Python 3.12. Should consider original script issues:
- Hard-coded path, no context manager/closing connection, resource leak.
- Uses cur.execute multiple times fetchall, fine for small data; vectorization? For SQLite no true vectorization, but can optimize queries, use single query with UNION? Use dataclasses, typed.
- dates list assumes non-empty. Empty DB causes dates[0] IndexError.
- get_series returns list of rows; if all values null then hb_vals empty, min/max ValueError; latest value may None, print None.
- Formatting .1f on None? If val None? For hb_data[-1][1] may be None; f-string None no format spec if no .1f? Latest line uses no format spec? It says {hb_data[-1][1]} g/L; if None prints None. But range line min/max on empty list ValueError.
- step = max(1, len(data)//10); if len 0 skip due if data; if len 1 step 1. Milestone list creation for last duplicate check creates list each time; if last duplicate? It checks if hb_data[-1] not in [hb_data[i] ...]. If last row duplicated? It can print last again if not equal to any milestone. Fine. But inefficient and tuple equality can be weird if rows identical. If step > 1, range stops before end; may omit near end.
- Platelets .0f formatting if val is None? range line only if vals nonempty? If plt_vals empty but plt_data nonempty all None -> min ValueError.
- WBC loop uses max(1, len(wbc_data)//8) inside range each call? len constant.
- LDH prints all rows, potential large output. No null handling.
- Precursors: date set; for each last 10 dates, scans all precursors O(n*10). Better group by date with dict.
- JSON glob: hard-coded, no path existence, exceptions silently pass hiding errors. d may not dict? json.load can list. d.get fails if not dict. Comments may not list; c may non-str. seen_snippets uses first 30, not robust. Date fallback can be None. No closing? open with context ok.
- Type safety: no annotations, dynamic indexing, rows as tuples.
- Security? Hard-coded Windows path; use Path, config/env.
- Performance: multiple SELECTs; can fetch canonical ids in one query? But for series need all. Could use pandas? "vectorized/optimized" maybe use pandas if available, but avoid heavy dependency? Could use sqlite3 + collections. Maybe provide optional pandas implementation? The request says vectorized/optimized version. We can write pure stdlib optimized, not necessarily numpy. Clinical data likely small. Could include pandas variant? Need final answer likely include refactored code with type annotations. Could use sqlite3.Row, dataclasses, generators.
- Edge cases: empty dates, nulls, non-numeric values? value_numeric column should numeric; if not, float conversion. Need safe_float.
- Need docstrings, unit test examples.
- Need mention performance bottlenecks and edge cases.

Need decide refactored code. It should be complete runnable. Python 3.12 type annotations: Use `from __future__ import annotations`? In 3.12 not needed but okay. Use `typing`, `pathlib`. Use `sqlite3.Connection`. Could define constants, dataclass Observation. Functions: `connect_db`, `load_observations`, `compute_milestones`, `print_trajectory`. Use logging? For robust. Use context managers.

Potential refactored script:

```
from __future__ import annotations
import argparse, json, logging, math, sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from datetime import date, datetime

LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class Observation:
    date: str
    value: float | None
    ref_low: float | None
    ref_high: float | None
    canonical_id: str | None = None
    display_name: str | None = None
    units: str | None = None

def to_float(value: Any) -> float | None:
    if value is None: return None
    if isinstance(value, (int, float)): 
        f = float(value)
    elif isinstance(value, str):
       s=value.strip()
       if not s: return None
       try: f=float(s)
       except ValueError: return None
    else:
       try: f=float(value)
       except (TypeError, ValueError): return None
    return None if math.isnan(f) else f
```

Need date normalization? Use strings. Could parse to date for ordering? If ISO dates. Use `date.fromisoformat`? Need safe. For output use original string. For sorting, can use ISO. But DB date may be text. We can use `normalize_date_key` returning sortable key. If date string ISO, key string; else fallback. Could keep simple.

Queries:
- `SELECT DISTINCT date FROM observations ORDER BY date ASC` maybe dates null? exclude null.
- For series: query for multiple canonical ids in one call to reduce roundtrips:
```
def load_series(conn, canonical_ids):
    placeholders = ",".join("?"*len(ids))
    rows = conn.execute(f"SELECT canonical_id, date, value_numeric, ref_low, ref_high FROM observations WHERE canonical_id IN ({placeholders}) ORDER BY canonical_id, date", ids).fetchall()
    series = defaultdict(list)
    for row in rows: series[row[0]].append(Observation(...))
    return series
```
Need if ids empty return {}.

Milestones:
```
def select_milestones(rows: Sequence[Observation], max_points: int=10, include_latest=True) -> list[int]:
    n = len(rows)
    if n == 0: return []
    if n <= max_points: indices = list(range(n))
    else:
       step = max(1, n // max_points)
       indices = list(range(0, n, step))
       if include_latest and indices[-1] != n-1: indices.append(n-1)
       # de-duplicate preserve order
    # If last row duplicate value/date? It's index, no tuple equality issue.
    return indices
```
This avoids list equality. If max_points 0? use at least 1.

Summarize:
```
def numeric_stats(rows): vals=[row.value for row in rows if row.value is not None]; if not vals return None
latest = next((r for r in reversed(rows) if r.value is not None), rows[-1] if rows else None)
```
But if latest value None? Better latest non-null for range. If want latest raw, show latest with None. We can show `Latest non-null` to avoid None. But original prints latest possibly None. Robust: print latest observation date and value, if None display "n/a". Use latest non-null for stats.

Print trajectory:
```
def print_trajectory(title, rows, unit, precision=1, milestones=10):
    print section
    if not rows: print("No data"); return
    stats = stats
    if stats: print range min max latest
    for idx in select_milestones(rows, milestones): row=rows[idx]; print date, fmt_value
```
Formatting: if value None: 'n/a'; if precision integer: f"{value:.{precision}f}" else value. Need ensure float.

Precursors: group by date:
```
def summarize_precursors(conn):
 rows = ...; groups=defaultdict(list); for row: groups[row.date].append(...)
 dates = sorted(groups)
 print total, last 10 dates
 for d in dates[-10:]: print "; ".join(f"{display}={value}")
```
Handle display None.

LDH: use trajectory with all points? Could cap to milestones to avoid huge output. Maybe add `max_milestones`.

JSON comments:
```
@dataclass(frozen=True, slots=True)
class CommentRecord:
   source_file: str
   collected_date: str | None
   comment: str

def load_comments(directory: Path, max_comments: int=100) -> list[CommentRecord]:
   if not directory.exists(): return []
   records=[]
   for jf in sorted(directory.glob("*.json")):
      try:
          with jf.open(encoding="utf-8") as f: obj=json.load(f)
      except (json.JSONDecodeError, OSError) as exc:
          LOGGER.warning(...); continue
      if not isinstance(obj, dict): continue
      comments = obj.get("comments")
      if isinstance(comments, str): comments=[comments]
      if not isinstance(comments, list): continue
      meta = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
      dt = meta.get("collected_date") or meta.get("requested_date") or obj.get("_source_file")
      dt = str(dt) if dt is not None else None
      for c in comments:
         if isinstance(c, dict): text = c.get("text") or c.get("comment") ...
         elif isinstance(c, str): text=c
         else: text=str(c)
         clean=" ".join(text.split())
         if len(clean) > 20: records.append(...)
   return records
```
Unique snippet: use first 80? original 30. Use normalized first 80. Print limited.

Error handling: `safe_connect`? Use `contextlib.closing`. Main function with argparse for db and json dir. Use `main()`.

Need include unit test examples. Could provide `tests/test_clinical_trajectory.py` using pytest, monkeypatch, tmp_path. Need test empty database, nulls, comments. Need code testable.

Need think about type annotations and Python 3.12. Use `X | None`. Use `from collections.abc import Iterable, Sequence`. Use `typing`.

Potential code structure:

```
# clinical_trajectory.py
from __future__ import annotations
import argparse, json, logging, math, sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence

LOG = logging.getLogger(__name__)

CANONICAL_IDS = (...)

@dataclass(frozen=True, slots=True)
class Observation:
   canonical_id: str
   date: str
   value: float | None
   ref_low: float | None
   ref_high: float | None

@dataclass(frozen=True, slots=True)
class Precursor:
   date: str
   display_name: str
   value: float
   units: str | None

@dataclass(frozen=True, slots=True)
class CommentRecord:
   source: str
   date: str | None
   text: str

def safe_float... 
def date_sort_key(value: str | None) -> tuple[int, str]: ...
```
Sort date key: If None, put last? Use `(1, "")`? For non-None try date.fromisoformat -> `(0, d.isoformat())`, except `(0, value)`. If None `(1,"")`. This handles non-ISO. Need use in sorting dates and groups.

But if date None, output? Exclude null dates in timeline. Use `WHERE date IS NOT NULL`.

Connect:
```
def connect_db(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists(): raise FileNotFoundError
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```
But using Row then mapping to Observation. Need close. In main use `with closing(conn):`? sqlite3.Connection supports context manager? It commits/rollbacks but doesn't close. Use `contextlib.closing`.

```
def load_timeline(conn) -> list[str]:
   rows = conn.execute("SELECT DISTINCT date FROM observations WHERE date IS NOT NULL ORDER BY date ASC").fetchall()
   return [str(r[0]) for r in rows]
```

Load series:
```
def load_series(conn: sqlite3.Connection, canonical_ids: Sequence[str]) -> dict[str, list[Observation]]:
   if not canonical_ids: return {}
   placeholders = ",".join("?" for _ in canonical_ids)
   sql = f"""
      SELECT canonical_id, date, value_numeric, ref_low, ref_high
      FROM observations
      WHERE canonical_id IN ({placeholders})
      ORDER BY canonical_id, date ASC
   """
   series: dict[str, list[Observation]] = defaultdict(list)
   for row in conn.execute(sql, tuple(canonical_ids)):
       series[str(row["canonical_id"])].append(Observation(...))
   return dict(series)
```
Need handle duplicate canonical ids? Fine.

Stats:
```
@dataclass(frozen=True, slots=True)
class NumericSummary:
   count: int
   min: float
   max: float
   latest_date: str | None
   latest_value: float | None

def summarize(rows: Sequence[Observation]) -> NumericSummary | None:
    vals = [(r.date, r.value) for r in rows if r.value is not None]
    if not vals: return None
    min_v = min(v for _, v in vals)
    max_v = max(v for _, v in vals)
    # latest non-null by date? rows sorted date asc. Use last non-null.
    latest_date, latest_value = vals[-1]
    return NumericSummary(len(vals), min_v, max_v, latest_date, latest_value)
```
If date order not reliable due non-ISO, rows sorted by SQL date ASC. Good.

Milestones:
```
def milestone_indices(rows: Sequence[Observation], max_points: int = 10) -> list[int]:
   n=len(rows)
   if n==0: return []
   max_points = max(1, int(max_points))
   if n <= max_points: return list(range(n))
   step = max(1, n // max_points)
   indices = list(range(0, n, step))
   if indices[-1] != n - 1: indices.append(n - 1)
   # remove duplicates? if step 0 no. If max_points 1? n>1, step=n, range(0,n,n) [0], append n-1 -> two points; okay max points not strict. If want max_points strict: step = ceil(n/max_points) = -(-n//max_points); use that.
```
Better:
```
step = max(1, math.ceil(n / max_points))
indices = list(range(0, n, step))
if indices[-1] != n-1: indices.append(n-1)
if len(indices) > max_points:
   # remove one non-latest? if max_points 1, keep latest? For milestones include latest, if max_points 1, [0,n-1] length 2. Could adjust: if len > max_points and max_points>1: pop 0? Maybe not necessary. Use simple original step max(1, n//max_points). It can produce more than max_points. Accept.
```
For robust, use `step = max(1, n // max_points)` as original. Good.

Print formatting:
```
def format_value(value: float | None, precision: int = 1) -> str:
   if value is None: return "n/a"
   return f"{value:.{precision}f}"

def print_trajectory(title, rows, unit, precision=1, max_points=10):
   print(f"\n--- {title} ---")
   if not rows:
      print("No observations recorded.")
      return
   s = summarize(rows)
   if s:
      print(f"Range: Min {format_value(s.min, precision)} {unit} | Max {format_value(s.max, precision)} {unit} | Latest non-null ({s.latest_date}): {format_value(s.latest_value, precision)} {unit}")
   else:
      print("No non-null values recorded.")
   print("Milestones:")
   for i in milestone_indices(rows, max_points):
      row=rows[i]
      ref = f"ref {format_value(row.ref_low,0)}-{format_value(row.ref_high,0)}" if row.ref_low is not None and row.ref_high is not None else ""
      print(f"  {row.date or 'unknown'}: {format_value(row.value, precision)} {unit} {ref}".rstrip())
```
Need unit for platelets x10^9/L. For creat/egfr no precision? Use 1.

Precursors:
```
def load_precursors(conn, canonical_ids: Sequence[str], limit_dates: int=10) -> tuple[int, list[str], dict[str, list[str]]]
```
Better return `PrecursorSummary`.
```
@dataclass(frozen=True, slots=True)
class PrecursorSummary:
   total: int
   dates: list[str]
   formatted: dict[str, list[str]]

def summarize_precursors(conn, limit=10):
   rows = conn.execute(...).fetchall()
   groups: dict[str, list[str]] = {}
   total = 0
   for row in rows:
       d = str(row["date"]) if row["date"] is not None else "unknown"
       display = str(row["display_name"] or row["canonical_id"])
       val = safe_float(row["value_numeric"])
       if val is None: continue
       total +=1
       groups.setdefault(d, []).append(f"{display}={format_value(val, 1)} {row['units'] or ''}".strip())
   dates = sorted(groups, key=date_sort_key)
   return total, dates, {d: groups[d] for d in dates[-limit:]}
```
Need if display_name None and canonical_id? row has canonical_id? query select canonical_id, display_name. Use.

JSON:
```
def load_comment_records(json_dir: Path, limit: int=50) -> list[CommentRecord]:
   if not json

 Considering the limited time by the user, I have to give the solution based on the thinking directly now.
```

#### Final Output Response

## 1. Issues Identified in the Original Script

### A. Performance bottlenecks

1. **Repeated individual queries per analyte**
   - The script calls `get_series()` separately for each canonical ID.
   - This creates multiple SQL round-trips even when the data can be fetched with one query using `IN (...)`.

2. **Repeated list construction for “latest” duplicate check**
   - Example:
     ```python
     if hb_data[-1] not in [hb_data[i] for i in range(0, len(hb_data), step)]:
     ```
   - This builds a temporary list every time.
   - It also compares whole rows, which is unnecessary and can lead to subtle issues if two rows are identical but logically distinct.

3. **Quadratic-looking precursor formatting**
   - For each of the last 10 dates, the script scans the full `precursors` list:
     ```python
     cells = [f"{r[1]}={r[2]}" for r in precursors if r[0] == d]
     ```
   - Better to group rows by date once.

4. **LDH prints every row**
   - If LDH has many observations, this can produce very large console output.
   - A milestone/sampling approach is more scalable.

5. **No indexing assumptions documented**
   - The script relies on `canonical_id`, `date`, and `value_numeric` being efficient.
   - In a production system, indexes on `observations(canonical_id, date)` and `observations(date)` are desirable.

---

### B. Missing edge cases

1. **Empty database**
   - `dates[0]` and `dates[-1]` will raise `IndexError` if there are no rows.

2. **Rows exist but all values are `NULL`**
   - Example:
     ```python
     hb_vals = [r[1] for r in hb_data if r[1] is not None]
     min(hb_vals)
     ```
   - If `hb_data` is non-empty but all `value_numeric` are `NULL`, `hb_vals` is empty and `min()` raises `ValueError`.

3. **Latest value is `NULL`**
   - The script prints `None` directly.
   - It does not distinguish “latest observation” from “latest non-null observation.”

4. **Missing JSON files**
   - The `glob` result may be empty.
   - The script silently prints zero files, which is acceptable, but the directory itself may not exist.

5. **Malformed JSON**
   - `json.load()` exceptions are silently ignored.
   - This hides data-quality problems.

6. **JSON root object not a dict**
   - The script assumes `d` is a dict:
     ```python
     d.get('comments', [])
     ```
   - If JSON root is a list, this raises `AttributeError`.

7. **`comments` not a list**
   - The script assumes `comments` is iterable as a list of strings.
   - It may be a string, `None`, dict, or other type.

8. **Comment items not strings**
   - The script assumes each comment is a string.
   - If it is a dict, number, or `None`, `.strip()` fails.

9. **Date values can be `None`**
   - The script does not explicitly filter `NULL` dates.
   - Sorting and display can become ambiguous.

10. **Non-numeric stored values**
    - `value_numeric` may contain strings, blanks, or invalid numbers.
    - The original code assumes clean numeric values.

11. **NaN handling**
    - If `value_numeric` contains `NaN`, `min()`/`max()` and formatting may behave unexpectedly.

12. **Hard-coded paths**
   - The script will not run outside the specific Windows path.
   - It is not testable in CI.

13. **Database connection not closed**
   - The connection is never explicitly closed.
   - This can leave resources open, especially in long-running or repeated use.

---

### C. Type safety issues

1. **No type annotations**
   - Rows are treated as positional tuples.
   - There is no structural guarantee of field order.

2. **Magic tuple indexing**
   - `r[0]`, `r[1]`, `r[2]`, `r[3]` are fragile.
   - If query columns change, bugs are easy to introduce.

3. **No data model**
   - There is no explicit `Observation`, `Precursor`, or `Comment` type.

4. **Dynamic `dict.get()` usage on unknown JSON structures**
   - No validation that values are strings, lists, or dicts.

5. **Mixed string/date handling**
   - Dates are treated as raw strings.
   - There is no normalization or robust sorting strategy.

---

# 2. Refactored, Robust, Optimized Version

Below is a complete refactored implementation.

Design goals:

- Safe on empty data.
- Safe on `NULL` values.
- Safe on malformed JSON.
- Uses one query per data domain where possible.
- Uses typed dataclasses.
- Uses `Path` for filesystem access.
- Uses logging instead of silent exception swallowing.
- Is unit-testable.
- Uses Python 3.12+ style type annotations.
- Avoids hard-coded paths in the core logic.
- Provides a CLI entry point.

---

## Refactored Script

```python
"""Clinical longitudinal trajectory analysis.

This module provides a robust, typed, and testable implementation of the
original clinical data trajectory report.

It assumes an SQLite database with a table named ``observations`` containing,
at minimum, the following columns:

    canonical_id TEXT
    display_name TEXT
    date TEXT
    value_numeric REAL
    ref_low REAL
    ref_high REAL
    units TEXT
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Canonical IDs to summarize as numeric trajectories.
PRIMARY_TRAJECTORY_IDS = (
    "haemoglobin",
    "platelets",
    "wbc",
    "neutrophils",
    "ldh",
    "uric_acid",
    "egfr",
    "creatinine",
)

#: Canonical IDs representing immature cells / blood film precursors.
PRECUSOR_CANONICAL_IDS = (
    "blasts",
    "myelocytes",
    "metamyelocytes",
    "promyelocytes",
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Observation:
    """A single numeric observation for a clinical variable."""

    canonical_id: str
    date: str | None
    value: float | None
    ref_low: float | None
    ref_high: float | None
    units: str | None = None


@dataclass(frozen=True, slots=True)
class NumericSummary:
    """Summary statistics for a sequence of observations."""

    non_null_count: int
    min_value: float
    max_value: float
    latest_date: str | None
    latest_value: float | None


@dataclass(frozen=True, slots=True)
class PrecursorSummary:
    """Summary of precursor observations by date."""

    total_observations: int
    dates: list[str]
    latest_date_details: list[tuple[str, list[str]]]


@dataclass(frozen=True, slots=True)
class CommentRecord:
    """A cleaned reviewer comment from a Stage 1 JSON file."""

    source_file: str
    date: str | None
    text: str


# ---------------------------------------------------------------------------
# Safe conversion utilities
# ---------------------------------------------------------------------------
def to_float(value: Any) -> float | None:
    """Convert a value to float safely.

    Returns
    -------
    float | None
        The converted float, or ``None`` if conversion fails.

    Notes
    -----
    NaN is treated as missing.
    """
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(result):
        return None

    return result


def to_clean_text(value: Any) -> str:
    """Convert a value to a single-line cleaned string."""
    if value is None:
        return ""

    if isinstance(value, str):
        text = value
    elif isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, dict):
        # Support common comment object shapes.
        for key in ("text", "comment", "message", "value"):
            if key in value:
                return to_clean_text(value[key])
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)

    return " ".join(text.split())


def date_sort_key(value: str | None) -> tuple[int, str]:
    """Return a stable sort key for date-like strings.

    Missing dates are sorted last. ISO-8601 dates sort naturally because
    their string representation is lexicographically sortable.
    """
    if value is None:
        return (1, "")

    text = str(value).strip()
    if not text:
        return (1, "")

    # Prefer ISO dates when possible.
    try:
        return (0, text[:10])
    except Exception:
        return (0, text)


# ---------------------------------------------------------------------------
# SQLite access
# ---------------------------------------------------------------------------
def connect_db(db_path: Path) -> sqlite3.Connection:
    """Open an SQLite database connection.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.

    Returns
    -------
    sqlite3.Connection
        A new connection with row factory enabled.

    Raises
    ------
    FileNotFoundError
        If the database file does not exist.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def load_timeline_dates(conn: sqlite3.Connection) -> list[str]:
    """Return distinct non-null observation dates in ascending order."""
    rows = conn.execute(
        """
        SELECT DISTINCT date
        FROM observations
        WHERE date IS NOT NULL
        ORDER BY date ASC
        """
    ).fetchall()

    return [str(row["date"]) for row in rows]


def load_observations_for_canonical_ids(
    conn: sqlite3.Connection,
    canonical_ids: Sequence[str],
) -> dict[str, list[Observation]]:
    """Load observations for multiple canonical IDs in one query.

    Parameters
    ----------
    conn:
        SQLite connection.
    canonical_ids:
        Canonical IDs to load.

    Returns
    -------
    dict[str, list[Observation]]
        Mapping from canonical ID to a list of observations sorted by date.
    """
    if not canonical_ids:
        return {}

    placeholders = ",".join("?" for _ in canonical_ids)
    sql = f"""
        SELECT
            canonical_id,
            date,
            value_numeric,
            ref_low,
            ref_high,
            units
        FROM observations
        WHERE canonical_id IN ({placeholders})
        ORDER BY canonical_id ASC, date ASC
    """

    series: dict[str, list[Observation]] = defaultdict(list)

    for row in conn.execute(sql, tuple(canonical_ids)):
        canonical_id = str(row["canonical_id"])
        series[canonical_id].append(
            Observation(
                canonical_id=canonical_id,
                date=str(row["date"]) if row["date"] is not None else None,
                value=to_float(row["value_numeric"]),
                ref_low=to_float(row["ref_low"]),
                ref_high=to_float(row["ref_high"]),
                units=str(row["units"]) if row["units"] is not None else None,
            )
        )

    return dict(series)


def load_precursor_observations(
    conn: sqlite3.Connection,
    canonical_ids: Sequence[str],
) -> list[Observation]:
    """Load precursor observations for the supplied canonical IDs."""
    if not canonical_ids:
        return []

    placeholders = ",".join("?" for _ in canonical_ids)
    sql = f"""
        SELECT
            canonical_id,
            display_name,
            date,
            value_numeric,
            units
        FROM observations
        WHERE canonical_id IN ({placeholders})
          AND value_numeric IS NOT NULL
        ORDER BY date ASC
    """

    observations: list[Observation] = []
    for row in conn.execute(sql, tuple(canonical_ids)):
        value = to_float(row["value_numeric"])
        if value is None:
            continue

        observations.append(
            Observation(
                canonical_id=str(row["canonical_id"]),
                date=str(row["date"]) if row["date"] is not None else None,
                value=value,
                ref_low=None,
                ref_high=None,
                units=str(row["units"]) if row["units"] is not None else None,
            )
        )

    return observations


# ---------------------------------------------------------------------------
# Statistics and milestone selection
# ---------------------------------------------------------------------------
def summarize_observations(observations: Sequence[Observation]) -> NumericSummary | None:
    """Compute basic statistics for a sequence of observations.

    Returns ``None`` if there are no non-null numeric values.
    """
    non_null = [obs for obs in observations if obs.value is not None]
    if not non_null:
        return None

    values = [obs.value for obs in non_null]
    min_value = min(values)
    max_value = max(values)

    # Because observations are loaded ordered by date, the last non-null
    # observation is the latest non-null observation.
    latest = non_null[-1]

    return NumericSummary(
        non_null_count=len(non_null),
        min_value=float(min_value),
        max_value=float(max_value),
        latest_date=latest.date,
        latest_value=float(latest.value) if latest.value is not None else None,
    )


def milestone_indices(
    observations: Sequence[Observation],
    max_points: int = 10,
) -> list[int]:
    """Select milestone indices for display.

    The goal is to show roughly ``max_points`` observations across the
    trajectory while always including the final observation when possible.
    """
    n = len(observations)
    if n == 0:
        return []

    max_points = max(1, int(max_points))

    if n <= max_points:
        return list(range(n))

    step = max(1, n // max_points)
    indices = list(range(0, n, step))

    if indices[-1] != n - 1:
        indices.append(n - 1)

    return indices


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
def format_value(value: float | None, precision: int = 1) -> str:
    """Format a numeric value for console output."""
    if value is None:
        return "n/a"
    return f"{value:.{precision}f}"


def format_ref_range(
    ref_low: float | None,
    ref_high: float | None,
    precision: int = 0,
) -> str:
    """Format a reference range if both bounds are available."""
    if ref_low is None and ref_high is None:
        return ""

    if ref_low is None:
        return f"ref <{format_value(ref_high, precision)}"

    if ref_high is None:
        return f"ref >{format_value(ref_low, precision)}"

    return f"ref {format_value(ref_low, precision)}-{format_value(ref_high, precision)}"


def print_trajectory(
    title: str,
    observations: Sequence[Observation],
    unit: str,
    precision: int = 1,
    max_milestones: int = 10,
) -> None:
    """Print a compact trajectory summary for one clinical variable."""
    print(f"\n--- {title} ---")

    if not observations:
        print("No observations recorded.")
        return

    summary = summarize_observations(observations)

    if summary is None:
        print("No non-null numeric values recorded.")
    else:
        latest_date = summary.latest_date or "unknown"
        print(
            "Range: "
            f"Min {format_value(summary.min_value, precision)} {unit} | "
            f"Max {format_value(summary.max_value, precision)} {unit} | "
            f"Latest non-null ({latest_date}): "
            f"{format_value(summary.latest_value, precision)} {unit}"
        )

    print("Historical milestones:")
    indices = milestone_indices(observations, max_milestones)

    if not indices:
        print("  none")
        return

    for idx in indices:
        obs = observations[idx]
        date_text = obs.date or "unknown"
        ref_text = format_ref_range(obs.ref_low, obs.ref_high)
        value_text = format_value(obs.value, precision)

        line = f"  {date_text}: {value_text} {unit}"
        if ref_text:
            line += f" ({ref_text})"

        print(line)


def print_precursor_summary(summary: PrecursorSummary) -> None:
    """Print a compact precursor summary."""
    print("\n--- LEUKOERYTHROBLASTIC BLOOD FILM / PRECURSORS ---")
    print(f"Total Precursor Observations Recorded: {summary.total


---
### Test 2: Half-Full Context (AIMS ~81k Repo Audit)

#### Prompt Summary
```text
You are a Principal Rust Architect. Below is the full source code and configuration of the AIMS project (45 files):

--- FILE: rust-toolchain.toml ---
[toolchain]
channel = "stable"
components = ["clippy", "rustfmt"]


--- FILE: Cargo.toml ---
[workspace]
resolver = "2"
members = [
    "crates/aims-core",
    "crates/aims-db",
    "crates/aims-domain",
    "crates/aims-api",
]

[workspace.package]...
```

#### Reasoning Trace (`<think>`)
```text
The user is asking for a thorough architecture audit of a Rust workspace project called AIMS. There are three parts:

1. End-to-end data flow — trace the request lifecycle from the API layer through to database migrations/queries
2. Concurrency & resilience audit — deadlocks, async cancellation hazards, unchecked unwrap calls, transaction rollback edge cases
3. Telemetry & health check design — concrete Rust implementation plan including structs and handlers

Let me carefully think through the codebase to produce a high-quality answer. I am a "Principal Rust Architect", so the answer should be deep, specific, and reference exact files/lines.

Let me analyze the codebase thoroughly.

## Repository composition

Workspace crates:
- `aims-core`: newtypes (`TenantId`, `UserId`, `PatientId`, `PractitionerId`, `CentAmount`), `AimsError` (thiserror). sqlx traits implemented for newtypes.
- `aims-db`: `Pool` (= `PgPool`), `create_pool`, `check`, `begin_tenant_tx` (BEGIN + `set_config('app.current_tenant_id', $1, true)`), `patients::list_active` via `query_as!` checked query.
- `aims-domain`: `ops::patients::list_patients` — single transaction: begin tenant tx, list, commit.
- `aims-api`: axum 0.8, maud templates, htmx. `main.rs` (sync setup with eyre, dotenvy, tracing-subscriber, tokio runtime, block_on `async_main`), `config.rs` (env vars), `state.rs` (AppState with Arc), `handlers.rs` (routes: /healthz, /, /patients), `templates.rs`, `error.rs` (ApiError wrapping AimsError, maps to 500).

Migrations: 0001–0008. RLS applied via `apply_tenant_rls`. Roles `aims_app` (RLS subject), `aims_ops` (BYPASSRLS). Deferrable constraint trigger for ledger balance. Immutable tables via REVOKE + triggers.

Tests: SQL stage-1 tests (RLS leak suite, ledger invariants, FK integrity).

## Part 1: End-to-end data flow

Request lifecycle for `GET /` (and `GET /patients`):

1. **Process start**: `main()` — color_eyre install, dotenvy, tracing_subscriber with EnvFilter (default `info,aims_api=debug`), build tokio multi-thread runtime, `block_on(async_main())`.
2. `async_main`: `load_config()` reads `DATABASE_URL`, `AIMS_TENANT_ID` (parsed to `TenantId` newtype via `FromStr` — parse-don't-validate), `AIMS_LISTEN_ADDR` (default `127.0.0.1:3000`).
3. `aims_db::create_pool(&config.database_url)` — `PgPool::connect`. Note: connects as `aims_app` per README. No explicit pool options (max connections default 10, no min idle, no acquire timeout override, no max lifetime). This is a resilience finding: default `PgPoolOptions` — default acquire timeout is 30s, default max connections = num_cpus. Should be explicit.
4. `aims_db::check(&pool)` — `SELECT 1` as liveness check.
5. `AppState { pool, tenant }` wrapped in `Arc`, `router(state)` builds the axum Router with state.
6. `TcpListener::bind`, `axum::serve(listener, app).await`.

Request path for `GET /patients`:
1. axum extracts `State(Arc<AppState>)`.
2. Handler `patients_fragment` calls `aims_domain::ops::patients::list_patients(&state.pool, state.tenant)`.
3. Domain op: `aims_db::begin_tenant_tx(pool, tenant)`:
   - `pool.begin().await?` — acquires a connection from the pool, sends `BEGIN`.
   - `sqlx::query("SELECT set_config('app.current_tenant_id', $1, true)").bind(tenant.as_uuid().to_string()).execute(&mut *tx)` — parameterized SET LOCAL. `true` = is_local → transaction-scoped.
4. `aims_db::patients::list_active(&mut *tx)` — checked query `query_as!` selecting id, given_names, family_name::text AS "family_name!", date_of_birth, medicare_number from patients WHERE active ORDER BY family_name, given_names.
   - RLS: the policy `tenant_isolation` filters with `tenant_id = current_setting('app.current_tenant_id', true)::uuid`. Since we're inside the tx where the GUC is set LOCAL, rows are scoped. If GUC is unset, `current_setting(..., true)` returns NULL → predicate is NULL → zero rows (fail-closed).
5. `tx.commit().await?`.
6. Returns `Vec<Patient>`; the handler renders a maud fragment; axum `Html` response.

Error path: sqlx::Error → `#[from]` to AimsError::Db → `ApiError` → IntoResponse: 500 "internal server error", tracing::error with full details. On any `?` failure, the `Transaction` is dropped → queued rollback runs on next pool use. Note: `Transaction::drop` only queues rollback; it is *not* awaited. This is a real edge case worth discussing: sqlx's `Transaction` on drop issues a ROLLBACK when the connection is returned to the pool — in practice sqlx handles it at drop time by issuing rollback before the connection goes back. Let me recall exactly: in sqlx, `Transaction::drop_impl` sends ROLLBACK on the connection (the connection is not returned to the pool until rollback completes — in the executor, the rollback is issued when the transaction is dropped, and the pool re-acquires the connection after that). Yes — sqlx's `Transaction` drop executes `ROLLBACK` synchronously (via `drop_impl` which runs on the connection's executor) before returning the connection. So the connection is not re-pooled with an open transaction. Good — I should state that accurately: drop triggers a rollback before re-pooling; the only hazard is if the process exits, or if the connection itself is disconnected mid-transaction (in which case the server rolls back on disconnect). Also the GUC set with `SET LOCAL` disappears with the rollback — so no context leak across pooled connections.

RLS context leak hazard: if a transaction fails after set_config, the rollback clears the LOCAL GUC. If a query ran outside `begin_tenant_tx` on a pooled connection, the GUC is unset (fail-closed). Since `SET LOCAL` is transaction-scoped, it cannot leak across pool reuses. Good design. One subtle point: `check(pool)` runs `SELECT 1` on a pooled connection with no tenant context — harmless.

Type flow: `TenantId` binds via `Encode<Postgres>` delegating to Uuid; but in `begin_tenant_tx` it's `.bind(tenant.as_uuid().to_string())` — a `String` bind for a text GUC. Fine.

In `list_active`, `PatientId` (uuid), `String`, `NaiveDate` (chrono), `Option<String>`. The `!` suffix on `family_name!` pins non-null because the `::text` cast makes it an expression that sqlx cannot nullability-derive.

Note: `list_active` takes `impl Executor<'_, Database = Postgres>` — called with `&mut *tx` (deref of Transaction to PgConnection). Fine.

Data-flow trace through migrations: `patients` table (0003): citext family_name, RLS applied via `apply_tenant_rls('patients')`. `tenants` (0001). Roles. Seed data in `dev-seed.sql` with fixed tenant UUID `deadbeef-0000-4000-8000-000000000001`, matching `.env`'s `AIMS_TENANT_ID`.

I can present this as a numbered trace with code references and a diagram.

Other flows to mention:
- `GET /healthz` — static "ok", no DB.
- `GET /` — same domain op + full page.
- Rendering: `Patient` → maud → escaped HTML; medicare_number uses em-dash placeholder.

## Part 2: Concurrency & resilience audit

Let me enumerate specific findings:

### a) Transaction rollback edge cases
- `list_patients`: begin → query → commit. If `list_active` fails, `?` drops tx → sqlx's `Transaction` drop issues ROLLBACK before the connection returns to the pool. GUC is LOCAL so it can't leak. Good.
- The comment in `ctx.rs` says "Transaction queues rollback on drop (which runs when the pooled connection is next used)" — this is actually **imprecise/incorrect** about sqlx's behavior. In sqlx, `Transaction::drop` does run ROLLBACK at drop time (via `drop_impl` which uses the connection's executor to send ROLLBACK; if the connection is dead, it's discarded). Let me double-check: sqlx's `Transaction` has `drop_impl(&mut self)` which calls `self.inner.rollback()`. This happens when the connection is dropped. The connection is returned to the pool after rollback completes. So the comment "which runs when the pooled connection is next used" is wrong; it runs at drop, before re-pooling. This is a documentation-accuracy finding — important because the design docs lean on this property. I should flag it as a doc/comment inaccuracy, not a bug. (In old versions? No — sqlx has been doing rollback-at-drop for a long time.) I'll flag it and recommend fixing the comment; the behavior itself is safe.
- If the process is killed mid-transaction: the Postgres backend rolls back on disconnect. Safe.
- `SET LOCAL` + `BEGIN` are two round-trips; no atomicity issue since rollback clears it.
- Deadlock consideration: the single SELECT is read-only; no locks taken beyond the implicit snapshot. With default READ COMMITTED, no deadlocks. When money-path ops land (multiple writes in one tx), I'll recommend a consistent locking order and `FOR UPDATE` conventions.
- `begin_tenant_tx` borrows `pool` for `'c` and returns a `Transaction<'c>` that's tied to the pool lifetime — standard.

### b) Pool configuration hazards
- `PgPool::connect` uses defaults: `max_connections = available_parallelism()` (so e.g. 8–128+ depending on host), no `min_connections`, default `acquire_timeout = 30s`, `max_lifetime = 30 min` (default Some(30 min)), `idle_timeout = 10 min`. On a large host, default pool = core count can exhaust a small RDS (e.g., db.t4g.small max ~200? Actually t4g.small Postgres max_connections default 100? 2048? no — RDS Postgres t4g.small is 100? Let me not overstate: I'll say "defaults scale with host core count and can overshoot a modest RDS instance"). Recommendations: explicit `PgPoolOptions::new().max_connections(20).min_connections(2).acquire_timeout(...).connect_with(...)`; also validate that the connection user is not BYPASSRLS — a startup probe that runs `SELECT current_setting('is_superuser'), session_user` and asserts it's `aims_app`. This is a key resilience/compliance point: a misconfigured DATABASE_URL pointing at superuser silently disables RLS while tests pass (the README itself warns). A startup assertion would convert this into a startup failure.

### c) Unchecked unwrap/expect calls
- Workspace lints deny `unwrap_used`, `expect_used`, `panic`, `indexing_slicing`, etc. `main.rs` uses `.unwrap_or_else` (fine) and `wrap_err`. Lints are clean.
- `healthz` returns `&'static str` — fine.
- The test module in `money.rs` allows unwraps under `#[cfg(test)]`. Fine.
- One subtle point: `CentAmount` arithmetic (`self.0 + rhs.0`) can overflow in release (wrap) — in healthcare money, silent overflow is a hazard. Consider checked arithmetic (`checked_add`) or `overflow-checks` (debug only; release wraps). Since money is i64 cents, overflow at ~9.2e18 cents = $9.2e16 — practically unreachable, but as a principle, use checked ops in the service layer, or at least document. Worth a line as a "latent, low-severity" item.
- `tracing::info!(tenant = %config.tenant_id, ...)` — Display for TenantId — fine.
- `load_config` — parses env vars with typed errors; good.

### d) Async cancellation hazards
- axum handlers are cancellation-safe here: the only non-idempotent operation is a read tx; if a client disconnects, tokio cancels the future; `Transaction` drop issues ROLLBACK — for a read-only tx, nothing lost. For future money ops, cancellation mid-write is fine (rollback), but *post-commit* side effects (e.g., webhook dispatch, S3 upload) must be structured so they don't run before commit, or made idempotent (design doc's open item).
- `runtime.block_on(async_main())` — if `axum::serve` is interrupted (SIGINT), axum 0.8's `serve` handles graceful shutdown on ctrl_c by default? Actually `axum::serve(listener, app)` installs a default graceful shutdown that waits for SIGINT/SIGTERM and then drains. Yes — `serve` has built-in graceful shutdown on SIGINT/SIGTERM. Good; worth mentioning.
- `Transaction` held across an `.await` in a context where a task can be dropped — fine.
- One hazard: `#[tracing::instrument]` on `list_active` with `skip(conn)` — fine.
- Long-lived `AppState` in `Arc` — no locks, so no `await_holding_lock` risk (the lint is denied anyway).

### e) Concurrency
- `AppState` is immutable after startup → `Arc` shared, no mutex. Good.
- `CentAmount` is Copy. Good.
- Templates are pure functions. Good.
- No `Rc`, no `RefCell`. Good.
- axum 0.8: `State(Arc<AppState>)` — Clone per request; cheap.

### f) Other resilience gaps
- No request timeout on the pool acquire? Pool has acquire_timeout 30s default — OK.
- No `#[tokio::time::timeout]` on slow query — optional.
- Health endpoint `/healthz` is a shallow liveness check; no readiness probe that checks DB (`check` is only at startup). Propose in part 3.
- `check()` at startup is good; but a post-deploy silent connection loss won't be detected until a request. Deep health probe in part 3.
- `TcpListener::bind` before DB? No, DB first — good ordering.
- TLS termination is out of scope (dev only); note for production.
- `.env` trust — fine for dev.
- `list_active`'s ORDER BY family_name (citext) — uses collation; fine.
- Missing: no pagination on patient list — will grow; minor.
- `query_as!` offline mode: `.sqlx` tracked — build fails on drift. Good; note that `begin_tenant_tx` uses runtime (unchecked) query — intentional, documented.
- `set_config` bound as text — GUC `app.current_tenant_id` is compared to `::uuid`; if a malformed UUID string is set, `::uuid` cast inside the policy would raise an error on any tenant-scoped query (not fail-closed, an error). But `TenantId` is a newtype parsed at the boundary, so only valid UUIDs reach it. Edge: `current_setting(..., true)` returns NULL if unset → predicate NULL → zero rows. If set to garbage → runtime error 22P02 on cast. Since only `begin_tenant_tx` sets it, and it binds `TenantId`'s string (valid), safe. Worth a one-line note.
- `begin_tenant_tx` sends `set_config` as a separate statement — fine.
- Potential finding: `begin_tenant_tx`'s doc comment says "Commit with tx.commit() on success" — the domain op does. OK.
- Finding: `list_patients` commits a read-only transaction — unnecessary but harmless; preserves the invariant "all DB access is inside a tenant tx".
- Finding: pool has no `idle_timeout` tuning; fine.
- Finding: `check` uses unchecked `SELECT 1` — fine.
- Finding: if the DB is unreachable at startup, `block_on` fails with eyre report — good, process exits non-zero.
- Finding: no graceful shutdown log; add `tracing::info!("shutting down")`.
- Finding: `color_eyre::install()` before dotenv — order fine.
- Finding: tracing subscriber uses fmt layer only; no JSON option for prod; part 3.

- Deadlock specifics: none in current code. When adding writes: recommend single-tx, fixed table order, `SELECT ... FOR UPDATE` on `appointments`/`invoices` row locks before ledger posting; deferrable constraint trigger `ledger_group_balance` — note: constraint triggers fire at statement end and re-check the whole group — the guard queries `ledger_entries` with `group_id = g`; if two concurrent txs post to the same group_id (must not happen since group_id is a fresh UUID per op), no conflict. If a group is posted across multiple statements with DEFER, the check happens at commit — a commit-time lock: constraint triggers acquire locks? At commit, deferred triggers run; the guard does a SELECT on ledger_entries — under READ COMMITTED, a plain SELECT does not block. OK.
- One subtle: the guard's subquery filters only by `group_id` (not tenant) — fine because group_id is a unique uuid.
- E4 check `(debit > 0) <> (credit > 0)` — enforces one-sidedness.

- Cancellation: axum handler task cancelled on client drop → `Transaction` dropped mid-await → rollback. The `SET LOCAL` context is cleared. Safe. For future: any operation that makes *external* calls (S3,

 Considering the limited time by the user, I have to give the solution based on the thinking directly now.
```

#### Final Output Response

# AIMS Architectural Audit

**Scope:** full read of all 45 files — 4 crates, 8 migrations, 3 Stage-1 SQL suites, discovery/design docs. Verdict up front: the architecture is sound and unusually disciplined (layering, RLS tenancy, checked queries, parse-don't-validate newtypes all cohere). The findings below are not "the design is wrong" — they are (a) one documentation inaccuracy that misstates a load-bearing safety property, (b) pool-hardening gaps that the current code silently defaults, (c) latent hazards that will bite the first *write* operation, and (d) the telemetry/health plan you asked for.

---

## 1. End-to-End Data Flow

### 1.1 Process startup (sync → async handoff)

```
main()                                        [aims-api/src/main.rs]
 ├─ color_eyre::install()                     sync; eyre handler for process-edge errors
 ├─ dotenvy::dotenv().ok()                    real env vars always win
 ├─ tracing_subscriber::fmt()
 │    .with_env_filter(RUST_LOG | "info,aims_api=debug")
 ├─ tokio multi-thread runtime build
 └─ runtime.block_on(async_main())            the only block_on in the codebase
     ├─ config::load_config()
     │    DATABASE_URL (required)             ── must point at aims_app (see §2.4)
     │    AIMS_TENANT_ID → .parse::<TenantId>()  newtype at the process edge
     │    AIMS_LISTEN_ADDR (default 127.0.0.1:3000)
     ├─ aims_db::create_pool(&url)            PgPool::connect — defaults, see §2.2
     ├─ aims_db::check(&pool)                 SELECT 1 (liveness + plan check)
     ├─ Arc::new(AppState { pool, tenant })   immutable from here on
     ├─ router(state)                         /healthz, /, /patients
     └─ TcpListener::bind → axum::serve       serve() installs SIGINT/SIGTERM graceful drain
```

The sync/async split is clean: everything that can fail *before* a runtime exists (config, pool, listener) is `eyre::Report`; everything inside the serve loop is typed `AimsError`. That boundary matches `docs/database-design-principles.md §4` and is one of the things this codebase does better than average.

### 1.2 Request lifecycle: `GET /patients` (the htmx fragment)

`GET /` is identical apart from the template function; `GET /healthz` never touches the DB.

```
Browser (htmx: hx-get="/patients" hx-trigger="load")
 │
 ▼
axum::extract::State(Arc<AppState>)           handlers.rs::patients_fragment
 │  (clone of Arc — no lock; AppState is immutable)
 ▼
aims_domain::ops::patients::list_patients(&pool, tenant)      [aims-domain]
 │
 │  ┌─────────────────────────────────────────────────────────────┐
 │  │ exactly one sqlx::Transaction (design principle §4)         │
 │  └─────────────────────────────────────────────────────────────┘
 ▼
aims_db::begin_tenant_tx(pool, tenant)                       [aims-db/src/ctx.rs]
 ├─ pool.begin()                         BEGIN; connection pinned from pool
 └─ SELECT set_config('app.current_tenant_id', $1, true)
 │     $1 = tenant.as_uuid().to_string() (runtime/unchecked query — deliberate,
 │     it is plumbing, not a data contract; the contract is the RLS policy)
 │
 │  Effect: GUC is SET LOCAL → dies with the transaction (commit or rollback).
 ▼
aims_db::patients::list_active(&mut *tx)                     [aims-db/src/entities/patients.rs]
 ├─ query_as! (COMPILE-TIME CHECKED against .sqlx/ offline data):
 │     SELECT id, given_names, family_name::text AS "family_name!",
 │            date_of_birth, medicare_number
 │     FROM patients WHERE active ORDER BY family_name, given_names
 │
 │  RLS in the kernel: policy `tenant_isolation` on patients (0003 → 0001 helper)
 │     USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
 │  • context set  → only this tenant's rows
 │  • context unset→ current_setting(..., true) = NULL → predicate NULL → 0 rows
 │                    (fail-closed, not an error — the property the whole tenancy
 │                    guarantee rests on; proven by db/tests/01_rls_leak.sql)
 ▼
tx.commit()                            read-only commit; connection returns to pool
 ▼
Vec<Patient>  (PatientId, String, String, NaiveDate, Option<String>)
 ▼
templates::patients_fragment(&patients)  maud html! — text interpolation escaped;
 │                                       medicare NULL → "—"
 ▼
axum response::Html<String>            → htmx innerHTML swap of #patients
```

### 1.3 Where each guarantee lives (trace back to migration)

| Guarantee | Enforced in | Evidence |
|---|---|---|
| Only `aims_app` can run the app | 0001 role (`NOSUPERUSER`, no `BYPASSRLS`) + README convention | `db/local/dev-seed.sql`, `.env` |
| Row tenancy | `apply_tenant_rls('patients')` in 0003; policy in 0001 | `01_rls_leak.sql` (27 tables, anti-vacuousness check, cross-tenant INSERT/UPDATE probes) |
| No DTO tier | `Patient` is `FromRow` *and* the domain shape; newtypes implement `Encode/Decode/Type<Postgres>` in `aims-core/src/ids.rs` so they're transparent in `query_as!` | README §Layout |
| Type drift = build error | `query_as!` + tracked `.sqlx/` offline mode | README §Dev loop step 4 |
| `family_name` nullability | `::text` cast makes it an expression; the `!` suffix pins NOT NULL in Rust because sqlx can't infer through a cast | comment in `patients.rs` |

### 1.4 Failure path (today)

```
any `?` in [pool.begin | set_config | fetch_all | commit]
 → sqlx::Error  --#[from]-->  AimsError::Db  --#[from]-->  ApiError
 → IntoResponse: 500 "internal server error"
   (deliberately no domain detail in the body; full error via tracing::error)
 + Transaction drop → ROLLBACK (see §2.1 for the precise semantics)
```

Process-level failures (bad `AIMS_TENANT_ID`, DB unreachable at boot) never become HTTP responses — they are `eyre::Report`s in `main`, which is the correct layering.

---

## 2. Concurrency & Resilience Audit

### 2.1 Transaction rollback edge cases

**Finding R1 — the comment in `ctx.rs` misstates a load-bearing property (doc bug, not code bug).**

> "On any error, `?` propagates and the transaction is dropped; `Transaction` queues a rollback on drop (it will run **when the pooled connection is next used**)"

That is not what sqlx does. `Transaction::drop` issues `ROLLBACK` **at drop time, before the connection is returned to the pool** (via `drop_impl` on the connection's executor); a dead connection is simply discarded. The safety property you're after is therefore *stronger* than documented — a pooled connection can never be handed out with a live transaction or a live `SET LOCAL` GUC — but the design doc and the `begin_tenant_tx` doc comment should say so, because `docs/database-design-principles.md §2` ("context is committed or rolled back together with the work it guards") is the thing the RLS suite is meant to prove. **Action:** correct the comment; keep the behavior.

Concrete edge cases, all currently safe:

- **Error after `set_config`:** `?` drops `tx` → rollback → LOCAL GUC vanishes. No context can leak to a future pooled connection. ✔
- **Client disconnect mid-handler:** axum cancels the future → `Transaction` dropped → rollback. Today read-only, so nothing is lost. **This is the one property that must be re-verified for the first write op** (§2.3).
- **Process kill mid-tx:** Postgres rolls back on backend disconnect. ✔
- **Garbage GUC value:** `current_setting(...)::uuid` would raise `22P02` (fail-*loud*, not fail-closed) — unreachable in practice because only `begin_tenant_tx` writes the GUC and it binds a `TenantId` that already parsed at the process edge. Noted for completeness.
- **`list_patients` commits a read-only tx.** Harmless and I'd keep it: it preserves the invariant "all DB access happens inside a `begin_tenant_tx` transaction," which is what makes a future stray query fail-closed rather than accidentally cross-tenant.

**Deadlocks:** none possible today — a single read-only `SELECT` under READ COMMITTED takes no blocking locks. When money-path writes land, the hazards are: (a) two ops touching the same `invoices`/`appointments` rows in opposite table order; (b) a `SELECT … FOR UPDATE` followed by a long external call. Prescribe now, before the first write op: **fixed lock ordering** (parent row first: `appointments` → `invoices` → ledger), **no external I/O between lock acquisition and commit** (S3/Tyro calls go *after* commit or become idempotent-and-retried), and the deferrable `ledger_group_balance` constraint trigger is safe at commit (its guard is a plain `SELECT`; `group_id` is a fresh UUID per op so no two txs contend on the same group).

### 2.2 Pool configuration — the biggest concrete gap

`create_pool` is `PgPool::connect(url)`, i.e. pure defaults:

| Setting | Default | Risk |
|---|---|---|
| `max_connections` | **host core count** | A 32-core dev box opening 32 conns against a modest RDS; a k8s pod on a large node worse. Overshoot → `too many connections` under load, exactly when you need it. |
| `min_connections` | 0 | Cold-pool connection churn on first request after idle. |
| `acquire_timeout` | 30 s | A request can block 30 s before failing; fine, but it should be a *decision*, and it should be surfaced by the deep health probe (§3). |
| `max_lifetime` | 30 min | Fine for RDS; keep explicit so it can be tuned per platform. |

**Action** — make it a `PgPoolOptions` decision and pin the role:

```rust
pub async fn create_pool(database_url: &str) -> Result<Pool, sqlx::Error> {
    let pool = PgPoolOptions::new()
        .max_connections(20)          // RDS db.t4g.* friendly; tune per instance
        .min_connections(2)           // absorb cold start
        .acquire_timeout(Duration::from_secs(5))
        .max_lifetime(Duration::from_secs(1800))
        .connect(database_url)?;
    verify_role(&pool).await?;        // see 2.4
    Ok(pool)
}
```

### 2.3 Async cancellation hazards

- **None active today** — the only in-flight state is a read-only tx, and cancellation rolls it back safely.
- **The rule to encode for the money path** (write it into `aims-domain`'s module docs so the first invoice op is built right): a domain op's future must be **cancellation-safe**, which for "one op = one tx" means: all external side effects (Tyro, S3, Xero) happen **after** `tx.commit()` returns, and any of them are idempotent (the design doc's open item — htmx double-submits make this *more* relevant, per principles §4). If an effect must precede commit, it needs a durable outbox row written *inside* the tx.
- `await_holding_lock` is lint-denied and there are no locks in `AppState` — no hazard.
- `axum::serve` already installs SIGINT/SIGTERM graceful drain; add a `tracing::info!` after it returns so shutdown is visible in logs.

### 2.4 Unchecked `unwrap` / panic surface — and the RLS-voiding misconfiguration

- **Lint surface is clean.** `unwrap_used`/`expect_used`/`panic`/`indexing_slicing` are denied workspace-wide; the only `.unwrap_*` in production code is `unwrap_or_else` in `config.rs`/`main.rs` (allowed, infallible). Test modules correctly self-allow. ✔
- **Latent:** `CentAmount` uses raw `+`/`-`/`-self.0` (`money.rs`). Release-mode `i64` overflow wraps. At cents scale the threshold is ~$9×10¹⁶, so this is theoretical — but the codebase's whole ethos is "money can't do anything silent." Recommend `checked_add/checked_sub` constructors returning `Result` (or at minimum a documented decision), consistent with "zero runtime surprises."
- **The real compliance hazard is a configuration one, not a code one:** connect as superuser or `aims_ops` and **every RLS policy silently stops applying while every test passes** — the README warns about this in prose. Prose is not a control. Add a startup assertion that fails the process:

```rust
/// Fail-closed tenancy: if we are not the RLS-subject role, RLS does not
/// apply to us and the whole tenancy guarantee is void. Refuse to boot.
async fn verify_role(pool: &Pool) -> Result<(), sqlx::Error> {
    let row: (String, bool) = sqlx::query_as!(
        (String, bool),
        r#"SELECT current_user, current_setting('is_superuser', true) = 'on'
           UNION ALL SELECT current_user, false"#  // or two separate selects
    ).fetch_one(pool).await?;
    if row.1 || row.0 != "aims_app" {
        return Err(sqlx::Error::Configuration(
            format!("refusing to run as role '{row.0}' (superuser={row.1}); \
                     connect as the RLS-subject role aims_app").into(),
        ));
    }
    Ok(())
}
```

(Or, simpler and unambiguously checked: run a probe *as the app* against a seeded cross-tenant row and assert zero rows — same shape as `01_rls_leak.sql`, once, at boot. That converts a silent guarantee-loss into a boot failure.)

### 2.5 Other resilience notes

- `check()` at startup is good; post-deploy, a silent connection loss isn't detected until a request — the deep probe in §3 fixes this continuously.
- No pagination on `list_active` — fine at practice scale, add `LIMIT/OFFSET` (or keyset) before it's a problem; the `ORDER BY family_name, given_names` gives you a stable keyset for free if you add `id` as tiebreaker.
- `tracing::instrument` coverage is consistent (handlers, domain op, entity query); good base for §3.
- TLS/ingress, cookie sessions, and CSRF are all V1-deferred per the docs — correct sequencing, but note the deep probe should be routable behind any future auth middleware (keep it unauthenticated like `/healthz` is today).

---

## 3. Telemetry & Healthcheck Design (concrete plan)

Design goals: (1) one structured pipeline, `tracing` as the single source; metrics derived from events, not a second instrumentation API; (2) health checks with three distinct semantics — liveness (process), readiness (dependencies), depth (DB + tenancy invariant); (3) zero new unsafe surface, lint-clean, no locks.

### 3.1 Crate dependency shape

```
aims-core   + tracing-subscriber (env-filter, json)   [telemetry init lives here? no — see 3.3]
aims-api    + metrics, metrics-exporter-prometheus, tracing-opentelemetry (optional)
aims-db     + metrics (pool/tx events)
aims-domain + metrics (op events) — or rely on tracing spans + a small macro
```

Keep the `tracing` dependency you already have in `aims-db`/`aims-domain`; add `metrics` + `metrics-exporter-prometheus` **only where events are emitted** (`aims-db`, `aims-domain`) and the exporter **only in `aims-api`** (process edge, consistent with the eyre rule).

### 3.2 Structured tracing

**`aims-api/src/telemetry.rs`** (new module, called from `main` before the runtime — subscriber init is sync):

```rust
pub fn init_tracing() {
    use tracing_subscriber::{fmt, prelude::*, EnvFilter};

    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,aims_api=debug,sqlx=warn"));

    let use_json = std::env::var("AIMS_LOG_JSON").is_ok_and(|v| v == "1");

    let fmt_layer = if use_json {
        // prod: one JSON line per event; fields carry tenant, entity, timing
        Box::new(fmt().json().with_target(true).without_ansi()) as Box<dyn fmt::FormatLayer<...>>
    } else {
        Box::new(fmt()) as _
    };

    tracing_subscriber::registry()
        .with(filter)
        .with(fmt_layer)
        .init();
}
```

**Span/field conventions


---
