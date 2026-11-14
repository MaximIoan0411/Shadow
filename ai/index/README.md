# index — indexul bazei de cunoștințe (generat, NU intră în git)

**Cine lucrează aici:** AI

`uv run python -m rag.ingest` îl reface din `corpus/docs/` și `../data/`: `chunks.json` (fragmentele, cu titlu și
URL), `vectors.npy` (vectorii lor), `meta.json` (modelul de embedding și câte fragmente are).
