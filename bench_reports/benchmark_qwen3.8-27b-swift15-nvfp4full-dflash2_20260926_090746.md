# NInfer Benchmark & Quality Report

- **Model ID:** `qwen3.8-27b-swift15-nvfp4full-dflash2`
- **Date & Time:** 2026-09-26 09:09:17
- **Temperature:** `1.0`
- **Thinking Budget:** `2048` | **Max Tokens:** `8192`
- **Overall Quality Status:** **`PASS (Verified by Agent)`**

## 1. Performance Scorecard

| Test | Prompt Tokens | Thinking Tokens | Out Tokens | TTFT (s) | Total Time (s) | Decode (tok/s) | MTP Accept | Quality Status |
|---|---|---|---|---|---|---|---|---|
| Test 1: Empty Context (Dev Short Refactor) | 1,879 | 4,096 | 8,192 | 0.35 | 29.61 | 280.2 | 42.8% | **`PASS`** |
| Test 2: Half-Full Context (AIMS ~81k Repo Audit) | 81,441 | 4,096 | 8,192 | 11.39 | 53.81 | 193.3 | 29.3% | **`PASS`** |

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
We need answer user's request in English. Need produce final with identified issues and refactored robust optimized version with Python 3.12+ type annotations, docstrings, error handling, unit test examples. Need analyze script.

We need think thoroughly. User asks: expert Python systems/data engineer. Review clinical data processing script. Identify performance bottlenecks, missing edge cases, type safety issues. Provide fully refactored robust, vectorized/optimized version with Python 3.12+ type annotations, docstrings, error handling, and unit test examples.

We need likely include refactored code. Need decide architecture. Original connects to sqlite, prints trajectories, reads JSON glob. Need robust, vectorized/optimized. Since sqlite small? Could use pandas? They ask vectorized/optimized; likely use pandas for numerical summaries, but can keep sqlite and pandas optional? Need Python 3.12+ type annotations. Could provide module with functions: load_observation_series, summarize_series, milestone selection, load_json_comments, print report. Use sqlite3, json, pathlib, typing, math? For vectorized, use pandas if available; but to avoid dependency, we can implement optimized SQL aggregation and minimal Python loops. But "vectorized/optimized" suggests use pandas/numpy if possible. However clinical script maybe standalone. We can provide version using pandas for summaries and optional fastparquet? Need be practical. Could use sqlite3 to read into pandas DataFrame via pd.read_sql, then groupby. But if no pandas, maybe not. They didn't specify dependencies. As expert, can propose using pandas for vectorized numeric ops. But unit tests can use pandas. Need include type annotations.

Need identify bottlenecks:
- Repeated get_series executes 8 separate queries, fine but can fetch once all canonical ids and partition in Python/pandas.
- Milestone logic: creates list [hb_data[i] for i in range...] and checks membership repeatedly O(n^2) for large series; also if last not in sampled indices, uses tuple membership expensive.
- For precursors: inner list comprehension for each date O(D*P) filtering; use groupby.
- Comments: reads all JSON files sequentially, no streaming, no size limit, broad except pass hides errors, no validation, duplicate detection by 30-char prefix, no cap, no progress.
- No handling empty dates: dates[0] if no dates IndexError.
- hb_vals empty if all None -> min/max ValueError.
- Formatting None values with :.1f etc TypeError.
- ref_low/high may be None, prints None.
- date may not be string sortable? If date stored text, okay; if mixed, sorting issues.
- canonical_id hardcoded.
- No transaction/close, connection leaks.
- No path existence checks, glob may return none, json load exceptions ignored.
- Type safety: values from sqlite are Any; numeric may be Decimal, float, str, None; no conversion.
- No NaN handling: float('nan')? min/max with NaN? Python min/max treats NaN weird. Need coerce numeric, ignore nonfinite.
- Unit tests: test empty, all null, NaN, milestones, JSON comments, type conversion.

Refactored version: Could be a module `clinical_report.py`. Use dataclasses, protocols. Use `sqlite3`, `pathlib`, `json`, `typing`, `math`, `pandas as pd`? Need decide. If include pandas, code more vectorized. But unit tests can use in-memory sqlite. Provide optional pure Python fallback? Might be too long. The prompt asks fully refactored robust and vectorized/optimized version. I can provide with pandas (vectorized) and note install pandas. Use `pd.read_sql` with sqlite connection. Use `pd.to_numeric(errors='coerce')`, `df.groupby('canonical_id')`, `.dropna()`, `.min()`, `.max()`, `.tail(1)`, milestone sampling via `np.linspace` or `pd.Series.iloc`? Need avoid numpy? Pandas includes numpy. Use `pandas` and `numpy` for vectorized.

But if they expect no external dependencies? Python standard library? The original uses only stdlib. "vectorized/optimized" could mean use SQL aggregation and efficient loops, not necessarily pandas. But type annotations and unit tests. We can provide a robust standard-library version with optimized queries and O(1) milestone selection, plus optional pandas variant? The user specifically asks "vectorized/optimized". I can say: For true vectorization use pandas; below refactored module uses pandas for numeric summaries. If you want stdlib-only, include notes. But final should be useful. Maybe provide a complete module with pandas dependency. Need include unit test examples. Could also include a stdlib fallback to avoid dependency? That would be long.

Need craft final answer: sections:
1. Review findings: performance, edge cases, type safety.
2. Refactored code: module with functions.
3. Unit tests.
4. Notes: dependencies, usage.

Need ensure code is syntactically correct Python 3.12. Use `from __future__ import annotations`? Python 3.12 supports new union syntax, can use `list[str]`, `str | None`. Use `typing`.

Design refactored code:

```
from __future__ import annotations
import sqlite3, json, math, re
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Iterable, Sequence
import pandas as pd
import numpy as np

class ClinicalDataError(Exception): ...

def connect(db_path: Path) -> sqlite3.Connection: ...

def load_observations(conn: sqlite3.Connection, canonical_ids: Sequence[str]) -> pd.DataFrame:
    if not canonical_ids: return pd.DataFrame(columns=[...])
    placeholders = ','.join('?' for _ in canonical_ids)
    sql = f"""
      SELECT date, canonical_id, value_numeric, ref_low, ref_high, units
      FROM observations
      WHERE canonical_id IN ({placeholders})
    """
    df = pd.read_sql_query(sql, conn, params=list(canonical_ids), parse_dates=['date']?)
```

Date parsing: dates might be ISO strings. `parse_dates` can fail if inconsistent. Better not parse; keep as string. For sorting, if date text ISO, lexicographic works. Could provide `coerce_date`? Simpler: keep original date. Need handle empty. If `date` null? Filter? Use `df.dropna(subset=['date'])`? For observations with null date, cannot timeline. Could exclude or bucket. We'll raise or exclude. Use `df = df.dropna(subset=['date'])`.

Convert numeric columns:
```
for col in ['value_numeric','ref_low','ref_high']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
```
This handles strings, Decimal, NaN.

Need `canonical_id` lower? Hardcoded.

`SeriesSummary` dataclass:
```
@dataclass(frozen=True)
class SeriesSummary:
    canonical_id: str
    count: int
    non_null: int
    min: float | None
    max: float | None
    latest_date: str | None
    latest_value: float | None
    milestones: tuple[tuple[str, float | None, float | None, float | None], ...]
```
But if value None, milestones maybe None. We can format.

