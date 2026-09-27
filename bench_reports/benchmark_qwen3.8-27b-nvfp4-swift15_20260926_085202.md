# NInfer Benchmark & Quality Report

- **Model ID:** `qwen3.8-27b-nvfp4-swift15`
- **Date & Time:** 2026-09-26 08:54:10
- **Temperature:** `1.0`
- **Thinking Budget:** `2048` | **Max Tokens:** `8192`
- **Overall Quality Status:** **`PASS (Verified by Agent)`**

## 1. Performance Scorecard

| Test | Prompt Tokens | Thinking Tokens | Out Tokens | TTFT (s) | Total Time (s) | Decode (tok/s) | MTP Accept | Quality Status |
|---|---|---|---|---|---|---|---|---|
| Test 1: Empty Context (Dev Short Refactor) | 1,879 | 4,096 | 8,192 | 0.39 | 46.10 | 179.2 | 61.2% | **`PASS`** |
| Test 2: Half-Full Context (AIMS ~81k Repo Audit) | 81,441 | 4,096 | 8,192 | 14.88 | 75.48 | 135.3 | 47.8% | **`PASS`** |

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
We need answer user's request. Need review script, identify bottlenecks, edge cases, type safety; provide fully refactored robust vectorized/optimized version with Python 3.12+ type annotations, docstrings, error handling, unit test examples. Need likely include code. Need think thoroughly.

User asks in English. Need final answer in English. Need produce detailed analysis and refactored code. Need consider clinical data processing script. It uses sqlite3, json, collections unused. It connects to fixed path. It executes queries. Potential bottlenecks: repeated DB queries for 8 canonical ids; per-row milestone loops; list comprehensions for min/max; building [hb_data[i] for i ...] each time? For last check creates list of selected rows? Actually `if hb_data[-1] not in [hb_data[i] for i in range(0, len(hb_data), step)]:` builds list of tuples. Not huge but can optimize. For precursor dates, for each date in last 10 scans all precursors to filter O(n*10). Could group by date with defaultdict. JSON loading all files sequentially, no parallelism; exception pass hides errors; no validation; encoding; large files; date parsing; sorting. No type hints. No handling empty dates; `dates[0]` if no rows raises IndexError. `min(hb_vals)` if all None raises. `hb_data[-1][1]` can be None and prints None; formatting for min uses float. `r[1]` may be TEXT/NaN? sqlite numeric could be None, not NaN, but if imported with 'NaN' as text? Type safety. `value_numeric` may be string? Need cast. `ref_low/ref_high` may be None. Unit assumptions. Duplicate dates? observations may have multiple rows same date per canonical? Query returns ordered by date, no dedup; if multiple same date, latest ambiguous. Need aggregate? Need handle canonical id existence. Missing tables? DB connection not context manager, no close. Hardcoded paths. No logging. JSON path hardcoded, glob may be huge; no error handling for invalid JSON, permission; broad except. `d.get('comments', [])` may not be list; comments may not strings. `d.get('_source_file')` missing. `seen_snippets` arbitrary 30 char. Performance: use SQL aggregate for min max latest; use index on canonical_id/date. Use pandas? User says vectorized/optimized. Could use sqlite3 + pandas read_sql if available, but to keep stdlib? Python 3.12+ type annotations. Could provide two options? Fully refactored robust vectorized/optimized version. Could use `pandas` for vectorized operations. But if no dependencies? Clinical data processing; likely can use pandas. Need decide. They ask vectorized/optimized. Using pandas is natural. But robust code can be dependency-light with sqlite3 and dataclasses. Vectorized? Maybe use NumPy/Pandas. We can provide refactored module using `pandas` for time series, `pathlib`, `logging`, `json`, `concurrent.futures` for JSON parsing. Type annotations Python 3.12+. Include unit tests with pytest. Need handle empty inputs, null/NaN, division by zero? There is no division except step //; max prevents zero. But if data empty, avoid. Need mention no division by zero in original due to max, but edge empty. Also `len(hb_data)//10` okay. But if all values None min max error. Need handle NaN if numeric column includes float('nan')? SQLite doesn't store NaN normally, but pandas may. Need use `pd.notna`, `dropna`.

Need identify performance bottlenecks:
- Multiple separate queries; can fetch all needed canonical ids in one query and pivot in pandas.
- No DB indexes; full table scans if no index on canonical_id, date.
- Python loops over rows to compute min/max/latest; use SQL aggregates or pandas.
- Milestone sampling in Python and duplicate last check; can use pandas `iloc` and boolean masks.
- Precursor grouping O(n*dates) with list filter; use groupby.
- JSON loading serial; can use ThreadPoolExecutor; validate schema; use `json.load` with parse_float? Maybe.
- Broad exceptions; no logging.
- Unused import collections.
- Hardcoded paths; no context management; connection remains open.
- Print output not configurable.
- `dates` distinct all observations, not just key lineages; if huge, one query.
- Type safety: rows are tuple[Any], no type; values can be None/str/Decimal; formatting fails if None; units mismatch; canonical ids magic strings.
- Edge cases: empty DB/table; no dates; all values null; missing JSON files; invalid JSON; comments not list/string; missing metadata; date strings inconsistent; duplicate observations; out-of-order dates; negative values? Clinical validity? ref bounds null.
- Security: fixed path; SQL parameterized okay. File paths from JSON? no.

Refactored version:
Could create a package module `clinical_trajectory.py`. Use dataclasses:
```
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
import sqlite3
import json
import logging
from collections.abc import Sequence as AbcSequence?
```
Python 3.12 type annotations: use `X | None`.

Use pandas? Need include optional dependency. Could write refactored with pandas for vectorized. If no pandas, fallback? The prompt says vectorized/optimized; likely okay to use pandas. But robust code with type annotations. Need unit tests examples. We can include code that uses pandas. Need ensure code runs if pandas installed. Could also include a lightweight fallback? That may be too long. Better provide a refactored module using `pandas` and `sqlite3`, with type hints.

Design:
- Constants: `KEY_CANONICAL_IDS: tuple[str,...]`, `PRECURSOR_CANONICAL_IDS: tuple[str,...]`, `UNITS_BY_CANONICAL: dict[str,str]`.
- `@dataclass(frozen=True) class TrajectorySummary`: canonical_id, unit, count, non_null_count, min, max, latest_date, latest_value, milestones: list[Milestone]. `Milestone` date, value, ref_low, ref_high.
- `@dataclass(frozen=True) class FilmComment`: source_file, collected_date, comment.
- `@dataclass(frozen=True) class AnalysisResult`: n_dates, span_start, span_end, summaries, precursor_dates, precursor_rows, comments.

