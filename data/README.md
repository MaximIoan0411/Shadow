# data — datele comune

**Cine lucrează aici:** backend (le încarcă), AI (catalogul și sursele); oricine propune corecturi

Conținut, fără cod: pragurile cu sursele lor, catalogul de recomandări, textele, mediile, evenimentul solar real,
scenariul misiunii. Formatul fiecărui fișier și regulile: `../contract/data/README.md`.

```bash
uv run --project backend python scripts/validate_data.py     # „OK” sau lista problemelor
```

**Limba:** textele care apar în aplicație (nume, explicații, unități, recomandări, pași, check-in, medii) sunt în
**engleză**, ca interfața. Cheile, id-urile și valorile fixe (`VERIFICAT`, `derivat`, `1_singur`…) rămân cum sunt,
fiindcă le citește codul. Notițele de cercetare (`verificat_cum`, `nota_derivare`, `corecturi_plan`,
`catalog_recomandari_texte.md`) rămân în română: nu apar pe ecran.

Schimbările de **conținut** (un text, un prag cu sursa lui) se pot face oricând. Schimbările de **format** se
anunță: opresc pornirea backend-ului.