Function `summarize_series(df: pd.DataFrame, canonical_id: str, max_milestones: int=10) -> SeriesSummary | None`:
- subset = df[df.canonical_id == cid]
- if empty return None
- numeric = subset.value_numeric.dropna()
- latest = subset.iloc[-1] if not empty after sort? Need sort by date. Sort df initially by date, canonical_id.
- milestone indices: vectorized selection. If n <= max_milestones, all. Else choose evenly spaced including last? Original includes first and step, and ensures last. We can choose indices `np.unique(np.linspace(0, n-1, num=max_milestones).round().astype(int))`; if last not included add n-1. This is vectorized. Use `subset.iloc[idx]`.
- Return.

Need `format_summary` functions.

Precursors: `load_precursors(df)` maybe from df where canonical_id in list and value_numeric notna. Group by date: `grouped = precursors.groupby('date', sort=True).apply(lambda g: ...)`. For performance, use `pivot = precursors.pivot_table(index='date', columns='display_name', values='value_numeric', aggfunc='first')` but need display_name. Original query selects display_name. We need include display_name in observations. If not, use canonical_id. We'll select display_name. For each date last 10, produce strings. Vectorized: `prec['label'] = prec['display_name'].astype(str) + '=' + prec['value_numeric'].astype(str)` then groupby date list, `', '.join`. Use `groupby` with `sort=True`.

LDH: all rows. If large, maybe limit? Provide `max_rows` parameter. Use `df[df.canonical_id == 'ldh']`.

Renal: summarize.

JSON comments: `load_comment_files(directory: Path) -> list[CommentRecord]`. Robust: use `pathlib.Path.glob('*.json')`, read with encoding, catch JSONDecodeError, log? No logging? Could use `logging`. Provide `CommentRecord(date: str|None, source_file: str, comments: list[str])`. Validate comments list; if string, wrap. Dedupe snippets: use set of normalized first N chars. Cap output. Use `max_examples` parameter.

Need error handling: `read_json_comments` can skip unreadable files and count errors. Use `try except (OSError, json.JSONDecodeError, UnicodeDecodeError)`.

Main function `generate_report(db_path: Path, json_dir: Path, output: TextIO | None = None) -> None` or return string. Use `contextlib.redirect_stdout`? Simpler: `io.StringIO` and print. Use `with closing(connect(...))`.

Need type annotations for functions. Use `logging` for warnings.

Potential issue: `pd.read_sql_query` with sqlite connection: If using `sqlite3.connect`, need `isolation_level=None`? Not necessary. Use `pd.read_sql(sql, conn, params=...)`. For empty canonical_ids, return empty DataFrame with columns.

Need ensure `pd` import. If user wants stdlib, not. We can mention dependency: `pip install pandas`.

Unit tests: Use `pytest`. Create in-memory sqlite with sample data. Test functions:
- `test_load_observations_empty` returns empty.
- `test_summarize_series_empty` returns None.
- `test_summarize_series_all_null` count 0? non_null 0, min None, latest value None, milestones include null? We can decide milestones from rows even if value null. Summary non_null 0. latest_value None.
- `test_milestones_includes_last` with 100 rows max_milestones=10, last index included.
- `test_numeric_coercion` strings and NaN.
- `test_load_comment_files` with temp JSON, invalid JSON skipped, comment string converted.
- `test_precursor_grouping`.

Need code for tests. Use `pytest` and `tmp_path`. For in-memory sqlite: `sqlite3.connect(':memory:')`, create table. Insert rows. `pd` uses same connection. Need ensure table exists.

Potential code details:

```
def _empty_obs_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=['date','canonical_id','value_numeric','ref_low','ref_high','units','display_name'])
```

`load_observations`:
```
def load_observations(conn: sqlite3.Connection, canonical_ids: Sequence[str] | None = None) -> pd.DataFrame:
    if canonical_ids is None:
       canonical_ids = DEFAULT_CANONICAL_IDS
    canonical_ids = [str(c) for c in canonical_ids]
    if not canonical_ids:
       return _empty_obs_frame()
    placeholders = ...
    sql = ...
    df = pd.read_sql_query(sql, conn, params=canonical_ids)
    if df.empty: return _empty_obs_frame()
    # ensure columns
    for col in ...: if col not in df: df[col] = pd.NA? 
    df['date'] = df['date'].astype(str)
    for col in numeric: df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.sort_values(['date', 'canonical_id'], kind='stable').reset_index(drop=True)
    return df
```
But if date is NaT? We convert to str; `pd.to_datetime` not used. If date null, `astype(str)` gives 'None'? Then dropna subset date won't drop because string 'None'. Need detect null before astype:
```
if 'date' in df:
    df['_date_missing'] = df['date'].isna()
    df['date'] = df['date'].astype('string')
    df = df[~df['_date_missing']]
```
Simpler: `df = df.dropna(subset=['date'])` before astype. If date is object None/NaN. Good.

`value_numeric` may be integer/float/decimal/string. `pd.to_numeric` handles.

Milestones:
```
def _milestone_indices(n: int, max_points: int) -> list[int]:
    if n <= 0: return []
    if n <= max_points: return list(range(n))
    # include first and last, evenly spaced
    idx = np.unique(np.linspace(0, n - 1, num=max_points).round().astype(int))
    if idx[-1] != n - 1: idx = np.append(idx, n - 1)
    return idx.tolist()
```
Need import numpy. If n=11, max=10, linspace 0..10 10 points includes last? likely. Unique sorted.

`summarize_series`:
```
def summarize_series(df: pd.DataFrame, canonical_id: str, max_milestones: int=10) -> SeriesSummary | None:
    sub = df[df['canonical_id'] == canonical_id]
    if sub.empty: return None
    sub = sub.sort_values('date', kind='stable')
    numeric = sub['value_numeric'].dropna()
    min_val = float(numeric.min()) if not numeric.empty else None
    max_val = float(numeric.max()) if not numeric.empty else None
    latest = sub.iloc[-1]
    latest_val = latest['value_numeric']
    latest_val = None if pd.isna(latest_val) else float(latest_val)
    idx = _milestone_indices(len(sub), max_milestones)
    milestones = tuple((str(row.date), None if pd.isna(row.value_numeric) else float(row.value_numeric), None if pd.isna(row.ref_low) else float(row.ref_low), None if pd.isna(row.ref_high) else float(row.ref_high)) for row in sub.iloc[idx].itertuples(index=False))
    return SeriesSummary(...)
```
Need `itertuples` with named attributes? If columns have names, `row.date` works? Itertuples returns namedtuple with field names, but if column name starts with digit, not. date okay. Use `row = sub.iloc[idx]` and iterate values:
```
for _, row in sub.iloc[idx].iterrows(): ...
```
Less performant but milestones small. Use `records = sub.iloc[idx].to_dict('records')`.

```
milestones = tuple(
  (
    str(rec['date']),
    _as_float(rec['value_numeric']),
    _as_float(rec['ref_low']),
    _as_float(rec['ref_high']),
  )
  for rec in sub.iloc[idx].to_dict('records')
)
```
`_as_float` returns None if NaN.

```
def _as_float(value: object) -> float | None:
    try:
       if value is None: return None
       f = float(value)
    except (TypeError, ValueError): return None
    return None if math.isnan(f) else f
```
But for pandas NA, float(pd.NA) raises? `float(pd.NA)` TypeError. Good.

`format_trajectory`:
```
def format_trajectory(summary: SeriesSummary | None, title: str, unit: str) -> str:
   if summary is None: return f"{title}\nNo data available."
   lines = [title]
   if summary.non_null:
      lines.append(f"{label} Range: Min {summary.min:.1f} {unit} | Max {summary.max:.1f} {unit} | Latest ({summary.latest_date}): {summary.latest_value:.1f} {unit}" if latest not None else ...)
   else: lines.append("No numeric values.")
   for d,val,rl,rh in summary.milestones:
       val_s = 'null' if val is None else f"{val:.1f}" ...
```
Need handle ref None.

