## T30 — Reverificarea alertelor

### Pe scurt, ce am făcut (pe înțeles)

Fiecare alertă are o dată de reverificare (`recheck_at`, peste 1–3 zile, din catalog): momentul în care SHADOW se uită dacă planul a funcționat. Acum chiar se uită:
- **Valorile au revenit la normal** → alerta se **închide singură**, iar în istoric apar „rechecked” și „resolved” de „SHADOW”, cu nota „Values back to normal.”
- **Valorile sunt tot peste prag** → alerta **urcă un nivel** (cel mult 3) și primește o nouă dată de reverificare; în istoric apare „rechecked” cu „Still above the threshold: moved to level N.” La nivelul 3 pleacă singură spre Pământ (pachetul de la T23).
- **Nu au venit date noi** (de exemplu nimeni n-a mai tastat de când a apărut alerta) → **nu se întâmplă nimic**; se verifică din nou mai târziu. Lipsa datelor nu înseamnă „e bine”.

Pentru fiecare pilon se folosește regula lui: Santinela (pulsul de noapte al zilei), Tastatura (o sesiune de tastare nouă), Inima (scorul zilei), alertele de mediu (dacă semnalul slab mai e prezent), radiațiile (dacă furtuna a trecut sub prag). Un task din fundal verifică **la fiecare 5 secunde reale**; evenimentele `alert.updated` pleacă după salvare.

Reverificarea rulează și **în replay-ul de la pornire**: alertele de somn din ziua 40 au fost reverificate în ziua 41 (încă somn scurt → nivelul 2) și în ziua 42 (somnul a revenit → închise).

**Verificat pe serverul pornit:** după ce ceasul misiunii a trecut de 07:17 (ora reverificării alertei de tastare a lui `cm-2`), alerta a rămas deschisă, corect, pentru că nu au venit sesiuni noi de tastare.

### Fișiere modificate
- `backend/app/services/pipeline.py` — `recheck_due` și verdictul pe pilon (`_recheck_verdict`); reverificarea în replay
- `backend/app/services/alerts.py` — `recheck_loop` (bucla de 5 s)
- `backend/app/main.py` — bucla pornește cu celelalte taskuri din fundal
- `backend/tests/routers/test_recheck.py` — nou, 4 teste

### Teste adăugate
- `test_values_back_to_normal_resolve_the_alert` — pulsul de noapte revine la normal → alerta se închide, cu „rechecked” + „resolved” de SHADOW
- `test_values_still_high_move_the_alert_up_one_level` — valori tot mari → nivelul 3, dată nouă de reverificare, pachet spre Pământ; a doua rulare nu mai face nimic
- `test_no_new_data_waits` — fără date noi, alerta de tastare rămâne deschisă
- `test_not_due_is_left_alone` — alertele care nu au ajuns la data reverificării nu se ating

### Rezultate
pytest **247 trecute / 0 picate** · ruff ok · **smoke OK** · serverul pornit de 2 ori la rând (`1.76 s` / `1.90 s`), fără erori; tabloul de bord 161–199 ms · editorul: fără probleme

### Endpointuri devenite reale
- închiderea și escaladarea automată la `recheck_at` (vizibile în `GET /api/v1/alerts/{id}` și prin SSE `alert.updated`)

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **„Fără date noi” = așteaptă**, nu „închide”; altfel alerta de tastare a lui `cm-2` s-ar fi închis singură în demo la 07:17.
- **Radiațiile** nu urcă nivelul la reverificare (nivelul 3 îl dă doza acumulată, T26); se închid când furtuna trece sub prag.
- Alerta imunitară a lui `cm-2` se reverifică în ziua 97 (după escaladarea din ziua 95); dacă pulsul e încă mare, urcă la nivelul 3 și pleacă spre Pământ.

### Cum verific eu de mână
1. `uv run pytest tests/routers/test_recheck.py -v`
2. `GET /api/v1/alerts/<o alertă din ziua 40>` → istoricul: created, rechecked, rechecked, resolved

### Mesaj de commit propus (comun pentru T28, T29 și T30)
backend: T28, T29, T30 pilonul Încărcarea și exercițiile; semnalele încrucișate și cauza de mediu; reverificarea automată a alertelor

### Următoarele taskuri
T31 și T32 (dependențele lor sunt gata: da — T17 pentru T31; T08 și T16 pentru T32)
