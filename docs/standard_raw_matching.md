# Standard ↔ Raw filename matching (reference table)

`normalize_token` strips trailing `_r<digits>`, then trailing `_YYYYMMDD` or `_YYYYMMDD_YYYYMMDD`, lowercases, and normalizes underscores.

## Auto-match (no extra YAML)

These raw basenames normalize to the same token as the standard file (after version/date strip):

| Standard | Raw example |
|----------|-------------|
| `BA_CVA_Allocation_r20260217.csv` | `BA_CVA_ALLOCATION_20241031_20250527.csv` |
| `Book_Sensitivities_r20260205.csv` | `BOOK_SENSITIVITIES_20241031_20250411.csv` |
| `MRC_Book_Reallocated_r20260205.csv` | `MRC_BOOK_REALLOCATED_20260227_20260312.csv` |
| `Netting_Impact_r20251224.csv` | `NETTING_IMPACT_20260227_20260330.csv` |
| `SA_CVA_Allocation_r20260217.csv` | `SA_CVA_ALLOCATION_20241031_20250821.csv` |
| `T_COLL_r20260219.csv` | `T_COLL_20260227_20260309.csv` |
| `T_DER_EAD_r20260219.csv` | `T_DER_EAD_20260227_20260309.csv` |
| `T_NETSET_r20260219.csv` | `T_NETSET_20260331_20260415.csv` |
| `T_SFT_EAD_r20260219.csv` | `T_SFT_EAD_20260227_20260309.csv` |
| `T_TRADE_RWA_r20260219.csv` | `T_TRADE_RWA_20260331_20260415.csv` |

## Needs `raw_prefix_to_standard` (raw prefix → exact standard filename key under `rules`)

| Prefix (raw basename starts with) | Standard file |
|-----------------------------------|----------------|
| `DESK_STANDALONE_RWA_` | `Desk_RWA_r20260205.csv` |
| `MRC_BOOK_STANDALONE_RWA_` | `MRC_Book_RWA_r20260205.csv` |
| `MRC_BUSINESS_LINE_STANDALONE_RWA_` | `MRC_BL_RWA_r20260205.csv` |
| `SACVA_SENSITIVITY_PREAGGREG_BNS_EXCL_GT_` | `SACVA_Sensitivity_BNS_r20260217.csv` |
| `SACVA_SENSITIVITY_PREAGGREG_ENTERPRISE_` | `SACVA_Sensitivity_ENT_r20260217.csv` |
| `V_SFT_NETSEC_NS_` | `V_SFT_NETSEC_r20260219.csv` |
| `V_SFT_NFX_IN_OUT_` | `V_SFT_NFX_r20260219.csv` |

Longer prefixes are matched first in code, so `SACVA_SENSITIVITY_PREAGGREG_BNS_EXCL_GT_` does not collide with `SACVA_SENSITIVITY_PREAGGREG_ENTERPRISE_`.

## Optional `aliases` (BNS / ENT)

- **BNS**: alias `SACVA_SENSITIVITY_PREAGGREG_BNS_EXCL_GT` (no trailing `_`) matches raw after date strip; prefix above is optional redundancy.
- **ENT**: alias `SACVA_SENSITIVITY_PREAGGREG_ENTERPRISE` recommended in addition to prefix.

## Skipped inputs (not CSV pipeline)

- `GBM_Attributed_Capital.csv` / `GBM_Daily_Transmission.csv` — raw `.xlsx`; pipeline skips with `skipped_xlsx`.

## When you bump standard filenames (`_r20260205` → `_r20260309`)

Update the **value** side of `raw_prefix_to_standard` (and any `mappings`) to the new standard filename under `rules`, and keep the same **prefix** keys if raw naming is unchanged.

## Placeholder standard CSVs

Some standards in `standards/` may still use generic columns (`Col_A`, `Col_B`, `Col_C`) so that `rules` keys exist and prefixes resolve. Replace those files with real row-1 / row-2 standard definitions when available, then run `python -m src.reader --base-dir .` to refresh inferred types (merge preserves `mappings`, prefixes, and merged `aliases`).
