# 00 — Citește întâi: predarea backend-ului SHADOW

Acest folder e făcut ca să-l dai **unei alte instanțe de Claude** (sau să-l citești tu), un task pe rând.
Fiecare fișier e independent: conține tot contextul de care are nevoie taskul lui.

## Ce e aici

| Fișier | Ce conține | Când îl dai lui Claude |
|---|---|---|
| `01_CONTEXT.md` | proiectul, arhitectura, regulile de cod asincron, convențiile | **la fiecare task** |
| `02_CONTRACT_ENDPOINTS.md` | toate cele 57 de endpoint-uri, compact: roluri, cerere, răspuns, erori, taskul fiecăruia (generat) | la taskurile cu endpoint-uri |
| `03_BAZA_DE_DATE.md` | cele 16 tabele, coloanele, cheile, indecșii (generat din modele) | la taskurile care scriu sau citesc din bază |
| `04_SCHELET.md` | fiecare fișier din `backend/`, ce face, dacă e gata / mock / schelet și taskul lui (generat) | la primul task și când te pierzi |
| `05_PROMPT_CLAUDE.md` | mesajul de dat lui Claude la începutul fiecărui task | **la fiecare task** |
| `tasks/T00-…` … `tasks/T34-…` | câte un task mic: ce faci, pașii, fișierele, criteriile de acceptare, capcanele | **unul singur pe rând** |

## Cum lucrezi, pe fiecare task

1. Alegi următorul task din tabelul de mai jos (dependențele lui trebuie să fie gata).
2. Creezi ramura: `git switch -c be/T14-nightsignal`.
3. Deschizi o conversație nouă cu Claude și îi dai, în ordine: `05_PROMPT_CLAUDE.md`, `01_CONTEXT.md`,
   fișierul taskului și fișierele listate la „De citit” în task (din repo).
4. Claude implementează **doar** taskul. Rulezi comenzile din „Gata când”.
5. PR mic, titlul `backend: T14 regula NightSignal`; celălalt îl citește în cel mult 10 minute; squash merge.
6. Bifezi taskul în tabel (sau în issue-ul echipei).

**Regula de aur:** se schimbă doar **corpul** funcțiilor din routere. Calea, parametrii, modelele din
`app/schemas.py` și forma erorilor rămân (sunt contractul cu frontend-ul). Mock-ul merge până la ultimul task,
deci frontend-ul nu se strică niciodată.

## Ordinea și împărțirea

**A** = Backend A (fundație, cereri, coadă) · **B** = Backend B (simulator, motor, piloni). Prioritate: P0 = fără
el nu merge demo-ul, P1 = dacă e gata până la ora 16, P2 = bonus.

| Task | Titlu | Cine | Prio | Depinde de | Ora țintă |
|---|---|---|---|---|---|
| T00 | Pornire și verificare | A+B | P0 | — | 0:00 |
| T01 | Setările | A | P0 | T00 | 0:15 |
| T02 | Ceasul misiunii (SimClock) | A | P0 | T00 | 0:30 |
| T03 | Baza de date la pornire | A | P0 | T01 | 1:00 |
| T04 | Id-urile cu prefix | A | P0 | T03 | 1:15 |
| T05 | Datele din `data/` la pornire | B | P0 | T03 | 1:00 |
| T06 | Seed: echipaj și conturi | A | P0 | T03, T04 | 1:45 |
| T07 | Autentificarea reală | A | P0 | T06 | 2:45 |
| T08 | Jurnalul de acces | A | P1 | T07 | 3:15 |
| T09 | Misiunea și mediile | A | P0 | T02, T05 | 3:45 |
| T10 | Simulatorul: generatorul de scenariu | B | P0 | T05 | 2:30 |
| T11 | Seed: istoricul zilelor 1–96 | B | P0 | T06, T10 | 3:15 |
| T12 | Motor: baseline-ul personal | B | P0 | T05 | 3:45 |
| T13 | Interogările refolosite (repos) | B | P0 | T11 | 4:15 |
| T14 | Pilonul Santinela (NightSignal) | B | P0 | T12, T13 | 5:00 |
| T15 | Motor: triajul | B | P0 | T14 | 5:30 |
| T16 | Drumul unei date + replay la pornire | B | P0 | T15 | 6:15 |
| T17 | Alertele: endpoint-urile reale | A | P0 | T16 | 7:15 |
| T18 | Check-in și decalajul de percepție | A | P0 | T16 | 6:30 |
| T19 | Tastarea | B | P0 | T16 | 7:15 |
| T20 | Testul de reacție (PVT-B) | B | P1 | T19 | 8:00 |
| T21 | Tablou de bord, panouri, derulator | A | P0 | T17, T18 | 9:00 |
| T22 | Evenimentele live | A | P0 | T16 | 9:45 |
| — | **Integrare cu frontend-ul** | toți | — | T21, T22 | **10:00** |
| T23 | Coada: crearea pachetelor | A | P0 | T17 | 11:00 |
| T24 | Coada: planificatorul | A | P0 | T23 | 12:00 |
| T25 | Radiații: generator, detector, adăpost | B | P1 | T16 | 11:30 |
| T26 | Furtuna: avertizarea DONKI prin coadă | B | P1 | T24, T25 | 13:30 |
| T27 | Pilonul Inima | B | P1 | T16 | 12:30 |
| T28 | Pilonul Încărcarea + exerciții | B | P1 | T16 | 14:30 |
| T29 | Semnale încrucișate + cauza de mediu | B | P1 | T16 | 15:30 |
| T30 | Reverificarea alertelor | B | P2 | T17 | 16:00 |
| T31 | Puntea către medicul AI | A | P1 | T17 | 13:00 |
| T32 | Măsurători de la dispozitive, respingeri, dovezi | A | P1 | T08, T16 | 14:30 |
| T33 | Demo: reset, salt de zi, atacuri | A | P0 | T24 | 16:00 |
| T34 | Scoaterea mock-ului și verificarea finală | A+B | P0 | toate | 17:00 |

**Dacă la ora 12 sunteți în urmă, se taie în ordinea:** T27 → proiecția din T28 → T30 → T26 → saltul de zi din T33.
**Nu se taie:** T14, T18, T23–T24, T07, pachetul falsificat din T33.

## Fișierele de predare se regenerează

`02`, `03` și `04` sunt generate din cod. După ce schimbi routere, modele sau adaugi fișiere:

```bash
uv run --project backend python scripts/build_handoff.py
```