Maybe use generic formatting. For platelets use 0 decimals. Could pass `decimals`. `format_value(value, decimals)`.

Precursors:
```
def format_precursors(df: pd.DataFrame, canonical_ids: Sequence[str] = PRECURSOR_IDS, max_dates: int=10) -> str:
    sub = df[df.canonical_id.isin(canonical_ids) & df.value_numeric.notna()]
    if sub.empty: return ...
    sub = sub.copy()
    sub['label'] = sub['display_name'].fillna(sub['canonical_id']).astype(str) + '=' + sub['value_numeric'].astype('float').map(lambda x: f"{x:g}")
    grouped = sub.groupby('date', sort=True)['label'].agg(', '.join)
    dates = grouped.index.tolist()
    lines = [f"Total Precursor Observations Recorded: {len(sub)}", f"Dates exhibiting ... ({len(dates)} timepoints):"]
    for d in dates[-max_dates:]: lines.append(f"  {d}: {grouped.loc[d]}")
```
Need `display_name` column. If not present, create:
```
if 'display_name' not in sub: sub['display_name'] = sub['canonical_id']
```

LDH:
```
def format_ldh(df, max_rows=1000):
   sub = df[df.canonical_id == 'ldh']
   if empty: ...
   tail = sub.tail(max_rows)
   lines = [f"--- 5. LD

 Considering the limited time by the user, I have to give the solution based on the thinking directly now.
```

#### Final Output Response

Below is a practical engineering review and a refactored implementation.

## 1) Issues in the original script

### Performance bottlenecks

1. **Repeated per-analyte SQL queries**
   - `get_series()` runs a separate query for each canonical analyte.
   - Better: fetch all needed observations once and partition/vectorize in memory.

2. **Quadratic milestone membership check**
   ```python
   if hb_data[-1] not in [hb_data[i] for i in range(0, len(hb_data), step)]:
   ```
   - This builds a list and performs tuple membership checks.
   - Cost grows with series length.
   - Better: compute milestone indices directly and include the last point if needed.

3. **Quadratic precursor grouping**
   ```python
   cells = [f"{r[1]}={r[2]}" for r in precursors if r[0] == d]
   ```
   - For each date, it scans the full precursor list.
   - Better: group by date once using `pandas.groupby()` or `defaultdict`.

4. **Sequential JSON loading with broad exception swallowing**
   - Reads every JSON file with no size guard, no structured logging, and `except Exception: pass`.
   - This can hide corruption, permission errors, malformed JSON, and encoding issues.
   - Better: explicit error handling, optional progress logging, and bounded output.

5. **No streaming / bounded memory strategy**
   - If observations or JSON files are large, the script can consume excessive memory.
   - Better: explicit limits, sampling, and optional chunked reads.

---

### Missing edge cases

1. **Empty database / no dates**
   ```python
   dates[0]
   dates[-1]
   ```
   - Raises `IndexError` if there are no observations.

2. **All numeric values are `NULL`**
   ```python
   hb_vals = [r[1] for r in hb_data if r[1] is not None]
   min(hb_vals)
   max(hb_vals)
   ```
   - Raises `ValueError` if `hb_vals` is empty.

3. **`None` values in formatted output**
   ```python
   print(f"... {hb_data[-1][1]} ...")
   ```
   - Fine for printing `None`, but later formatting like `:.1f` fails if `None` is used in numeric formatting.

4. **Non-numeric stored values**
   - SQLite can store numbers as `TEXT`, `DECIMAL`, `REAL`, or mixed types.
   - The original script assumes numeric compatibility.

5. **NaN handling**
   - If `value_numeric` contains `float('nan')`, `min()` / `max()` behavior can be misleading.
   - Need explicit non-finite filtering.

6. **Missing reference ranges**
   - `ref_low` and `ref_high` may be `NULL`.
   - The script prints them directly, which is okay, but numeric formatting would fail.

7. **Missing JSON fields**
   - The JSON loader assumes structure:
     - `comments`
     - `metadata.collected_date`
     - `metadata.requested_date`
     - `_source_file`
   - If `comments` is a string instead of a list, the code may misbehave.

8. **No path existence checks**
   - If the database or JSON directory does not exist, the script fails late or silently.

9. **No resource cleanup**
   - The SQLite connection is never closed explicitly.

10. **No cap on comment examples**
   - The unique-comment loop can print an unbounded number of lines.

---

### Type safety issues

1. **SQLite rows are untyped**
   - `cur.execute(...).fetchall()` returns `list[tuple[Any, ...]]`.
   - There is no runtime guarantee that `value_numeric` is numeric.

2. **Mixed numeric types**
   - Values may be:
     - `int`
     - `float`
     - `Decimal`
     - `str`
     - `None`
   - The script does not normalize them.

3. **Date assumptions**
   - The script assumes `date` is sortable as a string.
   - If dates are stored inconsistently, ordering can be wrong.

4. **JSON payload assumptions**
   - `d.get('comments', [])` may return:
     - `list[str]`
     - `str`
     - `None`
     - `dict`
   - The code does not validate the type.

5. **No return types**
   - Helper functions have no annotations, making contracts implicit.

---

## 2) Refactored robust implementation

The following version uses **pandas** for vectorized numeric handling and grouping. If you prefer a standard-library-only version, the same architecture can be implemented with `sqlite3` + `defaultdict`, but pandas is the cleanest way to get robust numeric coercion, `groupby`, and milestone sampling.

### Dependencies

```bash
pip install pandas numpy pytest
```

### Refactored module

