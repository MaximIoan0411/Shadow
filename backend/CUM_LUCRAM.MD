# Cum lucrăm la un task

Regulile pentru Claude Code la fiecare task din `backend/handoff/tasks/`.
Eu îți spun doar numărul taskului (de exemplu „T07"). Tu urmezi pașii de mai jos, în ordine.

## Limite

- Faci UN SINGUR task: cel pe care ți l-am spus. Nu începi altul și nu „îmbunătățești" alte fișiere.
- Lucrezi doar în `backend/`. Nu modifici `frontend/`, `ai/`, `security/`, `contract/`, `data/`.
- Nu schimbi contractul: căile, parametrii și `response_model` ale routerelor, `app/schemas.py`,
  `app/ai_schemas.py`, `app/datafiles.py`, semnăturile din `app/security/`.
  Dacă taskul pare să ceară asta, te oprești și îmi spui.
- Nu faci `git commit` și nu faci `git push`. Le fac eu.
- Dacă îți lipsește un fișier sau o informație, întrebi. Nu ghicești.

## Limba: tot ce ajunge la frontend e în ENGLEZĂ

Livrăm în engleză. Regula aceasta are prioritate față de `01_CONTEXT.md` și față de fișierele
de task, care cer texte în română.

- Orice text pe care îl scrii tu și care ajunge într-un răspuns API sau într-un eveniment live
  e în engleză: titluri și explicații de alerte, pași de plan, mesaje de eroare (`ApiError`),
  etichete, explicații de câmpuri, mesaje de respingere, note din istoric.
- Codul, numele câmpurilor, valorile enum și codurile de eroare sunt deja în engleză; nu le schimba.
- Textele deja existente în română în fișierele pe care le modifici în acest task (inclusiv
  răspunsurile mock din router) le traduci în engleză. Nu traduci fișiere pe care taskul nu le atinge.
- Textele care vin din `data/` (catalogul de recomandări, `texts/`, `parameters.json`) NU le traduci
  în cod și nu modifici `data/`. Le transmiți așa cum sunt și le treci în raport la „Texte rămase în română".
- Dacă un test existent verifică un text în română pe care l-ai tradus, actualizezi testul la textul
  în engleză și menționezi asta în raport.
- Comentariile, log-urile și documentele interne pot rămâne în orice limbă; nu pierde timp cu ele.

## Pasul 1 — Înainte să scrii cod

Citește `backend/handoff/01_CONTEXT.md`, fișierul taskului și fișierele de la „De citit".
Verifică dacă dependențele taskului sunt făcute (funcțiile lor nu mai aruncă `NotImplementedError`).
Dacă o dependență lipsește, te oprești și îmi spui care.

Apoi scrie-mi, în maximum 8 rânduri:

- **Ce face taskul**, pe înțelesul meu, într-o propoziție sau două.
- **Fișierele** pe care le vei modifica.
- **Testele** pe care le vei adăuga.
- **Riscuri sau neclarități**, dacă există.

După acest rezumat continui direct cu implementarea, fără să aștepți confirmare,
în afară de cazul în care ai o neclaritate care schimbă soluția.

## Pasul 2 — Implementarea

- Respectă regulile din `01_CONTEXT.md`: asincron peste tot, `clock.now()` în loc de `datetime.now()`,
  `selectinload` în loc de încărcare leneșă, evenimentele după commit, pragurile din `parameters.json`.
- Textele pentru utilizator în engleză (vezi secțiunea „Limba").
- Scrie testele cerute la „Gata când", în fișierele indicate în task.

## Pasul 3 — Verificarea

Rulează și arată-mi rezultatul fiecărei comenzi:

```bash
cd backend
uv run ruff format && uv run ruff check --fix
uv run pytest -q
cd .. && uv run --project backend python scripts/smoke.py
```

Dacă ceva pică, repară și rulează din nou. Nu declara taskul gata cu teste picate.
Nu șterge și nu slăbi un test ca să treacă; dacă un test pare greșit, spune-mi.

## Pasul 4 — Raportul final

Încheie mereu cu exact acest format:

```
## Txx — <titlul taskului>

**Ce s-a făcut:** 2–4 propoziții, pe înțeles.

**Fișiere modificate:**
- cale/fișier.py — ce s-a schimbat, într-un rând

**Teste adăugate:**
- cale/test_x.py::nume_test — ce verifică, într-un rând

**Rezultate:** pytest X trecute / Y picate · ruff ok/nu · smoke ok/nu

**Endpointuri devenite reale:** lista lor, sau „niciunul"

**Texte rămase în română:** ce texte vizibile la frontend sunt încă în română și din ce fișier vin, sau „niciunul"

**Decizii luate singur:** ce ai ales și de ce, sau „niciuna"

**Cum verific eu de mână:** 1–3 pași concreți (o comandă curl sau ce deschid în /docs)

**Mesaj de commit propus:** backend: Txx <titlu scurt>

**Următorul task:** Tyy (dependențele lui sunt gata: da/nu)
```

## Pasul 5 — Jurnalul

Adaugă raportul final de la pasul 4 la sfârșitul fișierului `JURNAL.md` din rădăcina proiectului
(îl creezi dacă nu există). Nu modifica intrările mai vechi.

## Dacă taskul e prea mare

Oprește-te după ultimul pas care funcționează și are teste verzi, scrie raportul cu ce s-a făcut
și listează clar ce a rămas. Continuăm într-o conversație nouă.