Functions:
`connect_db(db_path: Path) -> sqlite3.Connection` with context? Use `sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES?)`? Could enable `row_factory = sqlite3.Row`. Use `with sqlite3.connect(...) as conn:`? Note `with conn` commits/rollback but doesn't close. Better context manager `contextlib.closing`.
`load_observation_series(conn, canonical_ids) -> pd.DataFrame` with SQL:
```
placeholders = ",".join("?" for _ in canonical_ids)
sql = f"SELECT date, canonical_id, value_numeric, ref_low, ref_high, units FROM observations WHERE canonical_id IN ({placeholders}) ORDER BY date"
df = pd.read_sql_query(sql, conn, params=canonical_ids, parse_dates={"date": {"format": "%Y-%m-%d"}})
```
But dates may not ISO. Use `parse_dates=False`, then `pd.to_datetime(df['date'], errors='coerce')`; keep original date_str. Need handle empty df.
`sanitize_numeric(df, col)` use `pd.to_numeric(df[col], errors='coerce')`.
`summarize_series(df, canonical_id, unit) -> TrajectorySummary`: if empty return summary with zeros. `series = df[df.canonical_id==canon]`. Sort by date. `numeric = series.value_numeric.dropna()`. latest row: if series not empty, latest = series.iloc[-1]; if value NaN, latest_value None. milestones: choose step = max(1, len(series)//max_milestones); indices = range(0, len, step); ensure last included; use `series.iloc[indices]`. Need avoid duplicates. For values None, print `np.nan`? Summary fields `float | None`.
`load_precursors(conn) -> pd.DataFrame` one query. Group by date: `precursor_pivot = precursors.pivot_table(index='date', columns='display_name', values='value_numeric', aggfunc='first')`? But if multiple same date/cell, maybe sum/mean? Use `last`? For display, can use `groupby(['date','display_name'])['value_numeric'].last().unstack()`. Then last N dates. Need handle NaN.
`load_film_comments(json_dir: Path, max_workers: int=4, log: logger) -> list[FilmComment]`: Use `json_dir.glob('*.json')`; if no files return []. Use `ThreadPoolExecutor` because IO. `_parse_comment_file(path) -> list[FilmComment]`: open with encoding, `json.load`; validate `comments = data.get('comments')`; if not list, if str convert? Could be robust: if isinstance(comments, str): [comments]; elif list: [c for c in comments if isinstance(c,str)]; else []. Metadata date: `meta = data.get('metadata')`; if not dict, {}; date = meta.get('collected_date') or meta.get('requested_date') or data.get('_source_file')`. Need date may be non-str; convert to str if not None. Source file = data.get('_source_file') or path.stem. Return list. Use `try/except (OSError, json.JSONDecodeError, TypeError, ValueError)`. Log warnings. Avoid broad except. Use `with path.open(...)`; `path.read_text`? Use `json.loads`.
`run_analysis(db_path, json_dir, max_milestones=10, comment_sample_limit=50, max_workers=4) -> AnalysisResult`: Connect, load data. Need handle table missing? Use try except sqlite3.OperationalError. If no observations, return empty result.
`format_report(result) -> str`: build string. Need handle None values. Use helper `fmt_num(x, nd)`. If None -> "NA". If NaN -> "NA". Use `float`. For milestones. For precursor dates: last 10. For comments: unique snippets? Could preserve sample. Need not print directly; return string.

Need include unit tests examples:
- Test empty observations returns empty summary, no exception.
- Test all null values returns non_null_count 0, min/max None.
- Test summary min/max/latest and milestones includes last.
- Test precursor grouping.
- Test comment parsing valid/invalid.
- Test `fmt_num` handles None/NaN.
Maybe use `tmp_path` to create sqlite DB and JSON files.
Need code for tests. Could include `pytest` examples.

Need ensure refactored code type annotations. Let's draft code carefully.

Potential issue: `pd.read_sql_query` requires pandas. Type stub? okay.

Let's design code in detail.

```
from __future__ import annotations

import json
import logging
import math
import sqlite3
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

CANONICAL_SERIES: dict[str, str] = {
  "haemoglobin": "g/L",
  "platelets": "x10^9/L",
  "wbc": "x10^9/L",
  "neutrophils": "x10^9/L",
  "ldh": "U/L",
  "uric_acid": "umol/L",
  "egfr": "mL/min",
  "creatinine": "umol/L",
}
PRECURSOR_IDS: tuple[str, ...] = ("blasts", "myelocytes", "metamyelocytes", "promyelocytes")

@dataclass(frozen=True)
class Milestone:
    date: str
    value: float | None
    ref_low: float | None
    ref_high: float | None

@dataclass(frozen=True)
class TrajectorySummary:
    canonical_id: str
    unit: str
    observation_count: int
    non_null_count: int
    min_value: float | None
    max_value: float | None
    latest_date: str | None
    latest_value: float | None
    milestones: list[Milestone] = field(default_factory=list)

@dataclass(frozen=True)
class PrecursorEvent:
    date: str
    cells: dict[str, float]

@dataclass(frozen=True)
class FilmComment:
    source_file: str
    collected_date: str | None
    comment: str

@dataclass(frozen=True)
class AnalysisResult:
    unique_dates: int
    date_min: str | None
    date_max: str | None
    summaries: dict[str, TrajectorySummary]
    precursor_events: list[PrecursorEvent]
    comments: list[FilmComment]
```

Need `milestones` in frozen dataclass with mutable list default okay? It's mutable but frozen prevents reassignment; okay. Could use tuple[Milestone,...] to be immutable. Better:
`milestones: tuple[Milestone, ...] = ()`.

`PrecursorEvent.cells: Mapping[str, float]`? Use tuple? For immutable: `cells: tuple[tuple[str, float], ...]`? Simpler dict not frozen but dataclass frozen doesn't prevent mutation. Use `Mapping[str, float]`.

```
@dataclass(frozen=True)
class PrecursorEvent:
    date: str
    cells: Mapping[str, float]
```
Need import Mapping from collections.abc.

Helper:
```
def _clean_date(value: object) -> str | None:
    if value is None: return None
    if isinstance(value, (pd.Timestamp, datetime)): return value.strftime('%Y-%m-%d')? Need import datetime.
    s=str(value).strip()
    return s or None
```
Need import datetime.

`_to_float(value: object) -> float | None`:
```
if value is None: return None
if isinstance(value, (int, float, np.integer, np.floating)): 
   f=float(value)
   return None if math.isnan(f) else f
try: f=float(value)
except (TypeError, ValueError): return None
return None if math.isnan(f) else f
```
Need np? If no value? We use pandas so np available.

`_fmt(value: float | None, nd: int = 1) -> str`:
```
if value is None: return "NA"
if isinstance(value, float) and math.isnan(value): return "NA"
return f"{value:.{nd}f}"
```
For integer-like? okay.

Database:
```
def open_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists(): raise FileNotFoundError(...)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```
Maybe use `sqlite3.connect(db_path, check_same_thread=True)`.

`load_observation_timeline(conn) -> tuple[int, str|None, str|None]`:
```
try:
    row = conn.execute("SELECT COUNT(DISTINCT date), MIN(date), MAX(date) FROM observations").fetchone()
except sqlite3.OperationalError as exc: raise ValueError("observations table missing") from exc
return int(row[0]), _clean_date(row[1]), _clean_date(row[2])
```
If no rows, min max None.

`load_observation_frame(conn, canonical_ids) -> pd.DataFrame`:
```
if not canonical_ids: return empty df
placeholders = ",".join("?" * len(canonical_ids))
sql = f"""
SELECT date, canonical_id, value_numeric, ref_low, ref_high, units
FROM observations
WHERE canonical_id IN ({placeholders})
ORDER BY date ASC
"""
df = pd.read_sql_query(sql, conn, params=list(canonical_ids))
if df.empty:
    return pd.DataFrame(columns=[...])
df['date'] = pd.to_datetime(df['date'], errors='coerce')
for col in ['value_numeric','ref_low','ref_high']:
   df[col] = pd.to_numeric(df[col], errors='coerce')
return df
```
Need if date parsing all NaT? Keep.

But `pd.read_sql_query` with sqlite3 connection works. If pandas not installed? We assume.

`summarize_series(df: pd.DataFrame, canonical_id: str, unit: str, max_milestones: int = 10) -> TrajectorySummary`:
```
sub = df[df['canonical_id'] == canonical_id].sort_values('date', kind='stable')
obs_count = len(sub)
if obs_count == 0: return TrajectorySummary(...)
numeric = sub['value_numeric'].dropna()
min_value = float(numeric.min()) if not numeric.empty else None
...
latest = sub.iloc[-1]
latest_value = _to_float(latest['value_numeric'])
latest_date = _clean_date(latest['date'])
# milestone indices
if max_milestones <= 0: milestone_indices = [0, obs_count-1]?
else:
   step = max(1, obs_count // max_milestones)
   indices = list(range(0, obs_count, step))
   if indices[-1] != obs_count - 1: indices.append(obs_count - 1)
# remove duplicates preserving order
   seen=set(); unique_indices=[]...
milestones=[]
for idx in unique_indices:
   row=sub.iloc[idx]
   milestones.append(Milestone(date=_clean_date(row['date']) or '', value=_to_float(row['value_numeric']), ref_low=_to_float(row['ref_low']), ref_high=_to_float(row['ref_high'])))
return ...
```
Need `max_milestones` int positive. If `max_milestones=1`, step = max(1, n//1)=n; range(0,n,n) gives [0]; append last if n>1. Good. If n=1, indices [0], last same no append.

Potential issue: `sub.iloc[-1]` date may be NaT if unparseable; `_clean_date` returns None; in Milestone date expects str; use `or 'unknown'`? Better Milestone.date: str.

 Considering the limited time by the user, I have to give the solution based on the thinking directly now.
```

#### Final Output Response

## 1) Review of the original script

### Performance bottlenecks

1. **Repeated single-entity SQL queries**
   - The script executes a separate query for each canonical ID:
     - `haemoglobin`
     - `platelets`
     - `wbc`
     - `neutrophils`
     - `ldh`
     - `uric_acid`
     - `egfr`
     - `creatinine`
   - This causes multiple table scans if there is no useful index on `observations(canonical_id, date)`.

2. **No use of SQL aggregation**
   - Minimum, maximum, and latest values are computed in Python after fetching full series.
   - For large longitudinal tables, this transfers more data than necessary.

3. **Python loops for milestones**
   - Milestone selection is done with Python slicing/index loops.
   - The “include final row if not already included” check builds an intermediate list:
     ```python
     if hb_data[-1] not in [hb_data[i] for i in range(0, len(hb_data), step)]:
     ```
   - This is functionally okay for small data, but unnecessary and less scalable.

4. **Precursor date grouping is inefficient**
   - This block rescans the full precursor list for each displayed date:
     ```python
     for d in dates_with_precursors[-10:]:
         cells = [f"{r[1]}={r[2]}" for r in precursors if r[0] == d]
     ```
   - Complexity is roughly `O(N * displayed_dates)`.
   - A `GROUP BY`, `defaultdict`, or pandas `groupby` would be more efficient.

5. **Sequential JSON file parsing**
   - Stage 1 JSON files are parsed one at a time.
   - For many files, this can be slow.
   - File I/O can be parallelized with a thread pool because JSON parsing and file reads are I/O-bound.

6. **No database indexes considered**
   - The script assumes the table is already efficient.
   - For production use, indexes such as:
     ```sql
     CREATE INDEX IF NOT EXISTS idx_observations_canonical_date
     ON observations(canonical_id, date);
     ```
     would substantially improve query performance.

---

### Missing edge cases

1. **Empty database or empty `observations` table**
   - This line will raise `IndexError`:
     ```python
     print(f"Time Span: {dates[0]} to {dates[-1]} ({len(dates)} timepoints)\n")
     ```
   - If `dates` is empty, `dates[0]` does not exist.

2. **All numeric values are `NULL`**
   - Example:
     ```python
     hb_vals = [r[1] for r in hb_data if r[1] is not None]
     print(f"Hb Range: Min {min(hb_vals):.1f} g/L ...")
     ```
   - If `hb_vals` is empty, `min(hb_vals)` raises `ValueError`.

3. **Latest observation has `NULL` value**
   - This prints `None`:
     ```python
     Latest ({hb_data[-1][0]}): {hb_data[-1][1]} g/L
     ```
   - That is not a clean clinical report.

4. **Reference ranges may be `NULL`**
   - The script prints:
     ```python
     ref {rl}-{rh}
     ```
   - If `rl` or `rh` is `None`, output becomes `ref None-None`.

5. **Numeric column may contain non-numeric text**
   - SQLite is dynamically typed.
   - `value_numeric` may contain:
     - `None`
     - integers
     - floats
     - numeric strings
     - malformed strings
     - empty strings
   - The original script assumes values are directly printable and numeric.

6. **Duplicate observations on the same date**
   - The query returns all rows for a canonical ID ordered by date.
   - If there are multiple observations on the same date, “latest” is ambiguous.
   - The refactored version should define a deterministic rule, e.g. last row by rowid, or aggregate by date.

7. **Missing JSON directory**
   - The script does not check whether:
     ```python
     c:\tmp\bloods\output\stage1_json
     ```
     exists.
   - If missing, `glob.glob()` returns an empty list, which is okay, but a clearer warning is preferable.

8. **Invalid JSON files**
   - The script silently ignores all exceptions:
     ```python
     except Exception:
         pass
     ```
   - This hides:
     - permission errors
     - corrupt JSON
     - unexpected schemas
     - disk errors
   - Production code should log warnings or errors.

9. **`comments` may not be a list**
   - The script assumes:
     ```python
     comments = d.get('comments', [])
     ```
     is iterable as a list of strings.
   - It may be:
     - `None`
     - a single string
     - a dict
     - a list containing non-strings

10. **Metadata date may be missing or non-string**
    - The script uses:
      ```python
      dt = meta.get('collected_date') or meta.get('requested_date') or d.get('_source_file')
      ```
    - If the value is not a string, printing may produce unexpected output.

11. **Date format assumptions**
    - The script assumes `date` values are comparable as strings.
    - If dates are stored as `YYYY-MM-DD`, that works.
    - If they are stored as `DD/MM/YYYY`, `YYYY-MM-DD HH:MM:SS`, or mixed formats, sorting may be incorrect.

12. **Hard-coded file paths**
    - The database and JSON directory are hard-coded.
    - This makes the script difficult to test, reuse, or deploy.

13. **Database connection is never closed**
    - The script creates `conn` and `cur` but never closes the connection.
    - In long-running processes, this can leak resources.

---

### Type safety issues

1. **No type annotations**
   - The original code has no Python 3.12-style type hints.
   - This makes it harder to reason about data shapes.

2. **SQLite rows are untyped tuples**
   - Example:
     ```python
     d, val, rl, rh = hb_data[i]
     ```
   - There is no guarantee that:
     - `d` is a string
     - `val` is a number
     - `rl` is a number
     - `rh` is a number

3. **JSON values are unvalidated**
   - `d.get('comments', [])` can return any JSON type.
   - The code treats it as a list of strings without validation.

4. **Numeric formatting assumes floats**
   - This can fail if the value is `None`:
     ```python
     {min(hb_vals):.1f}
     ```
   - It can also produce misleading output if the value is a numeric string.

5. **Units are assumed, not validated**
   - The script hard-codes units in print statements.
   - If the database contains different units, the report may be clinically misleading.

6. **Canonical IDs are magic strings**
   - The script depends on exact strings such as:
     ```python
     "haemoglobin"
     "platelets"
     "wbc"
     ```
   - These should be centralized constants.

---

## 2) Refactored, robust, vectorized/optimized version

Below is a refactored version using:

- Python 3.12+ type annotations
- `dataclasses`
- `pathlib`
- `logging`
- `sqlite3`
- `pandas`
- `numpy`
- thread-based parallel JSON parsing
- deterministic null/NaN handling
- empty-input handling
- unit-test examples using `pytest`

This version is designed to be robust for clinical data processing while remaining readable.

---

### Refactored module

```python
"""Clinical longitudinal trajectory analysis.

This module provides a robust, vectorized implementation for summarizing
laboratory observations stored in SQLite and extracting blood-film reviewer
comments from Stage 1 JSON files.

The implementation is intended for Python 3.12+ and assumes `pandas` and
`numpy` are available.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

#: Canonical IDs and preferred display units for main trajectory sections.
CANONICAL_SERIES: Mapping[str, str] = {
    "haemoglobin": "g/L",
    "platelets": "x10^9/L",
    "wbc": "x10^9/L",
    "neutrophils": "x10^9/L",
    "ldh": "U/L",
    "uric_acid": "umol/L",
    "egfr": "mL/min",
    "creatinine": "umol/L",
}

#: Canonical IDs representing circulating immature / precursor cells.
PRECURSOR_CANONICAL_IDS: tuple[str, ...] = (
    "blasts",
    "myelocytes",
    "metamyelocytes",
    "promyelocytes",
)

#: Number of milestone rows to display per trajectory.
DEFAULT_MAX_MILESTONES: int = 10

#: Number of precursor dates to display.
DEFAULT_MAX_PRECURSOR_DATES: int = 10

#: Maximum number of comment snippets to display.
DEFAULT_MAX_COMMENT_SAMPLES: int = 50

#: Number of worker threads for JSON file parsing.
DEFAULT_JSON_MAX_WORKERS: int = 4


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Milestone:
    """A single selected observation point in a time series."""

    date: str
    value: float | None
    ref_low: float | None
    ref_high: float | None


@dataclass(frozen=True)
class TrajectorySummary:
    """Summary statistics for one canonical laboratory series."""

    canonical_id: str
    unit: str
    observation_count: int
    non_null_count: int
    min_value: float | None
    max_value: float | None
    latest_date: str | None
    latest_value: float | None
    milestones: tuple[Milestone, ...] = ()


@dataclass(frozen=True)
class PrecursorEvent:
    """Precursor cell observations recorded on a single date."""

    date: str
    cells: Mapping[str, float]


@dataclass(frozen=True)
class FilmComment:
    """A single reviewer comment extracted from a Stage 1 JSON file."""

    source_file: str
    collected_date: str | None
    comment: str


@dataclass(frozen=True)
class AnalysisResult:
    """Container for all analysis outputs."""

    unique_dates: int
    date_min: str | None
    date_max: str | None
    summaries: Mapping[str, TrajectorySummary]
    precursor_events: tuple[PrecursorEvent, ...]
    comments: tuple[FilmComment, ...]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _is_missing(value: Any) -> bool:
    """Return True if a value is null/missing/NaN."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, np.floating) and np.isnan(value):
        return True
    if isinstance(value, pd.Timestamp) and pd.isna(value):
        return True
    return False


def _to_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None for missing values."""
    if _is_missing(value):
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        LOGGER.debug("Failed to convert %r to float", value)
        return None

    if math.isnan(result):
        return None

    return result


def _clean_date(value: Any) -> str | None:
    """Normalize a date-like value to a display string."""
    if _is_missing(value):
        return None

    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()
    return text if text else None


def _fmt_number(value: float | None, decimals: int = 1) -> str:
    """Format a numeric value for reporting."""
    if value is None:
        return "NA"
    return f"{value:.{decimals}f}"


def _fmt_ref_range(ref_low: float | None, ref_high: float | None) -> str:
    """Format a reference range."""
    low = _fmt_number(ref_low, 1)
    high = _fmt_number(ref_high, 1)
    return f"{low}-{high}"


# ---------------------------------------------------------------------------
# Database access
# ---------------------------------------------------------------------------


def open_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with Row access enabled.

    Raises:
        FileNotFoundError: If the database file does not exist.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_observation_timeline(
    conn: sqlite3.Connection,
) -> tuple[int, str | None, str | None]:
    """Return unique date count, earliest date, and latest date.

    Returns:
        A tuple of `(unique_dates, date_min, date_max)`.
    """
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(DISTINCT date) AS unique_dates,
                MIN(date) AS date_min,
                MAX(date) AS date_max
            FROM observations
            """
        ).fetchone()
    except sqlite3.OperationalError as exc:
        raise ValueError(
            "Unable to query observations table. "
            "Ensure the table exists and is accessible."
        ) from exc

    unique_dates = int(row["unique_dates"])
    date_min = _clean_date(row["date_min"])
    date_max = _clean_date(row["date_max"])
    return unique_dates, date_min, date_max


def load_observation_frame(
    conn: sqlite3.Connection,
    canonical_ids: tuple[str, ...] | list[str],
) -> pd.DataFrame:
    """Load observations for multiple canonical IDs in one query.

    Args:
        conn: Open SQLite connection.
        canonical_ids: Canonical IDs to load.

    Returns:
        A pandas DataFrame with columns:
        - date
        - canonical_id
        - value_numeric
        - ref_low
        - ref_high
        - units

    Raises:
        ValueError: If the observations table cannot be queried.
    """
    if not canonical_ids:
        return pd.DataFrame(
            columns=["date", "canonical_id", "value_numeric", "ref_low", "ref_high", "units"]
        )

    placeholders = ",".join("?" for _ in canonical_ids)
    sql = f"""
        SELECT
            date,
            canonical_id,
            value_numeric,
            ref_low,
            ref_high,
            units
        FROM observations
        WHERE canonical_id IN ({placeholders})
        ORDER BY date ASC
    """

    try:
        df = pd.read_sql_query(sql, conn, params=list(canonical_ids))
    except sqlite3.OperationalError as exc:
        raise ValueError(
            "Unable to query observations table. "
            "Ensure the table exists and has expected columns."
        ) from exc

    if df.empty:
        return pd.DataFrame(
            columns=["date", "canonical_id", "value_numeric", "ref_low", "ref_high", "units"]
        )

    # Vectorized coercion.
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ("value_numeric", "ref_low", "ref_high"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_precursor_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load precursor cell observations in one query.

    Returns:
        A pandas DataFrame with precursor observations.
    """
    placeholders = ",".join("?" for _ in PRECURSOR_CANONICAL_IDS)
    sql = f"""
        SELECT
            date,
            canonical_id,
            display_name,
            value_numeric,
            units
        FROM observations
        WHERE canonical_id IN ({placeholders})
          AND value_numeric IS NOT NULL
        ORDER BY date ASC
    """

    try:
        df = pd.read_sql_query(sql, conn, params=list(PRECURSOR_CANONICAL_IDS))
    except sqlite3.OperationalError as exc:
        raise ValueError(
            "Unable to query precursor observations. "
            "Ensure the observations table exists."
        ) from exc

    if df.empty:
        return pd.DataFrame(
            columns=["date", "canonical_id", "display_name", "value_numeric", "units"]
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value_numeric"] = pd.to_numeric(df["value_numeric"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Vectorized summarization
# ---------------------------------------------------------------------------


def summarize_series(
    df: pd.DataFrame,
    canonical_id: str,
    unit: str,
    max


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
We need answer user's request. Need produce thorough architectural audit based on full repo. User asks in English. So analysis in English. Need think deeply. Need cover 1 end-to-end data flow, 2 concurrency/resilience audit, 3 telemetry/healthcheck design with concrete Rust implementation plan structs handlers across crates.

We need inspect code. Workspace Rust edition 2024? Cargo workspace. Crates aims-core, aims-db, aims-domain, aims-api. Lints forbid unsafe, deny unwrap/expect/panic etc. Migrations Postgres RLS. API axum, maud, htmx. Domain list_patients only. DB begin_tenant_tx uses SET LOCAL. Pool create. Entities patients query_as! checked.

Need identify issues. Need be principal architect. Need be accurate with sqlx transaction rollback edge cases. Need concurrency: async cancellation hazards, deadlocks? Rust async no locks? AppState Arc no locks. Transactions. Potential issue: begin_tenant_tx begins pool.begin() and executes set_config. If cancelled after begin before set_config? Transaction dropped queues rollback. okay. If cancellation during commit? sqlx Transaction commit returns; if cancelled during commit? Need know sqlx behavior: commit runs COMMIT. If future cancelled while running, connection may be in indeterminate state? sqlx docs? Transaction::commit if cancelled? It likely leaves transaction open? Actually sqlx pool connection: if drop transaction, it rolls back. If commit future cancelled mid-commit, the connection may be returned? Need discuss. In list_patients: let mut tx = begin; let patients = list_active(&mut *tx).await?; tx.commit().await?; Ok. If handler request cancelled after fetch before commit, tx drops -> rollback. Good. If cancelled during commit, possible connection not cleanly closed? sqlx handles? We should mention. Also if commit succeeds but future cancelled before returning Ok? If commit future completed? If cancelled after COMMIT sent? The result may be lost? Need nuance. Axum request cancellation: client disconnect cancels handler. If commit in progress, potential ambiguity. For read-only list, not critical. For money ops, need design: avoid relying on commit future alone? Use idempotency, outbox, or poll? We can propose.

Unchecked unwrap calls: code denies. In main: tracing_subscriber EnvFilter try_from_default_env().unwrap_or_else okay no unwrap. dotenvy::dotenv().ok() fine. config uses env var parse. ApiError match only AimsError::Db(_) currently exhaustive? AimsError enum only Db. wildcard_enum_match_arm deny? It matches one variant, no wildcard, ok. templates uses medicare_number.as_deref().unwrap_or("—") okay. CentAmount test allows unwrap? It uses assert no unwrap. Lints? clippy indexing_slicing deny, no indexing. Potential panic sources: maud? no. Arc no. TenantId parse uses FromStr. sqlx query_as checked offline. No unwrap.

Potential deadlocks: No mutex. Database transaction with single connection. No nested transactions. RLS GUC. No locks in Rust. Deadlock in Postgres? list read only no locks. Future writes: ledger constraint trigger etc. Need discuss ordering, FK locks, tenant context. Potential deadlock with RLS and set_config? No. If multiple ops on same tenant? Postgres MVCC. Money path: cross-entity writes in one tx. Need define lock ordering: appointments -> encounters -> notes -> invoices -> claims -> payments -> ledger? Need mention. Deferrable constraint trigger ledger_group_balance: with INITIALLY IMMEDIATE, statement end. If service SET CONSTRAINTS DEFERRED, can create risk of unbalanced intermediate state visible? Within tx no. But if long tx, constraint deferred to commit can allow temporary unbalanced; commit fails if unbalanced. Potential blocking? Constraint trigger fires after insert; if deferred, not fire until commit. Could cause long-lived transactions. Need recommend.

Concurrency hazards: AppState immutable. Pool PgPool. Each tx one connection. No await_holding_lock because no locks. But sqlx Executor &mut Transaction. If pass &mut *tx to query. Fine. Cancellation: request drop cancels. Transaction rollback on drop. However if a domain op does multiple steps, partial writes rolled back. Need ensure no resource leaks. Potential issue: begin_tenant_tx sets GUC on transaction. If caller drops tx without commit, rollback. If connection returned to pool after rollback? sqlx queues rollback on drop; will run when pooled connection next used? The doc says queues rollback on drop; it will run when pooled connection is next used. Is that safe? If connection dropped from pool, maybe not? Need verify. sqlx Transaction drop: if not committed, it issues rollback? I recall Transaction has Drop that sends rollback if needed, but because async drop? In sqlx, Transaction's Drop is not async? It may set a flag and pool connection handles on return? The code comment says queues a rollback on drop (it will run when pooled connection is next used). That means if connection is returned to pool with pending rollback, next user gets rollback first. If pool shuts down, may drop connection without rollback? In Postgres server terminates connection and rolls back. Safe. But if the same connection is reused before rollback? It runs before next use. Need discuss.

Potential issue: tenant GUC is transaction-scoped SET LOCAL. If rollback queued but not executed, and connection is used? It executes rollback before next query. Good. If connection is in pool and app code accidentally uses raw pool? pool.check uses SELECT 1 without tenant context. That's ok not tenant table. But if someone uses pool directly for tenant table, RLS fail-closed zero rows. Good.

End-to-end data flow: main sync setup: color_eyre, dotenv, tracing, tokio runtime, load_config, create_pool, check, state Arc, router, bind, serve. Request /: handler index State Arc<AppState> -> aims_domain::ops::patients::list_patients(&pool, tenant) -> begin_tenant_tx(pool, tenant): pool.begin, set_config app.current_tenant_id true; patients::list_active(tx) query_as! SELECT ... FROM patients WHERE active ORDER BY...; RLS policy filters tenant_id = current_setting; fetch_all; commit; return Vec<Patient>; templates::page maud HTML; axum Html. /patients fragment same. /healthz returns static. Error: ApiError from AimsError; IntoResponse 500. Process errors eyre in main.

Need mention migrations: 0001 roles, RLS helper, tenants, practitioners, locations. 0002 users, sessions, audit. 0003 patients etc. 0004 appointments. 0005 clinical notes. 0006 money. 0007 ledger. 0008 candidates. Dev seed fixed tenant. App connects as aims_app, .env AIMS_TENANT_ID. RLS context. Check query.

Need concurrency/resilience audit more details:
- Lints strong; no unsafe; no unwrap.
- Edition 2024? maybe features.
- Potential issue: main creates runtime then block_on; async_main. If signal? no graceful shutdown. axum::serve awaits indefinitely. No shutdown on Ctrl-C. Propose with tokio::signal.
- No request timeout, no rate limiting, no auth. Healthz shallow.
- Error handling: ApiError only Db. Domain ops return AimsError; no validation. tracing::error logs full error; okay. No request ID.
- Telemetry: currently tracing instrument handlers/domain/db, env filter. No structured fields for request id, tenant in all layers? list_patients fields tenant. patients list_active skip conn err debug. No metrics.
- Health check: /healthz static, doesn't check DB. startup check does SELECT 1. Need deep probe.
- Concurrency: no locks; Arc. PgPool bounded? Default max_connections? Need set. create_pool uses PgPool::connect with default options. Could exhaust. Need options max_connections, min, acquire timeout, idle timeout, statement cache? Need propose.
- Resilience: no retry policy for transient DB errors. No circuit breaker. No graceful pool close. No timeouts on queries. sqlx no default acquire timeout? Pool has. Need set.
- Cancellation: For read-only fine. For future writes, need commit ambiguity, idempotency, outbox. Domain op one tx. If request cancelled after commit but before response, client gets failure but DB committed. Need idempotency keys, client retry. For V1 read only acceptable. For money path, require idempotency and outbox.
- Transaction rollback edge cases: begin_tenant_tx if set_config fails, tx dropped rollback. If list_active fails, rollback. If commit fails due to network, transaction state unknown; sqlx returns Err, tx dropped? If commit fails, it may rollback? Need mention: a commit failure can mean commit in progress; don't assume rollback. For critical writes, verify via idempotent read or outbox. In current read-only no issue.
- Deadlocks: no Rust locks. Postgres: constraint trigger ledger_group_balance scans group; if large groups, can lock? Constraint trigger after insert takes row locks? It reads group. Could be heavy. If two transactions insert same group? group_id unique per op, no. If multiple entries same group in one statement, okay. If deferred and long tx, can hold locks. Need recommend group size small, immediate statement. FK constraints can cause lock waits; define ordering. RLS policies use current_setting; no locking.
- Unchecked unwrap: none. But potential panics: CentAmount Display uses unsigned_abs safe. NaiveDate in template? maud Display. No index. TenantId parse returns error. Sqlx query checked. Potential panic in maud? if invalid? no.
- Configuration: no validation of listen_addr parse? It is String passed to TcpListener::bind; if invalid, eyre. Could use SocketAddr newtype. AIMS_TENANT_ID fixed. Database URL may contain creds; logs? tracing info tenant only. Need avoid logging DATABASE_URL.
- Security: no auth, no CSRF, no cookie session. Not in scope? Could mention. RLS fail closed. aims_app no BYPASSRLS. dev seed. item_code_catalog revoke. ledger immutability.
- sqlx offline: query_as! uses .sqlx. Need ensure .sqlx tracked. If missing build offline. Fine.
- Layering: domain depends db, api depends domain. No repository. Good.
- AimsError only Db; exhaustive match in ApiError currently only Db. If add variants, compiler forces. Good.
- Potential issue: ApiError derive Error transparent, From AimsError. In into_response, tracing::error!(error = %self.0) moves? self.0 is AimsError; match &self.0. okay.
- Potential issue: handlers index and patients_fragment call list_patients. No pagination; ORDER BY family_name, given_names. At scale, full table scan? RLS filter tenant_id; index patients_tenant (tenant_id, family_name). WHERE active not in index. Could add partial index (tenant_id, family_name, given_names) WHERE active. Need mention.
- Patient struct family_name String from citext cast text. Good.
- date_of_birth NaiveDate; sqlx chrono. Display in template; no timezone issue date only.
- medicare_number Option<String>; template em dash.
- CSS raw in maud style; entity safe. Good.
- main uses runtime.block_on; no worker threads config. okay.
- tracing subscriber no JSON formatter, no tracing_opentelemetry. Need propose.

Telemetry & Healthcheck design: Need concrete Rust implementation plan including structs and handlers across crates. Need propose adding metrics (probably use metrics crate? Or axum metrics? Could propose `metrics` + `metrics-exporter-prometheus` in aims-api, tracing subscriber with JSON, request ID middleware, tenant field, DB pool metrics via sqlx? sqlx doesn't expose pool metrics directly? PgPool has metrics? sqlx Pool has `metrics()` returning PoolMetrics (size, active, idle etc) in recent versions? Yes sqlx pool has metrics(). We can use. Need propose health endpoints: /healthz liveness, /readyz readiness shallow, /health/db deep? Use axum routes. Structs: HealthReport, DbHealth, ComponentHealth. Handler. Use Domain op? Health check should not set tenant? Use pool check SELECT 1. Deep check can run in separate transaction? For RLS, maybe as aims_app no tenant; SELECT 1. Could check migration version? sqlx migrate? Maybe query pg? Need avoid superuser. Could check `SELECT 1` and pool metrics. For deeper, verify tenant context: begin_tenant_tx with config.tenant, run `SELECT current_setting('app.current_tenant_id', true)` and a read-only query to a tenant table? But as aims_app with tenant context, can see tenant rows. Could do `SELECT count(*) FROM tenants WHERE id = $1`? tenants has no RLS? In 0001 tenants no apply_tenant_rls. It is global. Could query tenants id. Or query patients with tenant context and limit 1. Deep health should not be expensive. Use `SELECT 1` plus pool metrics; optional `SELECT current_setting`. For readiness, ensure DB reachable, migration state maybe `sqlx::migrate!().apply`? No, don't apply in runtime. Could query a sentinel table? Migrations create tables; query `SELECT 1 FROM tenants LIMIT 1`. But if no rows? dev seed has. Better query `information_schema.tables` for tenants? As aims_app has grants. Could check `SELECT count(*) FROM tenants` no RLS. Or `SELECT 1 FROM pg_tables WHERE tablename='patients'`? aims_app can query pg_catalog? likely. But simple.

Need propose metrics: HTTP request duration histogram, active requests, errors by status; DB query duration, pool active/idle, tx commit duration; domain op duration. Use `tracing` spans and `metrics` macros. Structs: MetricsState? If using global metrics recorder, no state. But for Prometheus handler need exporter. In axum 0.8, can use `prometheus` crate and `axum::response::Html`? Better use `metrics-exporter-prometheus` `PrometheusBuilder`. Add dependency. State maybe `MetricsState { prometheus: PrometheusBuilder }`? PrometheusBuilder can be global. Handler returns text. Need structured plan.

Need concrete code snippets. We can provide Cargo.toml additions, code in aims-api/src/telemetry.rs, health.rs, middleware.rs, state.rs changes, main changes, domain/db instrumentation. Need ensure lints no unwrap. Use expect? Deny expect. Need code avoid unwrap/expect. Use match/ok_or. For metrics recorder install: `metrics_exporter_prometheus::PrometheusBuilder::new().install() -> Result<(), Box<dyn Error + Send + Sync>>`; map to eyre. Avoid unwrap. For axum serve graceful shutdown: `tokio::select!` with signal. Need code.

Potential issue: lints deny `clippy::unwrap_used` etc. In code snippets, avoid `.unwrap()`. Use `?`, `match`, `ok_or_else`. For default env filter already uses unwrap_or_else. For tokio signal: `tokio::signal::ctrl_c().await` returns Result; handle.

Need propose request ID: use `Uuid::new_v4()`? aims-api has uuid? Currently not direct dependency. Could add uuid to aims-api or use `tracing` field random? Better add `uuid = { version = "1", features = ["v4", "serde"] }` to aims-api. Middleware sets `RequestId(Uuid)` extension, tracing span field. Use `axum::middleware::from_fn_with_state`. In axum 0.8 middleware. Need code.

Need structured tracing: replace fmt with JSON? Use `tracing-subscriber` with `json` feature. Need Cargo features. Env filter. Could use `tracing_opentelemetry` optional. But propose concrete: enable `json` feature, init with `tracing_subscriber::fmt().json().with_env_filter(...).init()`. Add `tracing-subscriber = { version="0.3", features=["env-filter","json"] }`. For production. Also set tenant in AppState? We can add `tenant` to spans in handlers. `#[tracing::instrument(skip(state), fields(tenant = %state.tenant))]`. Currently handlers skip state and no tenant. Domain has tenant. Add.

Metrics design:
- `http_requests_total` counter labels method, route, status.
- `http_request_duration_seconds` histogram labels method, route.
- `http_active_requests` gauge.
- `db_pool_connections` gauge labels state? Use sqlx `pool.metrics()`: size, max_size, active, idle, idle_acquiring? Need check fields. sqlx PoolMetrics has `size`, `max_size`, `num_idle`, `num_active`? In sqlx 0.9? Let's recall: `sqlx::pool::PoolMetrics` fields: `size: u32`, `max_size: u32`, `num_idle: u32`, `num_active: u32`, `num_acquire_queued: u32`? There is `PoolMetrics { size, max_size, num_idle, num_active, num_acquire_queued }`. We'll use generic.
- `db_query_duration_seconds` histogram labels op.
- `domain_op_duration_seconds` histogram labels op.
- `db_tx_commit_total` counter labels outcome.
Could use `metrics` crate macros. In aims-domain add metrics? It currently depends tracing only. Add `metrics = "0.24"`? Need version. Could avoid adding to domain by using tracing spans and a layer? But concrete plan can add metrics dependency to aims-core? Better: metrics instrumentation in aims-api and aims-db? Domain ops are business; can instrument in domain with `tracing` only, and metrics via tracing layer? To keep dependencies lean, use `tracing` spans with named operations and a custom `MetricsLayer`? Too complex. Simpler: add `metrics` to aims-db and aims-domain. But user's lints? okay.

Need concrete structs/handlers:
```
pub struct AppState {
  pub pool: Pool,
  pub tenant: TenantId,
  pub metrics: Metrics,
}
#[derive(Clone)]
pub struct Metrics {
  pub prometheus: PrometheusBuilder,
}
```
But PrometheusBuilder clone? It has Arc? I think `PrometheusBuilder` is Clone. Use for handler. Or state not needed if global recorder; handler can use `PrometheusBuilder::new().into_recorder()`? Better keep in state.

Health structs:
```
#[derive(Debug, serde::Serialize)]
#[serde(tag = "status", rename_all = "lowercase")]
pub enum HealthStatus { Ok, Degraded, Unavailable }
#[derive(Debug, Serialize)]
pub struct ComponentHealth { pub

 Considering the limited time by the user, I have to give the solution based on the thinking directly now.
```

#### Final Output Response

# AIMS Architectural Audit

## 1. End-to-End Data Flow

### 1.1 Process Startup

The process starts in `crates/aims-api/src/main.rs`.

```text
main()
  → color_eyre::install()
  → dotenvy::dotenv().ok()
  → tracing_subscriber init
  → tokio::runtime::Builder::new_multi_thread().build()
  → runtime.block_on(async_main())
```

`async_main()` performs synchronous-at-the-edge configuration and database readiness:

```text
async_main()
  → config::load_config()
      reads DATABASE_URL
      reads AIMS_TENANT_ID
      parses AIMS_TENANT_ID as aims_core::TenantId
      reads optional AIMS_LISTEN_ADDR
  → aims_db::create_pool(&config.database_url)
      PgPool::connect(database_url)
  → aims_db::check(&pool)
      SELECT 1
  → AppState { pool, tenant }
  → handlers::router(state)
  → TcpListener::bind(config.listen_addr)
  → axum::serve(listener, app).await
```

Important operational detail: the application is expected to connect as `aims_app`, the RLS-subject role. The migrations create:

- `aims_app`: non-superuser, no `BYPASSRLS`, RLS applies.
- `aims_ops`: non-superuser, `BYPASSRLS`, for ops/migrations/cross-tenant admin.

This is the correct boundary. The tenancy guarantee depends on the app role never bypassing RLS.

---

### 1.2 HTTP Request Flow: `/`

Route registration:

```rust
Router::new()
    .route("/healthz", get(healthz))
    .route("/", get(index))
    .route("/patients", get(patients_fragment))
    .with_state(state)
```

For `/`:

```text
Axum
  → index(State<Arc<AppState>>)
      → aims_domain::ops::patients::list_patients(&state.pool, state.tenant)
          → aims_db::begin_tenant_tx(pool, tenant)
              → pool.begin()
              → SELECT set_config('app.current_tenant_id', $1, true)
              → return Transaction
          → aims_db::patients::list_active(&mut *tx)
              → sqlx::query_as!(Patient, ...)
              → fetch_all
          → tx.commit().await?
      → templates::page(&patients)
          → maud html!
          → Html<String>
```

The full page is server-rendered. It embeds an htmx fragment target:

```html
div id="patients"
    hx-get="/patients"
    hx-trigger="load"
    hx-swap="innerHTML"
```

So the browser initially receives a full page, then htmx refetches `/patients` to exercise the fragment path.

---

### 1.3 HTTP Request Flow: `/patients`

```text
Axum
  → patients_fragment(State<Arc<AppState>>)
      → aims_domain::ops::patients::list_patients(&state.pool, state.tenant)
          → same transaction/data path as `/`
      → templates::patients_fragment(&patients)
          → Html<String>
```

The important property is that the full page and the htmx fragment use the same domain operation. There is no separate API path that could drift from the rendered path.

---

### 1.4 Domain Operation Flow

`crates/aims-domain/src/ops/patients.rs`:

```rust
pub async fn list_patients(pool: &Pool, tenant: TenantId) -> Result<Vec<Patient>, AimsError> {
    let mut tx = aims_db::begin_tenant_tx(pool, tenant).await?;
    let patients = aims_db::patients::list_active(&mut *tx).await?;
    tx.commit().await?;
    Ok(patients)
}
```

This follows the intended layering:

```text
Axum handler
  → domain operation
      → one sqlx transaction
          → tenant context set
          → entity query
      → commit
```

The domain layer is currently thin, but it is the correct seam. Future invariants, audit writes, money-path rules, and idempotency should attach here, not in handlers or raw SQL.

---

### 1.5 Tenant Context and RLS

`crates/aims-db/src/ctx.rs`:

```rust
pub async fn begin_tenant_tx<'c>(
    pool: &'c Pool,
    tenant: TenantId,
) -> Result<Transaction<'c, sqlx::Postgres>, sqlx::Error> {
    let mut tx = pool.begin().await?;

    sqlx::query("SELECT set_config('app.current_tenant_id', $1, true)")
        .bind(tenant.as_uuid().to_string())
        .execute(&mut *tx)
        .await?;

    Ok(tx)
}
```

The GUC is set with `is_local = true`, equivalent to `SET LOCAL`. That means it lives only for the transaction.

The RLS policy in migrations is:

```sql
CREATE POLICY tenant_isolation ON <table> FOR ALL
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```

Because `current_setting(..., true)` returns `NULL` when unset, an unset context yields zero rows, not an error. This is the correct fail-closed behavior.

The current `patients` query relies on this:

```sql
SELECT
    id,
    given_names,
    family_name::text AS "family_name!",
    date_of_birth,
    medicare_number
FROM patients
WHERE active
ORDER BY family_name, given_names
```

There is no explicit `WHERE tenant_id = ...`. That is intentional: RLS enforces tenant scope.

---

### 1.6 Entity Shape

`crates/aims-db/src/entities/patients.rs`:

```rust
#[derive(Debug, Clone, FromRow)]
pub struct Patient {
    pub id: PatientId,
    pub given_names: String,
    pub family_name: String,
    pub date_of_birth: NaiveDate,
    pub medicare_number: Option<String>,
}
```

This struct is the domain shape. There is no DTO conversion. That matches the stated architecture:

```text
FromRow struct = domain shape
```

`PatientId` comes from `aims-core` and is transparent to sqlx because it implements `Type<Postgres>`, `Encode`, and `Decode`.

---

### 1.7 Rendering

`crates/aims-api/src/templates.rs` renders:

- Full page: `templates::page(&patients)`
- Fragment: `templates::patients_fragment(&patients)`
- Table: `patients_table(patients)`

The table renders patient fields directly:

```rust
td { (p.family_name) }
td { (p.given_names) }
td { (p.date_of_birth) }
td { (p.medicare_number.as_deref().unwrap_or("—")) }
```

`maud` escapes interpolated text, which is appropriate for HTML. The embedded CSS is raw, which is also appropriate for `<style>` content.

---

### 1.8 Error Flow

Domain errors are `aims_core::AimsError`:

```rust
pub enum AimsError {
    #[error("database: {0}")]
    Db(#[from] sqlx::Error),
}
```

Handlers return:

```rust
Result<Html<String>, ApiError>
```

`ApiError` wraps `AimsError`:

```rust
#[derive(Debug, Error)]
#[error(transparent)]
pub struct ApiError(#[from] AimsError);
```

`IntoResponse` maps known domain errors to HTTP responses:

```rust
let (status, body) = match &self.0 {
    AimsError::Db(_) => (StatusCode::INTERNAL_SERVER_ERROR, "internal server error"),
};
```

Currently there is only one `AimsError` variant, so the match is exhaustive. When new variants are added, the compiler will force an explicit HTTP mapping decision. That is a good design property.

Process-level failures, such as missing environment variables, runtime build failures, listener bind failures, and database connectivity failures, are handled with `color_eyre::eyre::Result` in `main` / `async_main`. They do not become HTTP responses.

---

## 2. Concurrency & Resilience Audit

### 2.1 Overall Concurrency Model

The current runtime model is simple and mostly sound:

```text
AppState
  → Arc<AppState>
      → PgPool
      → TenantId
```

There are no mutexes, no RwLocks, no channel-based state, and no in-process locks. `AppState` is immutable after startup.

This is good. It avoids most Rust async deadlock classes at the application layer.

The only shared mutable state is inside `sqlx::PgPool`, which is designed for concurrent use.

---

### 2.2 Deadlock Risk

#### Rust-side deadlocks

Current code: none.

There are no locks held across `.await` points. The `await_holding_lock` lint is enabled, and the code does not introduce locks.

#### Postgres-side deadlocks

Current code: low.

The current operation is read-only:

```text
BEGIN
SET LOCAL app.current_tenant_id = ...
SELECT ...
COMMIT
```

Read-only transactions under MVCC do not take write locks, so the current V1 surface has minimal deadlock risk.

However, future money-path operations will introduce write transactions across multiple tables:

```text
appointments
clinical_encounters
clinical_notes
note_sign_offs
invoices
invoice_line_items
insurance_claims
payments
ledger_entries
daily_settlement_batches
audit_events
```

At that point, a stable lock ordering policy is required.

Recommended canonical order:

```text
1. tenant-scoped root entity
   e.g. appointments / encounters / patients

2. clinical document
   e.g. clinical_notes / note_sign_offs

3. invoice
   e.g. invoices

4. invoice lines
   e.g. invoice_line_items

5. claims
   e.g. insurance_claims

6. payments
   e.g. payments

7. ledger
   e.g. ledger_entries

8. settlement / sync
   e.g. daily_settlement_batches / accounting_sync_logs

9. audit
   e.g. audit_events
```

This order should be encoded in domain-operation tests, not left to developer memory.

---

### 2.3 Transaction Rollback Edge Cases

#### Normal error path

Current code:

```rust
let mut tx = aims_db::begin_tenant_tx(pool, tenant).await?;
let patients = aims_db::patients::list_active(&mut *tx).await?;
tx.commit().await?;
```

If `list_active` fails, `tx` is dropped. `sqlx::Transaction` queues a rollback. This is correct.

If `begin_tenant_tx` fails after `pool.begin()` but before `set_config`, the transaction is dropped and rolled back. Correct.

If `set_config` fails, the transaction is dropped and rolled back. Correct.

#### Cancellation before commit

Axum cancels handler futures when the client disconnects. If the request is cancelled after the transaction begins but before commit, the `Transaction` drops and queues rollback. This is acceptable for the current read-only path.

#### Cancellation during commit

This is the main future hazard.

If a client disconnects while `tx.commit().await` is in flight, the process can no longer distinguish:

- commit never reached Postgres,
- commit was accepted,
- commit response was lost.

For the current read-only `list_patients`, this is not dangerous.

For future money-path operations, this is dangerous. A client may receive a failure while the database commit succeeded, or vice versa.

Required future mitigations:

1. Idempotency keys on all money-path operations.
2. Outbox pattern for external side effects.
3. No external side effects before transaction commit.
4. Retries based on idempotency key, not blind retry.
5. Explicit “unknown commit state” handling in the domain error model.

Example future error variant:

```rust
pub enum AimsError {
    Db(sqlx::Error),
    CommitOutcomeUnknown {
        idempotency_key: String,
    },
}
```

The HTTP layer should then return `500` or `502` depending on policy, but the domain layer must not pretend the operation failed when it may have committed.

---

### 2.4 sqlx Transaction Drop Behavior

The code comment says:

> `Transaction` queues a rollback on drop (it will run when the pooled connection is next used).

This is acceptable because Postgres also rolls back on connection termination. However, it is worth making explicit in tests:

- dropped transaction rolls back writes,
- tenant GUC does not leak to next pooled connection,
- a subsequent query on the same connection does not see the previous tenant context.

The RLS leak suite already tests cross-tenant isolation, but it does not explicitly test GUC leakage after a dropped transaction on a reused connection.

Recommended Stage-1 SQL test addition:

```sql
BEGIN;
SELECT set_config('app.current_tenant_id', '<tenant-a>', true);
ROLLBACK;

-- New transaction, no tenant set.
BEGIN;
SELECT current_setting('app.current_tenant_id', true);
-- expected NULL
ROLLBACK;
```

This would directly prove transaction-scoped context hygiene.

---

### 2.5 Unchecked `unwrap` / `expect` / Panic Audit

Current code appears compliant with the workspace lints:

```toml
[workspace.lints.clippy]
unwrap_used = "deny"
expect_used = "deny"
panic = "deny"
todo = "deny"
unimplemented = "deny"
indexing_slicing = "deny"
wildcard_enum_match_arm = "deny"
await_holding_lock = "deny"
```

Observed code:

- No `.unwrap()` in production paths.
- No `.expect()` in production paths.
- No raw indexing.
- No `todo!()` / `unimplemented!()`.
- `unsafe_code = "forbid"` is declared in every crate.
- Test module in `aims-core::money` allows `unwrap`/`expect` only under `#[cfg(test)]`, which is acceptable.

Potential future panic sources to watch:

1. `NaiveDate` parsing from external input.
2. `TenantId` parsing from environment variables — currently handled with `parse::<TenantId>()` and wrapped as an error.
3. `SocketAddr` parsing for `AIMS_LISTEN_ADDR` — currently deferred to `TcpListener::bind`, which is okay but less explicit.
4. Any future use of `array[index]`, `slice[range]`, `str::as_bytes()[n]`, etc.
5. Any future use of `Arc::try_unwrap`, `Mutex::into_inner`, `RwLock::into_inner`.

Recommended improvement: introduce a `ListenAddr` newtype in `aims-core` or `aims-api::config` that parses at config load time.

```rust
pub struct ListenAddr(SocketAddr);

impl FromStr for ListenAddr {
    type Err = AddrParseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        s.parse::<SocketAddr>().map(Self)
    }
}
```

This moves a runtime bind failure into a config validation failure with a clearer message.

---

### 2.6 Pool Resilience

`create_pool` currently uses:

```rust
PgPool::connect(database_url).await
```

This uses sqlx default pool options. For production, this should be made explicit.

Recommended pool configuration:

```rust
PgPoolOptions::new()
    .max_connections(20)
    .min_connections(1)
    .acquire_timeout(Duration::from_secs(3))
    .idle_timeout(Some(Duration::from_secs(300)))
    .max_lifetime(Some(Duration::from_secs(1800)))
    .connect(database_url)
    .await
```

Values should be tuned to deployment, but the important properties are:

- bounded connections,
- acquire timeout,
- idle timeout,
- max lifetime,
- observability of pool metrics.

Without an acquire timeout, a saturated pool can cause requests to hang indefinitely waiting for a connection.

---

### 2.7 Query Timeout / Statement Timeout

The current code has no query timeout.

For V1 read-only patient listing, this is acceptable if the database is healthy and the tenant is small.

For future operations, query timeouts are important. Options:

1. sqlx pool/statement-level timeout, if enabled by configuration.
2. `statement_timeout` GUC per transaction.
3. Axum request timeout middleware.
4. Domain-operation timeout wrapper.

For money-path transactions, a transaction-level timeout is preferable to a request-level timeout alone, because the transaction is the unit of consistency.

Example:

```sql
SET LOCAL statement_timeout = '5s';
```

This should be set inside `begin_tenant_tx` or a future `begin_tenant_tx_with_policy`.

---

### 2.8 Request Cancellation and Resource Safety

Current request paths are safe because:

- no files are opened,
- no external resources are allocated,
- no background tasks are spawned,
- transactions drop on cancellation.

Future hazards:

1. Streaming audio uploads.
2. S3 multipart uploads.
3. External API calls inside a transaction.
4. Background jobs spawned from request handlers.
5. Long-running LLM inference calls.

Architectural rule:

```text
No external side effects inside a sqlx transaction.
```

Recommended pattern:

```text
1. Validate request.
2. Call external system if necessary.
3. Begin transaction.
4. Write durable state.
5. Write outbox row.
6. Commit.
7. Background worker performs external side effect.
```

This avoids holding a database transaction open while waiting on Tyro, Heidi, SMS, S3, Xero


---