```python
"""
Clinical longitudinal trajectory reporting.

This module provides robust, vectorized reporting over SQLite observations
and JSON stage-1 comment files.

It is designed for Python 3.12+ and uses pandas for numeric coercion,
grouping, and milestone sampling.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence, TextIO

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ClinicalReportError(RuntimeError):
    """Base exception for clinical report generation failures."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = Path(r"c:\tmp\bloods\data\bloods.db")
DEFAULT_JSON_DIR = Path(r"c:\tmp\bloods\output\stage1_json")

DEFAULT_ANALYTES: tuple[str, ...] = (
    "haemoglobin",
    "platelets",
    "wbc",
    "neutrophils",
    "ldh",
    "uric_acid",
    "egfr",
    "creatinine",
)

PRECURSOR_ANALYTES: tuple[str, ...] = (
    "blasts",
    "myelocytes",
    "metamyelocytes",
    "promyelocytes",
)

OBSERVATION_COLUMNS: tuple[str, ...] = (
    "date",
    "canonical_id",
    "display_name",
    "value_numeric",
    "ref_low",
    "ref_high",
    "units",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeriesSummary:
    """Summary statistics for a single analyte time series."""

    canonical_id: str
    total_rows: int
    numeric_rows: int
    min_value: float | None
    max_value: float | None
    latest_date: str | None
    latest_value: float | None
    milestones: tuple[tuple[str, float | None, float | None, float | None], ...]


@dataclass(frozen=True)
class CommentRecord:
    """A normalized comment record extracted from a stage-1 JSON file."""

    source_file: str
    collected_date: str | None
    comments: tuple[str, ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_float(value: Any) -> float | None:
    """
    Convert a scalar to float if possible.

    Returns:
        float: Converted value.
        None: If conversion fails or the value is non-finite.
    """
    if value is None:
        return None

    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(converted) or math.isinf(converted):
        return None

    return converted


def _format_value(value: float | None, *, decimals: int = 1) -> str:
    """
    Format a numeric value for reporting.

    Args:
        value: Numeric value or None.
        decimals: Number of decimal places.

    Returns:
        A formatted string.
    """
    if value is None:
        return "null"
    return f"{value:.{decimals}f}"


def _format_ref_range(low: float | None, high: float | None, *, decimals: int = 1) -> str:
    """
    Format a reference range.

    Args:
        low: Lower bound or None.
        high: Upper bound or None.
        decimals: Number of decimal places.

    Returns:
        A formatted range string.
    """
    low_s = _format_value(low, decimals=decimals)
    high_s = _format_value(high, decimals=decimals)
    return f"{low_s}-{high_s}"


def _milestone_indices(n: int, max_points: int) -> list[int]:
    """
    Select milestone indices from a series.

    The selection includes the first point, approximately evenly spaced points,
    and the last point.

    Args:
        n: Number of points.
        max_points: Maximum number of milestone points to return.

    Returns:
        A sorted list of indices.
    """
    if n <= 0:
        return []

    if max_points <= 1:
        return [n - 1]

    if n <= max_points:
        return list(range(n))

    idx = np.unique(
        np.linspace(0, n - 1, num=max_points).round().astype(int)
    )

    # Guarantee the latest observation is always included.
    if int(idx[-1]) != n - 1:
        idx = np.append(idx, n - 1)

    return [int(i) for i in idx]


def _empty_observation_frame() -> pd.DataFrame:
    """Return an empty observation DataFrame with expected columns."""
    return pd.DataFrame(columns=list(OBSERVATION_COLUMNS))


def _ensure_observation_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure expected observation columns exist.

    Args:
        df: Input DataFrame.

    Returns:
        A DataFrame with all expected columns present.
    """
    out = df.copy()
    for col in OBSERVATION_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out


def _coerce_observation_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize and coerce observation data.

    This function:
      - drops rows with missing dates
      - coerces numeric columns
      - sorts by date and canonical_id

    Args:
        df: Raw observations DataFrame.

    Returns:
        A normalized DataFrame.
    """
    if df.empty:
        return _ensure_observation_columns(df)

    out = _ensure_observation_columns(df)

    # Drop rows without a date.
    out = out.dropna(subset=["date"], how="any")

    if out.empty:
        return _ensure_observation_columns(out)

    # Normalize date to string. If dates are ISO-like, lexicographic ordering is stable.
    out["date"] = out["date"].astype("string")

    # Coerce numeric fields.
    for col in ("value_numeric", "ref_low", "ref_high"):
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # Optional: coerce display_name to string for safe reporting.
    out["display_name"] = out["display_name"].astype("string")

    # Stable sort for deterministic milestones.
    out = out.sort_values(
        by=["date", "canonical_id"],
        kind="stable",
    ).reset_index(drop=True)

    return out


# ---------------------------------------------------------------------------
# Database access
# ---------------------------------------------------------------------------


def connect_sqlite(db_path: str | Path) -> sqlite3.Connection:
    """
    Open a SQLite connection.

    Args:
        db_path: Path to SQLite database.

    Returns:
        A SQLite connection.

    Raises:
        ClinicalReportError: If the database file does not exist.
    """
    path = Path(db_path)
    if not path.exists():
        raise ClinicalReportError(f"Database file not found: {path}")

    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA query_only = 1")
    return conn


def load_observations(
    conn: sqlite3.Connection,
    canonical_ids: Sequence[str] | None = None,
) -> pd.DataFrame:
    """
    Load observations for the requested canonical IDs.

    Args:
        conn: Open SQLite connection.
        canonical_ids: Canonical analyte IDs to load.
            If None, loads DEFAULT_ANALYTES plus PRECURSOR_ANALYTES.

    Returns:
        A normalized pandas DataFrame.

    Raises:
        ClinicalReportError: If the query fails.
    """
    if canonical_ids is None:
        canonical_ids = tuple(dict.fromkeys((*DEFAULT_ANALYTES, *PRECURSOR_ANALYTES)))

    canonical_ids = [str(c).strip() for c in canonical_ids if str(c).strip()]
    if not canonical_ids:
        return _empty_observation_frame()

    placeholders = ", ".join("?" for _ in canonical_ids)
    sql = f"""
        SELECT
            date,
            canonical_id,
            display_name,
            value_numeric,
            ref_low,
            ref_high,
            units
        FROM observations
        WHERE canonical_id IN ({placeholders})
    """

    try:
        df = pd.read_sql_query(
            sql,
            conn,
            params=canonical_ids,
        )
    except Exception as exc:
        raise ClinicalReportError(f"Failed to load observations: {exc}") from exc

    return _coerce_observation_frame(df)


# ---------------------------------------------------------------------------
# Series summarization
# ---------------------------------------------------------------------------


def summarize_series(
    df: pd.DataFrame,
    canonical_id: str,
    *,
    max_milestones: int = 10,
) -> SeriesSummary | None:
    """
    Summarize one analyte time series.

    Args:
        df: Normalized observations DataFrame.
        canonical_id: Canonical analyte ID.
        max_milestones: Maximum number of milestone rows to include.

    Returns:
        A SeriesSummary if data exists, otherwise None.
    """
    if df.empty:
        return None

    sub = df[df["canonical_id"] == canonical_id]
    if sub.empty:
        return None

    numeric = sub["value_numeric"].dropna()
    numeric = numeric[np.isfinite(numeric)]

    min_value = float(numeric.min()) if not numeric.empty else None
    max_value = float(numeric.max()) if not numeric.empty else None

    latest_row = sub.iloc[-1]
    latest_value = _as_float(latest_row["value_numeric"])

    idx = _milestone_indices(len(sub), max_milestones)
    milestone_records = sub.iloc[idx].to_dict(orient="records")

    milestones = tuple(
        (
            str(rec["date"]),
            _as_float(rec["value_numeric"]),
            _as_float(rec["ref_low"]),
            _as_float(rec["ref_high"]),
        )
        for rec in milestone_records
    )

    return SeriesSummary(
        canonical_id=canonical_id,
        total_rows=int(len(sub)),
        numeric_rows=int(len(numeric)),
        min_value=min_value,
        max_value=max_value,
        latest_date=str(latest_row["date"]),
        latest_value=latest_value,
        milestones=milestones,
    )


def format_trajectory(
    summary: SeriesSummary | None,
    *,
    title: str,
    unit: str,
    decimals: int = 1,
) -> list[str]:
    """
    Format a trajectory block for reporting.

    Args:
        summary: Series summary or None.
        title: Section title.
        unit: Measurement unit.
        decimals: Decimal places for numeric formatting.

    Returns:
        A list of report lines.
    """
    lines: list[str] = []
    lines.append(title)

    if summary is None:
        lines.append("  No data available.")
        return lines

    if summary.numeric_rows > 0 and summary.min_value is not None and summary.max_value is not None:
        latest_text = _format_value(summary.latest_value, decimals=decimals)
        lines.append(
            "  "
            f"Range: Min {_format_value(summary.min_value, decimals=decimals)} {unit} | "
            f"Max {_format_value(summary.max_value, decimals=decimals)} {unit} | "
            f"Latest ({summary.latest_date}): {latest_text} {unit}"
        )
    else:
        lines.append("  No numeric values available.")

    if not summary.milestones:
        lines.append("  No milestones.")
        return lines

    lines.append("  Historical milestones:")
    for date, value, ref_low, ref_high in summary.milestones:
        ref = _format_ref_range(ref_low, ref_high, decimals=decimals)
        val = _format_value(value, decimals=decimals)
        lines.append(f"  {date}: {val} {unit} (ref {ref})")

    return lines


# ---------------------------------------------------------------------------
# Precursor reporting
# ---------------------------------------------------------------------------


def format_precursors(
    df: pd.DataFrame,
    *,
    max_dates: int = 10,
) -> list[str]:
    """
    Format precursor / immature cell observations.

    Args:
        df: Normalized observations DataFrame.
        max_dates: Maximum number of dates to display.

    Returns:
        A list of report lines.
    """
    lines: list[str] = []
    lines.append("--- 4. LEUKOERYTHROBLASTIC BLOOD FILM / PRECURSORS ---")

    if df.empty:
        lines.append("  No precursor observations recorded.")
       


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
We need answer user: "Based on complete repository provided above, provide thorough architectural audit: 1. End-to-End Data Flow; 2. Concurrency & Resilience Audit; identify potential deadlocks, async cancellation hazards, unchecked unwrap calls, transaction rollback edge cases. 3. Telemetry & Healthcheck Design: propose concrete Rust implementation plan (including structs and handlers) to add structured tracing, metrics, and deep health check probes across all crates."

Need produce final answer. Need analyze code carefully. We have 45 files? Provided many. Need identify issues.

Let's inspect code.

Workspace: resolver 2, edition 2024 (maybe not stable? Rust 2024 edition? assume). Lints: unsafe_code forbid, clippy unwrap_used deny, expect_used deny, panic deny, todo deny, unimplemented deny, indexing_slicing deny, wildcard_enum_match_arm deny, await_holding_lock deny.

Crates: aims-core, aims-db, aims-domain, aims-api.

aims-core: newtypes TenantId, UserId, PatientId, PractitionerId via macro wrapping Uuid; CentAmount. sqlx encode/decode transparent. Error AimsError with Db(sqlx::Error). Note thiserror 2.

aims-db: Pool = PgPool. ctx begin_tenant_tx: pool.begin, execute set_config(... $1, true) bind tenant UUID string. pool.rs create_pool, check SELECT 1. entities patients Patient struct FromRow, list_active query_as! SELECT id, given_names, family_name::text AS "family_name!", date_of_birth, medicare_number FROM patients WHERE active ORDER BY... It takes conn impl Executor<'_, Database=Postgres>.

Potential issue: query_as! with `family_name::text AS "family_name!"` to pin non-null. It casts citext to text. Good.

Domain ops patients: list_patients(pool, tenant) -> begin_tenant_tx, list_active(&mut *tx), tx.commit. This is a read-only transaction; commit not strictly needed but okay. It does not set READ ONLY. Transaction held until commit. On error, tx dropped rollback. But if cancellation? Async fn cancellation: if future dropped after pool.begin and set_config but before commit/drop? Transaction drop impl queues rollback on connection? Need inspect sqlx behavior: Transaction drop: if not committed/rolled back, it will rollback when connection returned? In sqlx, Transaction has Drop that calls `self.rollback()`? Actually sqlx Transaction drop performs rollback by returning connection to pool? Need know. In sqlx, `Transaction` has `drop` that calls `self.rollback()`? I think it queues rollback? The code comment says it will run when pooled connection is next used. In async cancellation, if future is cancelled while awaiting `list_active` or `tx.commit`, the Transaction may be dropped, rollback queued. Is that safe? Need mention async cancellation hazard: if task is cancelled between `pool.begin()` and `set_config` execution? `pool.begin()` returns tx, then `sqlx::query(...).execute(&mut *tx).await?`. If cancellation occurs after `pool.begin()` acquired connection and before set_config completes, transaction dropped; rollback on drop. But if cancellation occurs during `pool.begin()`? pool.begin future may have acquired connection? Need discuss.

Potential issue: `begin_tenant_tx` takes `pool: &'c Pool`, returns `Transaction<'c, Postgres>`. The `sqlx::query("SELECT set_config('app.current_tenant_id', $1, true)").bind(tenant.as_uuid().to_string()).execute(&mut *tx).await?;` The `set_config` returns text. It binds string. Since GUC expects uuid? The policy casts `current_setting(...)::uuid`. If unset, `current_setting('app.current_tenant_id', true)` returns NULL? In Postgres, current_setting(name, true) returns NULL if unset. Casting NULL::uuid is NULL. Policy `tenant_id = NULL` yields NULL -> no rows. Good fail-closed.

But if set_config value is not valid UUID, casting to uuid will error. They bind tenant.as_uuid().to_string(), valid.

Concurrency & resilience: no locks. `await_holding_lock` lint irrelevant. `Arc<AppState>` no locks. Potential deadlock: none explicit. But DB deadlocks? Single query list. Transactions read-only, no locks except maybe row locks? No.

Unwrap calls: In main: `tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(...)` okay no unwrap. In config: parse tenant_id using parse::<TenantId> and wrap_err. TenantId implements FromStr from Uuid parse. Good. In templates: `p.medicare_number.as_deref().unwrap_or("—")` okay no unwrap. No `.unwrap()`/expect? There are tests with allow. Clippy indexing_slicing: no indexing. Potential `self.0` field access okay. `CentAmount` arithmetic can overflow? i64 add/sub/neg can overflow. In debug panic? Rust integer overflow panics in debug, wraps in release? Actually overflow in release wraps by default unless overflow checks. Workspace lints don't forbid overflow. Money arithmetic could overflow i64 if huge cents. Need mention. `Neg` `-self.0` can overflow for i64::MIN. Add/Sub can overflow. Should use checked/checked wrapping? For money, use checked arithmetic and error. This is resilience issue.

`CentAmount::Display` uses `unsigned_abs`, okay. `fmt::Result`.

`TenantId` FromStr uses Uuid parse. Good.

API: `AppState { pool, tenant }`. Router: /healthz returns "ok" static, does not check DB. Index and patients_fragment call domain list_patients. Error ApiError wraps AimsError. `impl IntoResponse` matches only `AimsError::Db(_)`. Since AimsError currently one variant, okay, but `wildcard_enum_match_arm` lint? Match arm only Db, no wildcard. If AimsError gets variants, exhaustive match forces. Good.

`main.rs`: creates tokio runtime, block_on async_main. `color_eyre::install`. `dotenvy::dotenv().ok()`. `tracing_subscriber::fmt().with_env_filter(...).init()`. Potential issue: tracing subscriber init in sync main; okay. `axum::serve(listener, app).await`. No graceful shutdown? It will run forever; Ctrl+C? tokio serve handles? `axum::serve` returns when connection errors? No signal handling. Could add graceful shutdown.

Healthcheck: shallow only. Need propose deep health checks.

End-to-end data flow: request HTTP GET / or /patients -> Axum router -> State<Arc<AppState>> -> handlers call aims_domain::ops::patients::list_patients(&state.pool, state.tenant) -> domain begins tenant tx via aims_db::begin_tenant_tx -> pool.begin -> set_config local app.current_tenant_id -> aims_db::patients::list_active(&mut *tx) -> sqlx checked query_as! SELECT patients WHERE active ORDER BY -> rows decoded into Patient (PatientId, String, NaiveDate, Option<String>) via FromRow, newtypes decode transparent -> Vec<Patient> -> commit tx -> templates render maud HTML -> Html response. RLS: app role aims_app, no BYPASSRLS, policies tenant_isolation using current_setting. Migrations create tables, RLS policies, roles. `patients` table tenant_id, citext family_name, medicare_number partial unique, active. `apply_tenant_rls` creates policy FOR ALL USING/WITH CHECK. App connects as aims_app. V1 fixed tenant from env.

Need mention sqlx offline checked queries: query_as! pinned to schema; `.sqlx` tracked. `family_name::text AS "family_name!"` because cast makes expression nullability not inferable, `!` pins NOT NULL.

Concurrency: all state immutable Arc. Pool is async, safe. No global locks. Potential async cancellation: if client disconnects during handler future, Axum cancels handler. If domain future is dropped while transaction open, Transaction drop should rollback. Need be precise: sqlx `Transaction` drop rolls back if not committed/rolled back. For `pool.begin()` future cancellation, if it acquires connection then drops, rollback? We need state: ensure no half-applied writes. For read-only list, no writes. For future money ops, cancellation between multi-statement transaction and commit can leave transaction open until drop; drop rollback. But if drop occurs after `commit` started? commit future cancellation? `tx.commit().await` if cancelled, commit may have been sent? In sqlx, commit is atomic; cancellation drops future, but underlying query? Need mention. The connection may be returned with commit in flight? SQLx transaction commit is a database operation; cancellation of future does not necessarily cancel SQL. If commit sent, it may commit; drop after commit? Need not overstate. For safety, domain ops should be idempotent and avoid long multi-step; use transaction scope.

Potential transaction rollback edge cases:
- `begin_tenant_tx` sets GUC with `SET LOCAL`. If `pool.begin` succeeds but `set_config` fails, tx dropped rollback; GUC local rolled back.
- If `list_active` returns error, `?` drops tx; rollback on drop.
- If `tx.commit` fails, transaction rolled back? commit failure means rollback? sqlx commit returns error; if commit fails, transaction is rolled back? Need mention.
- If task is cancelled while `tx.commit().await` is in flight, the future is dropped. SQLx may not be able to cancel an in-progress commit at database level; the connection may be returned and transaction state ambiguous. Need design: commit is last step; if uncertain, treat as unknown and use idempotency. For read-only op no issue.
- `begin_tenant_tx` returns tx with lifetime tied to pool. The caller must hold tx across all queries. Domain does.
- `list_active` takes `impl Executor<'_, Database = Postgres>`. Passing `&mut *tx` is okay. But `Executor` lifetime? It borrows tx for duration. Fine.
- Potential issue: `begin_tenant_tx` uses `pool.begin().await?` then `sqlx::query(...).execute(&mut *tx)`. If the set_config query fails, the transaction is dropped. Good.
- The RLS policy uses `current_setting('app.current_tenant_id', true)::uuid`. If context is set to a tenant id for which RLS policy exists, okay. For tables with tenant_id. The `tenants` table has no RLS? In 0001, no `apply_tenant_rls('tenants')`. App role can SELECT tenants. V1 fixed. The leak test doesn't include tenants. Tenants is global config. Fine.
- `users` no RLS global. Isolation via memberships. Fine.
- The app role has default privileges ALL on tables. Some tables revoke update/delete. RLS with FORCE? Migrations create roles but do not `ALTER TABLE ... FORCE ROW LEVEL SECURITY`? `apply_tenant_rls` only ENABLE ROW LEVEL SECURITY. Principles say `FORCE ROW LEVEL SECURITY` on tenant tables. Migrations only enable, not force. Table owner? The migration runner (superuser) owns tables; RLS not applied to table owner unless FORCE. Since app role is not owner, ENABLE is enough for app role. But principles say FORCE. The RLS leak test as app role passes without FORCE because app is not owner. But if table owner is aims_app? It isn't. So okay but deviation from docs. Need mention: `apply_tenant_rls` does not `ALTER TABLE ... FORCE ROW LEVEL SECURITY`; if any role owns table and isn't BYPASSRLS, RLS would be bypassed. Current roles: tables owned by migration superuser, so app role subject to RLS. For defense in depth, add FORCE.
- The `apply_tenant_rls` policy: `tenant_id = current_setting('app.current_tenant_id', true)::uuid`. For INSERT, WITH CHECK same. If current_setting returns NULL, no rows. Good.
- The `set_config` in begin_tenant_tx uses `true` (is_local) so transaction-scoped. Good.
- Potential issue: `current_setting` with missing_ok=true returns NULL if unset. In Postgres, for custom GUC? `app.current_tenant_id` is custom. If not set, returns NULL with missing_ok true. Good.
- `set_config` returns the new value. Not used.

