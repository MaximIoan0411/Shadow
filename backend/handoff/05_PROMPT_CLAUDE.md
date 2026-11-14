# 05 — Promptul pentru Claude (copiază-l la începutul fiecărui task)

Înlocuiește `Txx` cu taskul și atașează fișierele indicate.

---

Lucrez la backend-ul SHADOW (NASA Space Apps 2026), un prototip FastAPI + SQLAlchemy asincron + SQLite.
Îți atașez:

1. `01_CONTEXT.md` — proiectul, arhitectura și regulile obligatorii;
2. `tasks/Txx-….md` — **singurul** task pe care îl facem acum;
3. fișierele din repo listate la „De citit” în task.

Te rog:

- **Implementează doar taskul Txx.** Nu începe alte taskuri, nu „îmbunătăți” alte fișiere, nu redenumi nimic.
- **Nu schimba contractul:** căile, parametrii și `response_model` ale routerelor, modelele din `app/schemas.py`,
  `app/ai_schemas.py`, `app/datafiles.py` și semnăturile din `app/security/`. Dacă taskul pare să ceară asta,
  oprește-te și spune-mi.
- Respectă regulile din `01_CONTEXT.md`: asincron peste tot, `clock.now()` în loc de `datetime.now()`,
  `selectinload` în loc de încărcare leneșă, evenimentele după commit, textele pentru utilizator în română.
- Scrie testele cerute la „Gata când”, în fișierele indicate.
- Dacă îți lipsește un fișier ca să fii sigur, **cere-l**; nu ghici conținutul lui.
- La sfârșit, dă-mi: lista fișierelor schimbate, comenzile de rulat pentru verificare și orice decizie pe care ai
  luat-o singur (pe scurt).

---

**Dacă Claude dă o eroare pe care nu o înțelegi:** lipește eroarea completă și fișierul în care apare. Nu-i cere
să „rescrie tot”.

**Dacă taskul a ieșit prea mare:** cere-i să se oprească după pasul la care a ajuns, faci PR cu ce merge și
continui într-o conversație nouă cu același task, spunând unde ați rămas.
