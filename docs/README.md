# Script Documentation Index

This folder contains one README-style document per script in `src/`.

**Start here for the full pipeline:** [clean_pipeline.md](clean_pipeline.md)  
**Audit then clean (batch workflow):** [audit_clean_workflow.md](audit_clean_workflow.md)  
**Authoritative behavior rules:** [README_DATA_CLEAN_POLICY.md](../README_DATA_CLEAN_POLICY.md)

- `audit_clean_workflow.md`: recommended audit → clean steps and behavior comparison table
- `clean_pipeline.md`: end-to-end clean flow, report sheets, common scenarios
- `main.md`: pipeline entrypoint and runtime flow
- `reader.md`: standard CSV parsing and YAML rule loading/generation
- `file_matcher.md`: raw-to-standard file matching
- `header_detector.md`: header row scoring and detection
- `cleaner.md`: value-level cleaning logic
- `validator.md`: type conversion and status derivation
- `exporter.md`: cleaned CSV export and Excel reporting
- `utils.md`: shared helpers
- `types.md`: dataclass contracts
- `__init__.md`: package marker note