Unchecked unwrap calls: none in production except `unwrap_or`. But `CentAmount` arithmetic can panic on overflow. `Uuid` decode? sqlx decode can fail. `TenantId::from_str` uses parse. `std::env::var` handled. `TcpListener::bind` handled. `axum::serve` handled. `color_eyre::install` handled. `dotenvy` ok.

Potential `tracing_subscriber` init multiple? main only.

`ApiError` display transparent. `IntoResponse` logs error. It maps only Db to 500. If domain adds NotFound etc, need match.

`Patient` struct: `date_of_birth: NaiveDate` sqlx chrono feature. Good.

`query_as!` uses `WHERE active` (boolean). Good.

`list_active` does not filter tenant explicitly because RLS. Good.

`Patient` medicare_number Option<String>. Template uses em dash.

`templates.rs` CSS includes `&`? It says kept entity-safe no & < >. CSS has `rgba(128,128,128,0.25)` no &. Good.

`maud` interpolation of `p.date_of_birth`? NaiveDate implements Display? chrono yes. `p.family_name` String. Good.

`handlers.rs` healthz no state. index and fragment duplicate domain call. Good.

Config: `AIMS_LISTEN_ADDR` optional default. `TenantId` parse. `TenantId` FromStr uses Uuid::parse_str. It accepts hyphenated? Uuid parse accepts canonical and maybe braced? Uuid::parse_str accepts any valid UUID format? It can parse hyphenated, simple, braced? It may accept. Good.

