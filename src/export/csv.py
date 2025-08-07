@validate_io
@sensor("export")
def run(db_path: Path = Path("yachts.duckdb")) -> Path:
    """Write **exports/yachts.csv** and return its Path."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = _select_from_yachts(db_path) if db_path.exists() else pd.DataFrame(columns=REQUIRED)

    if df.empty:
        df = _load_json_fallback()

    # Ensure schema & order
    df = df.reindex(columns=REQUIRED)
    df["name"] = df["name"].astype(str)
    df["length_m"] = pd.to_numeric(df["length_m"], errors="coerce")

    # Drop rows with nulls in required columns
    df = df.dropna(subset=REQUIRED)
    # Fill remaining nulls
    df["name"] = df["name"].fillna("Unknown")
    df["length_m"] = df["length_m"].fillna(0)

    df.to_csv(CSV_PATH, index=False)
    log.info("wrote %d rows → %s", len(df), CSV_PATH)
    return CSV_PATH
