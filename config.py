"""
config.py -- secrets loading and corporate-TLS handling for Fed-Taskforce.

Two jobs, both stdlib-first:
  1. Load .env into the process environment (no python-dotenv dependency).
  2. Make HTTPS verification work behind a corporate TLS-intercepting proxy by
     trusting the OS certificate store (where the proxy's root CA lives), via
     the optional `truststore` package.

Import this once at the top of any script that touches a live API. Keys are
never printed in full; the self-test masks them.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_PATH = Path(__file__).parent / ".env"


def load_dotenv(path: Path | None = None) -> None:
    """
    Parse simple KEY=VALUE lines from .env into os.environ. A non-empty value in
    .env is authoritative -- it overrides whatever is already in the environment
    (so a real key pasted into .env wins over a stale placeholder OS var). Empty
    .env lines never clobber an existing variable.
    """
    path = path or _ENV_PATH
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val:
            os.environ[key] = val


def enable_corporate_tls() -> str | None:
    """
    Trust the OS certificate store so HTTPS works behind a TLS-intercepting
    proxy (Zscaler/Netskope/etc.). Returns a label for what was enabled, or
    None if no adjustment was made.
    """
    # 1. Explicit CA bundle wins if the user set one.
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        bundle = os.environ.get(var)
        if bundle and Path(bundle).exists():
            return f"{var}={bundle}"
    # 2. Otherwise inject the OS trust store (has the corporate root CA).
    try:
        import truststore

        truststore.inject_into_ssl()
        return "truststore (OS trust store)"
    except ImportError:
        return None


def init() -> str | None:
    """Convenience: load .env then enable corporate TLS. Call at import time."""
    load_dotenv()
    return enable_corporate_tls()


def _mask(value: str | None) -> str:
    if not value:
        return "MISSING"
    return f"set (...{value[-4:]}, len {len(value)})"


if __name__ == "__main__":
    tls = init()
    print("=== Fed-Taskforce config self-test ===")
    print(f"corporate-TLS: {tls or 'no adjustment (system default certs)'}\n")

    for k in ("ANTHROPIC_API_KEY", "FRED_API_KEY", "FMP_API_KEY"):
        print(f"  {k:20} {_mask(os.environ.get(k))}")

    print("\nConnectivity probes (need the matching key set):")
    try:
        import requests
    except ImportError:
        print("  requests not installed; skipping probes")
        raise SystemExit(0)

    fred = os.environ.get("FRED_API_KEY")
    if fred:
        try:
            r = requests.get(
                "https://api.stlouisfed.org/fred/series",
                params={"series_id": "PCEPILFE", "file_type": "json", "api_key": fred},
                timeout=20,
            )
            print(f"  FRED/ALFRED : HTTP {r.status_code} "
                  f"({'OK' if r.ok else r.text[:80]})")
        except Exception as e:
            print(f"  FRED/ALFRED : {type(e).__name__}: {str(e)[:90]}")
    else:
        print("  FRED/ALFRED : skipped (no FRED_API_KEY)")

    fmp = os.environ.get("FMP_API_KEY")
    if fmp:
        try:
            # Exercise the SAME endpoint data_real.py uses (the current "stable"
            # API), not the retired v3 path.
            r = requests.get(
                "https://financialmodelingprep.com/stable/treasury-rates",
                params={"from": "2024-01-02", "to": "2024-01-05", "apikey": fmp},
                timeout=20,
            )
            print(f"  FMP         : HTTP {r.status_code} "
                  f"({'OK' if r.ok else r.text[:80]})")
        except Exception as e:
            print(f"  FMP         : {type(e).__name__}: {str(e)[:90]}")
    else:
        print("  FMP         : skipped (no FMP_API_KEY)")