Telemetry & healthcheck design: Need propose concrete Rust implementation plan including structs and handlers across crates. Need include structured tracing, metrics, deep health check probes.

Current tracing: handlers have `#[tracing::instrument]`, domain op instrument, db list instrument. main init tracing subscriber with env filter. No metrics. Healthz shallow.

Need propose:
- Add `aims-core::telemetry` or `aims-api`? Since all crates need tracing spans, maybe `aims-core` or new `aims-observability` crate? User asks across all crates. Could propose new crate `aims-obs` to avoid dependency cycles. But workspace currently 4 crates. Could add `crates/aims-observability` with traits for metrics, tracing fields, health probe. Or keep in aims-core? aims-core is kernel; adding metrics dependency to core may be okay but core is pure? Better new crate `aims-observability` depends on tracing, prometheus? Or use `metrics` crate + `metrics-exporter-prometheus`. Need propose concrete structs and handlers.

Need respect lints: no unwrap, no panic. Use `Result`. Use `color_eyre` at process edge. Use `thiserror` for domain errors.

Metrics design:
- Use `metrics` facade crate (or `prometheus`). Propose `metrics` because backend-agnostic. Add `prometheus` exporter or `metrics-exporter-prometheus`. In `aims-api`, install recorder.
- Define metrics in `aims-obs`:
  - `aims_http_requests_total` counter labels: route, method, status, tenant? tenant label high cardinality? V1 fixed, okay but avoid tenant label if multi-tenant. Use route pattern (axum route not full URI), status class.
  - `aims_http_request_duration_seconds` histogram.
  - `aims_db_pool_active`/`aims_db_pool_idle`/`aims_db_pool_waiters` gauges via sqlx pool metrics? sqlx PgPool has `metrics()` returns PoolMetrics. Need poll periodically.
  - `aims_db_transaction_duration_seconds` histogram labels op, result.
  - `aims_domain_ops_total` counter labels op, result.
  - `aims_health_probe_total` counter labels probe, result.
  - `aims_tenant_context_set_total`? maybe.
- Structs:
```
pub struct Observability {
  pub metrics: Option<...>,
}
```
But metrics facade global. Use `metrics::describe_counter!` etc.

