## T04 — Id-urile cu prefix

### Pe scurt, ce am făcut (pe înțeles)

Fiecare lucru din aplicație are un nume scurt, unic: o alertă e `al-0001`, un pachet trimis spre Pământ e `pk-0001`, un check-in e `ck-0001` și așa mai departe. Până acum, funcția care dă aceste nume nu exista (arunca eroare). Acum există.

Cum merge, ca la un bon de ordine la ghișeu:
- În baza de date, în tabelul `sim_state`, ține câte un **contor** pentru fiecare tip de nume (`id:al` pentru alerte, `id:pk` pentru pachete…).
- Când cineva cere un nume nou pentru o alertă, funcția `next_id` citește contorul, îl crește cu 1, îl salvează la loc și întoarce numele formatat cu 4 cifre: `al-0001`, apoi `al-0002`, `al-0003`.
- Fiecare tip are contorul lui: dacă dai `al-0001` și apoi ceri un pachet, primești `pk-0001`, nu `pk-0002`.
- A doua funcție, `next_seq`, face același lucru, dar întoarce doar un număr (1, 2, 3…) pentru ordinea mesajelor din coada navă ↔ Pământ, separat pe fiecare direcție (`down` = navă → Pământ, `up` = Pământ → navă).

Un lucru important: contorul crește **în aceeași tranzacție** cu restul scrierii. Dacă salvarea alertei eșuează și se anulează (rollback), se anulează și creșterea contorului, deci nu rămân „găuri” în numerotare și nu se dă de două ori același nume.

### Fișiere modificate
- `backend/app/ids.py` — am scris `next_id` și `next_seq` (plus o funcție mică comună `_bump` care crește contorul); am scos comentariile în română
- `backend/tests/routers/test_ids.py` — nou, 6 teste

### Teste adăugate
- `test_next_id_counts_up_with_padding` — trei cereri dau `al-0001`, `al-0002`, `al-0003`
- `test_prefixes_have_separate_counters` — alertele și pachetele au contoare separate
- `test_counter_persists_across_sessions` — după salvare, contorul se păstrează și la următoarea cerere
- `test_rollback_does_not_advance_counter` — dacă tranzacția se anulează, contorul nu crește
- `test_next_seq_per_direction` — `down` dă 1, 2, 3, iar `up` începe separat de la 1
- `test_width_grows_past_9999` — după `9999` vine `10000` (numele se lungește, nu se taie)

### Rezultate
pytest 31 trecute / 0 picate · ruff ok · smoke ok · serverul pornește (`"db":"ok"`) · editorul: fără probleme

### Endpointuri devenite reale
niciunul (funcțiile le vor folosi T06 și taskurile de după)

### Texte rămase în română
niciunul nou (id-urile nu au text pentru frontend)

### Decizii luate singur
- Am pus un `flush()` după fiecare creștere, ca un al doilea apel în aceeași tranzacție să vadă contorul deja crescut. Commit-ul tot îl face cine apelează funcția.
- La actualizare scriu un dicționar nou (`row.value = {...}`), nu modific pe loc, altfel SQLAlchemy nu observă schimbarea (capcana din task).
- Peste 9999 numele are 5 cifre (`rj-10000`), nu dă eroare.

### Cum verific eu de mână
1. `cd backend; uv run pytest tests/routers/test_ids.py -v` → 6 teste trecute

### Mesaj de commit propus
backend: T04 id-urile cu prefix

### Următorul task
T05 (dependențele lui sunt gata: da, T03)
