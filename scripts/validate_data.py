"""Verifică fișierele din data/ față de contract (backend/app/datafiles.py).

    uv run --project backend python scripts/validate_data.py [folderul-data]

Afișează „OK” sau lista TUTUROR problemelor, cu fișierul și câmpul.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.datafiles import DataError, load_all  # noqa: E402

try:
    b = load_all(sys.argv[1] if len(sys.argv) > 1 else None)
except DataError as e:
    print(e)
    sys.exit(1)
print(f"OK: {len(b.params.by_id())} parametri ({len(b.params.key_threshold_ids())} praguri cheie), "
      f"{len(b.catalog.recommendations)} recomandări, {len(b.checkin.indicators)} câmpuri de check-in, "
      f"{len(b.environments.environments)} medii, {len(b.scenario.events)} evenimente în scenariu")