Need implement middleware in Axum:
- `TracingLayer` with `tracing_opentelemetry`? Or use `tower`/`axum` layers. Axum 0.8: `axum::middleware::from_fn`, `tower::Layer`. Need propose concrete handler/middleware.
- Structured tracing: Use `tracing-subscriber` with JSON formatter for production. Add `tracing-opentelemetry` + OTLP if desired. Use `#[instrument]` already. Add span fields: `route`, `request_id`, `tenant_id`. Generate request ID with `uuid` or `ulid`. Add extension `RequestContext`.
- Healthcheck: Add `/healthz/live` liveness, `/healthz/ready` readiness, `/healthz/deep` maybe. Need deep probe: DB connectivity as aims_app, RLS context check, ledger invariant? Deep health check should verify database connectivity, role, tenant context, RLS fail-closed, ledger balance, pool saturation. Need not run expensive invariant in readiness? Could have tiered: shallow (process), readiness (DB SELECT 1), deep (admin only) runs RLS leak mini-check and ledger invariant. Need concrete structs and handlers.

Need propose code snippets.

Potential implementation plan:
1. Add dependencies:
- aims-api: `metrics = "0.24"`, `metrics-exporter-prometheus = "0.24"` or `prometheus = "0.13"`, `tower` maybe already via axum, `axum-macros`? `uuid` for request id? aims-core has uuid. `opentelemetry` optional. `tracing-opentelemetry` optional.
- aims-db: `metrics` for pool metrics.
- aims-domain: `metrics` for op metrics.
- aims-obs (new) or aims-core? Let's propose new crate `aims-obs` to keep core minimal. But user said across all crates; adding crate may be okay. If want no new crate, put in `aims-core`? `aims-core` currently has no tracing. Adding `tracing` and `metrics` to core is acceptable as shared kernel? But core is parse-don't-validate + error. Could add `aims-core::telemetry` with macros. But metrics in

 Considering the limited time by the user, I have to give the solution based on the thinking directly now.
```

#### Final Output Response

# AIMS Architectural Audit

This audit is based strictly on the repository contents you provided. It is organized into the three requested areas:

1. **End-to-end data flow**
2. **Concurrency & resilience audit**
3. **Telemetry & healthcheck design**

I have focused on what the code *actually* does today, not what the docs *intend*.

---

## 1. End-to-End Data Flow

### 1.1 High-level flow

The current V1 runtime path is:

```text
HTTP client
  → Axum router
    → thin handler
      → aims_domain op
        → aims_db tenant transaction
          → sqlx checked query
            → PostgreSQL (as aims_app, RLS-scoped)
          → sqlx row decode
        → domain result
      → maud HTML rendering
    → Axum Html response
```

The only implemented business operation is:

```rust
aims_domain::ops::patients::list_patients
```

and the only HTTP routes are:

```text
GET /healthz
GET /
GET /patients
```

---

## 1.1 Request lifecycle for `GET /` and `GET /patients`

### Step 1 — Axum router

`crates/aims-api/src/handlers.rs`:

```rust
pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/healthz", get(healthz))
        .route("/", get(index))
        .route("/patients", get(patients_fragment))
        .with_state(state)
}
```

`AppState` is:

```rust
pub struct AppState {
    pub pool: Pool,
    pub tenant: TenantId,
}
```

where `Pool = sqlx::postgres::PgPool`.

The state is shared via `Arc<AppState>`, which is correct for Axum.

---

### Step 2 — Handler

For `GET /`:

```rust
async fn index(State(state): State<Arc<AppState>>) -> Result<Html<String>, ApiError> {
    let patients = aims_domain::ops::patients::list_patients(&state.pool, state.tenant).await?;
    Ok(templates::page(&patients))
}
```

For `GET /patients`:

```rust
async fn patients_fragment(State(state): State<Arc<AppState>>) -> Result<Html<String>, ApiError> {
    let patients = aims_domain::ops::patients::list_patients(&state.pool, state.tenant).await?;
    Ok(templates::patients_fragment(&patients))
}
```

Both handlers are intentionally thin. They do:

- extract shared state
- call one domain operation
- render HTML
- map errors to `ApiError`

There is no authentication, no tenant extraction from request, and no per-user context. The tenant is fixed in `AppState` from environment configuration.

---

### Step 3 — Domain operation

`crates/aims-domain/src/ops/patients.rs`:

```rust
pub async fn list_patients(pool: &Pool, tenant: TenantId) -> Result<Vec<Patient>, AimsError> {
    let mut tx = aims_db::begin_tenant_tx(pool, tenant).await?;
    let patients = aims_db::patients::list_active(&mut *tx).await?;
    tx.commit().await?;
    Ok(patients)
}
```

This is the correct layering pattern:

- one business action
- one transaction
- tenant context set first
- database access only through the tenant transaction

The transaction is technically read-only, but the code still commits it. That is acceptable and consistent with the “one operation = one transaction” rule.

---

### Step 4 — Tenant transaction helper

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

This does two things:

1. begins a Postgres transaction
2. sets a transaction-local GUC:

```sql
SELECT set_config('app.current_tenant_id', $1, true)
```

The `true` argument means the GUC is local to the transaction.

This matches the RLS policy in the migrations:

```sql
CREATE POLICY tenant_isolation ON ...
FOR ALL
USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
```

So the tenant context is:

- set per transaction
- transaction-scoped
- rolled back with the transaction
- fail-closed when unset

This is a strong tenancy design.

---

### Step 5 — Checked SQL query

`crates/aims-db/src/entities/patients.rs`:

```rust
pub async fn list_active(
    conn: impl Executor<'_, Database = Postgres>,
) -> Result<Vec<Patient>, sqlx::Error> {
    let rows: Vec<Patient> = sqlx::query_as!(
        Patient,
        r#"
        SELECT
            id,
            given_names,
            family_name::text AS "family_name!",
            date_of_birth,
            medicare_number
        FROM patients
        WHERE active
        ORDER BY family_name, given_names
    "#
    )
    .fetch_all(conn)
    .await?;
    Ok(rows)
}
```

Key points:

- this is a **checked** sqlx query
- `Patient` is the domain shape
- `PatientId` is decoded transparently because `aims-core` implements sqlx traits for it
- `family_name` is `citext` in the database and cast to `text` on output
- the `!` in `"family_name!"` pins the output as non-`NULL`

The entity struct is:

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

This is consistent with the “no DTO tier” decision.

---

### Step 6 — Database schema and RLS

From `db/migrations/0003_patients.sql`:

```sql
CREATE TABLE patients (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL REFERENCES tenants(id),
  given_names      text NOT NULL,
  family_name      citext NOT NULL,
  date_of_birth    date NOT NULL,
  gender           text,
  medicare_number  text,
  irn              text,
  active           boolean NOT NULL DEFAULT true,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX patients_tenant ON patients (tenant_id, family_name);

SELECT apply_tenant_rls('patients');
```

And from `db/migrations/0001_tenancy.sql`:

```sql
CREATE OR REPLACE FUNCTION apply_tenant_rls(t regclass) RETURNS void AS $$
BEGIN
  EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', t);
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = t::text
      AND policyname = 'tenant_isolation'
  ) THEN
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON %s FOR ALL
       USING (tenant_id = current_setting(''app.current_tenant_id'', true)::uuid)
       WITH CHECK (tenant_id = current_setting(''app.current_tenant_id'', true)::uuid)',
      t
    );
  END IF;
END $$;
```

So the full tenancy chain is:

```text
AIMS_TENANT_ID env
  → TenantId
    → begin_tenant_tx
      → SET LOCAL app.current_tenant_id
        → RLS policy filters rows by tenant_id
