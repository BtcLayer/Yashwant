import os
import shutil


HEADER_MAP = {
    'historical_trades_btc.csv': [
        "Account", "Coin", "Execution Price", "Size Tokens", "Size USD", "Side",
        "Timestamp IST", "Start Position", "Direction", "Closed PnL",
        "Transaction Hash", "Order ID", "Crossed", "Fee", "Trade ID", "Timestamp"
    ],
    'ohlc_btc_5m.csv': [
        "timestamp", "symbol", "open", "high", "low", "close", "volume",
        "hl_range", "oc_range", "typical_price", "weighted_price", "true_range",
        "body_size", "upper_shadow", "lower_shadow", "vwap_component",
        "direction", "price_change", "price_change_pct", "range_pct", "datetime_str"
    ],
    'funding_btc.csv': [
        "timestamp", "symbol", "funding_rate", "premium"
    ],
}


def ensure_header(csv_path: str, header_cols: list) -> bool:
    """Ensure CSV has the exact header row. If missing, prepend it safely.

    Returns True if a change was made, False otherwise.
    """
    if not os.path.exists(csv_path):
        return False

    expected = ",".join(header_cols) + "\n"

    # Read the first 256 bytes to check if header exists
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        first_line = f.readline()
        if first_line.strip() == ",".join(header_cols):
            return False  # already has correct header

    # Prepend header using a temporary file for safety
    tmp_path = csv_path + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8', newline='') as out_f:
        out_f.write(expected)
        with open(csv_path, 'r', encoding='utf-8', newline='') as in_f:
            shutil.copyfileobj(in_f, out_f)

    # Replace the original file
    os.replace(tmp_path, csv_path)
    return True


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    changed = []
    for fname, header in HEADER_MAP.items():
        path = os.path.join(root, fname)
        try:
            if ensure_header(path, header):
                changed.append(fname)
        except Exception as e:
            print(f"Error fixing {fname}: {e}")

    if changed:
        print("Headers added to:", ", ".join(changed))
    else:
        print("All CSV headers present; no changes made.")


if __name__ == "__main__":
    main()
