# data — datele comune

**Cine lucrează aici:** backend (le încarcă), AI (catalogul și sursele); oricine propune corecturi

Conținut, fără cod: pragurile cu sursele lor, catalogul de recomandări, textele, mediile, evenimentul solar real,
scenariul misiunii. Formatul fiecărui fișier și regulile: `../contract/data/README.md`.

```bash
uv run --project backend python scripts/validate_data.py     # „OK” sau lista problemelor
```

Schimbările de **conținut** (un text, un prag cu sursa lui) se pot face oricând. Schimbările de **format** se
anunță: opresc pornirea backend-ului.