```

This is the correct kernel-level tenancy model.

---

## 1.2 Response path

After `list_patients` returns `Vec<Patient>`, the API renders HTML with `maud`.

For the full page:

```rust
pub fn page(patients: &[Patient]) -> Html<String> {
    let markup = html! { ... };
    Html(markup.into_string())
}
```

For the fragment:

```rust
pub fn patients_fragment(patients: &[Patient]) -> Html<String> {
    Html(patients_table(patients).into_string())
}
```

The table renders:

- `family_name`
- `given_names`
- `date_of_birth`
- `medicare_number` with an em-dash fallback

This is correct for the V1 htmx interface.

---

## 1.3 Error path

Domain errors are:

```rust
pub enum AimsError {
    #[error("database: {0}")]
    Db(#[from] sqlx::Error),
}
```

The API maps this to HTTP:

```rust
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        tracing::error!(error = %self.0, "request failed");
        let (status, body) = match &self.0 {
            AimsError::Db(_) => (StatusCode::INTERNAL_SERVER_ERROR, "internal server error"),
        };
        (status, body).into_response()
    }
}
```

Currently this is exhaustive because `AimsError` has one variant.

That is good. As new domain errors are added, the compiler will force you to make an explicit HTTP decision per variant.

---

## 2. Concurrency & Resilience Audit

This section identifies real issues, not theoretical ones.

---

## 2.1 Concurrency model

The application is:

- multithreaded Tokio runtime
- `Arc<AppState>` shared state
- `PgPool` shared pool
- no application-level locks

That is sound.

There are no `Mutex`/`RwLock` types in the current code, so the `await_holding_lock` lint is effectively not exercised yet.

---

## 2.2 Deadlock potential

### In-process deadlocks

**None found.**

There are no locks in the request path.

### Database deadlocks

The only operation is a read-only `SELECT` on `patients`. There are no write transactions yet, so database deadlock risk is currently minimal.

When money-path operations are added, you will need to enforce a consistent lock ordering. For example:

```text
invoice → line_items → ledger_entries
```

and always acquire related rows in the same order.

That is a future concern, not a current defect.

---

## 2.3 Async cancellation hazards

This is the most important area.

### 2.3.1 Cancellation of the domain operation

`list_patients` is:

```rust
let mut tx = aims_db::begin_tenant_tx(pool, tenant).await?;
let patients = aims_db::patients::list_active(&mut *tx).await?;
tx.commit().await?;
```

If the HTTP request is cancelled while this future is running, the future may be dropped.

In that case:

- the `Transaction` is dropped
- sqlx will roll back the transaction on drop
- the connection is returned to the pool

For this read-only operation, that is safe.

But there are subtleties.

---

### 2.3.2 Cancellation after `pool.begin()`

If the task is cancelled after `pool.begin()` has acquired a connection but before `set_config` completes, the transaction is dropped and rolled back.

That is acceptable.

However, you should be explicit in the design that:

- the tenant GUC is transaction-local
- a dropped transaction always rolls back
- no partial tenant context survives

The current code does this correctly.

---

### 2.3.3 Cancellation during `tx.commit()`

This is the more dangerous edge case.

`tx.commit().await` is the final step. If the future is cancelled while the commit is in flight, the runtime may drop the future before the commit result is observed.

In practice:

- for a read-only transaction, this is mostly harmless
- for future write transactions, this becomes a real issue

You must treat commit ambiguity as a first-class concern.

Recommendation:

- for write operations, do not assume “no commit” just because the future was cancelled
- design money-path operations to be idempotent
- use an explicit transactional outbox or idempotency key if commit state is ambiguous

This is already flagged in your design docs as an open item, and it is the right call.

---

## 2.4 Transaction rollback edge cases

### 2.4.1 `begin_tenant_tx` failure

If `set_config` fails, `?` propagates and `tx` is dropped.

Result:

- rollback on drop
- no partial tenant context

This is correct.

---

### 2.4.2 Query failure

If `list_active` fails, `?` propagates and `tx` is dropped.

Result:

- rollback on drop
- no partial state

Correct.

---

### 2.4.3 Commit failure

If `tx.commit()` fails, the transaction is not committed.

For future write paths, you need to decide what “commit failed” means operationally.

Recommendation:

- treat commit failure as a terminal domain error
- do not silently retry in-memory state
- use idempotency keys for all money-path writes

---

### 2.4.4 Cancellation + rollback

The current code is safe because:

- the operation is read-only
- `Transaction` drop semantics handle rollback

But this should be documented as an invariant:

> Every domain operation must be safe to drop at any `await` point.

That is a good rule to enforce as the codebase grows.

---

## 2.5 Unchecked `unwrap` / panic audit

There are **no production `unwrap()` or `expect()` calls** in the current code.

The only near-panic surfaces are:

### 2.5.1 Integer overflow in `CentAmount`

`crates/aims-core/src/money.rs`:

```rust
impl Add for CentAmount {
    fn add(self, rhs: Self) -> Self {
        Self(self.0 + rhs.0)
    }
}
```

Same for `Sub` and `Neg`.

This is a real resilience issue.

`i64` overflow can:

- panic in debug builds
- wrap in release builds

For money, wrapping is unacceptable.

#### Recommended fix

Make arithmetic checked:

```rust
pub fn checked_add(self, rhs: Self) -> Option<Self> {
    self.0.checked_add(rhs.0).map(Self)
}

pub fn checked_sub(self, rhs: Self) -> Option<Self> {
    self.0.checked_sub(rhs.0).map(Self)
}

pub fn checked_neg(self) -> Option<Self> {
    self.0.checked_neg().map(Self)
}
```

And keep the operator impls only if you accept overflow semantics, which you should not for money.

Better:

- remove `Add` / `Sub` / `Neg` for money in V1
- use explicit checked operations
- return a typed domain error on overflow

This is a priority fix before any ledger code is added.

---

### 2.5.2 `Uuid` decoding

`Uuid` decoding from Postgres can fail at runtime.

That is already handled through `Result` in sqlx.

No issue.

---

### 2.5.3 `TenantId` parsing

`TenantId` implements:

```rust
impl FromStr for TenantId {
    type Err = uuid::Error;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        s.parse::<Uuid>().map(Self)
    }
}
```

Config uses:

```rust
std::env::var("AIMS_TENANT_ID")
    .parse::<TenantId>()
    .wrap_err("AIMS_TENANT_ID must parse as a UUID")?
```

This is correct.

---

### 2.5.4 Template rendering

`p.medicare_number.as_deref().unwrap_or("—")` is safe.

No issue.

---

## 2.6 Pool resilience

`aims_db::create_pool` is:

```rust
pub async fn create_pool(database_url: &str) -> Result<Pool, sqlx::Error> {
    PgPool::connect(database_url).await
}
```

This is minimal.

Missing resilience features:

- no explicit pool sizing
- no connection timeout
- no idle timeout
- no max lifetime
- no health-aware pool behavior
- no backpressure configuration

For V1 this may be acceptable, but for production you should configure:

```rust
PgPoolOptions::new()
    .max_connections(...)
    .min_connections(...)
    .acquire_timeout(...)
    .idle_timeout(...)
    .max_connection_lifetime(...)
```

Also, `check()` is:

```rust
pub async fn check(pool: &Pool) -> Result<(), sqlx::Error> {
    sqlx::query("SELECT 1").execute(pool).await?;
    Ok(())
}
```

This is a good startup liveness check, but it does not prove:

- the role is `aims_app`
- RLS is active
- the tenant context works
- ledger invariants hold

That gap is addressed in Section 3.

---

## 2.7 RLS enforcement details

### What is correct

- `aims_app` is non-superuser
- `aims_ops` has `BYPASSRLS`
- application code connects as `aims_app`


---
