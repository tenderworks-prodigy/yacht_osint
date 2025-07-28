# Changelog

## [Unreleased]
- Pin all Python dependencies for reproducible installs.
- Added ruff and black formatting checks in CI.
- Implemented DuckDB persistence and CSV exporter.
- Added rclone upload with retry logic and data quality reporting.
- Introduced Google Sheets sync module with tests.
- CI pipeline now runs scraping modules and exports results.
- Secrets are loaded from `.env` via `python-dotenv`.
