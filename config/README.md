# Config guide (`config/file_rules.yaml`)

This project is driven by `config/file_rules.yaml`. Both **audit** and **data clean** load it to determine:

- how to read raw files (encoding/delimiter/skiprows)
- which standard schema applies to each raw file
- per-column types and date formats

## Quick rules of thumb

- If you have **new standards** (new domains / new column sets): add them under `standards/` and regenerate/merge YAML via `src.reader`.
- If you only have **new raw files** that belong to an existing standard: update matching (`mappings` or `raw_prefix_to_standard`) so the new files map to an existing rule.

## YAML structure (high level)

- **`defaults`**: global read options used when a rule does not override them.
  - `encoding` (e.g. `utf-8`, `latin1`)
  - `delimiter` (usually `,`)
  - `skiprows` (fixed pre-header lines upstream sometimes add)
- **`header_match_threshold`**: header detection match ratio (default `0.6`).
- **`mappings`**: explicit raw → standard mapping (highest priority).
  - Keys are either `filename.csv` **or** a raw path under `raw/` (use forward slashes), e.g. `teamA/foo.csv`.
  - Value is a key under `rules` (a standard filename), e.g. `Desk_RWA_r20260205.csv`.
- **`raw_prefix_to_standard`**: raw filename prefix → standard rule (good for changing date suffixes).
  - Example: `DESK_STANDALONE_RWA_: Desk_RWA_r20260205.csv`
- **`rules`**: standard schemas. One entry per standard file.
  - `aliases`: additional names that can match by token normalization
  - `read`: per-standard read overrides (encoding/delimiter/skiprows)
  - `columns`: list of column rules:
    - `name`
    - `type` (`int`, `float`, `date`, `string`)
    - `date_format` (required for strict date expectations; e.g. `'%Y-%m-%d'`)

## Matching precedence (what wins)

When the pipeline tries to match a raw file to a rule, it checks in this order:

1. **`mappings`** by relative path under `raw/` (e.g. `teamA/foo.csv`)
2. **`mappings`** by raw filename only (e.g. `foo.csv`)
3. **`raw_prefix_to_standard`** (longest prefix wins)
4. **`rules[*].aliases` / standard filename** token match (weakest; best-effort)

If matching is ambiguous or unstable, prefer **`raw_prefix_to_standard`** or **`mappings`**.

## Recommended update workflows

### A) You have new standards

1. Add/update standard CSVs under `standards/` (row 1 = column names, row 2 = sample values).
2. Regenerate/merge YAML:

```bash
python -m src.reader --base-dir .
```

Notes:
- Default behavior **merges** into existing YAML, preserving your manual `mappings` and `raw_prefix_to_standard`.
- Use `--no-merge` only if you want a clean rebuild (you will need to re-add mappings/prefixes).

### B) You have new raw files that should use an existing standard

Pick one:

- **Use `raw_prefix_to_standard`** when filenames differ only by dates/suffixes.
- **Use `mappings`** when filenames are inconsistent or when the same filename appears in multiple subfolders.

After updating YAML:

```bash
python -m audit.main --base-dir .
python -m src.main --base-dir .
```

## Audit vs data clean behavior (important)

- **Audit**: requires `file_rules.yaml`. If a raw file does **not** match a rule, audit still runs **file-level** checks only.
- **Data clean**: if a raw file does **not** match a rule, it is reported as **failed** (`No matching standard rule`).

## Common troubleshooting

- **Header not found**
  - Increase `header_match_threshold` sensitivity (lower threshold) only if truly needed.
  - Or fix `skiprows` / delimiter / encoding so the preview reads correctly.
- **Wrong standard matched**
  - Add an explicit `mappings` entry (path-level mapping is the most reliable).
- **Files in deeper raw nesting**
  - The pipeline scans `raw/*` and `raw/*/*` only. Files deeper than one subfolder are ignored by design.

