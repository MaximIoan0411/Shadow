# SHADOW — modelul de amenințări

Ce apărăm, de cine și ce atacuri contează. Fiecare apărare are un fișier de cod și testul care o dovedește;
unde testul lipsește, scrie la sfârșit.

## Ce apărăm

Într-un sistem medical de bord, furtul datelor nu e cazul cel mai grav. Cazul cel mai grav e o **urgență ascunsă**
(o măsurătoare proastă făcută să pară bună) sau o **alarmă falsă** (un ordin medical care nu vine de la medic).
De aceea integritatea datelor trece înaintea secretului lor.

| Ce | De ce contează |
|---|---|
| măsurătorile | din ele pornesc toate alertele |
| mesajele navă ↔ Pământ | un răspuns medical fals ajunge direct la astronaut |
| intimitatea fiecărui membru față de colegi | cine se știe privit de colegi nu mai raportează cinstit |
| urma accesului | fiecare vede cine i-a citit datele |

## De cine

| Cine | Ce poate face |
|---|---|
| un dispozitiv defect | trimite valori greșite, cu semnătură bună; e cazul cel mai probabil |
| cineva din rețeaua navei, fără cont | trimite cereri către backend, inclusiv către `POST /ingest/measurements` |
| un coleg de echipaj, cu contul lui | cere datele altuia |
| cineva ajuns la stația comună | folosește o sesiune rămasă deschisă |
| cineva pe legătura navă–Pământ | citește, modifică sau retrimite pachete |

**În afara modelului:** cine are acces la discul sau la procesul calculatorului de bord. Acela are cheile și baza de date.

## Amenințări și apărări

Căile care încep cu `app/` și `tests/` sunt din `backend/`; celelalte, din rădăcina repo-ului.

| Amenințare | Efect | Apărarea | Cod | Test |
|---|---|---|---|---|
| măsurătoare falsificată | alarmă falsă sau urgență ascunsă | semnătură Ed25519 pe fiecare măsurătoare, cu cheia dispozitivului; un dispozitiv vorbește pentru un singur membru | `app/security/signing.py`, `app/services/security_log.py` | `tests/security/test_ingest.py` |
| senzor defect sau „înghețat” | date greșite care par bune | limite fizic posibile; aceeași valoare de 20 de ori la rând e respinsă | `app/security/validation.py` | `tests/security/test_ingest.py` |
| mesaj modificat între navă și Pământ | ordin medical fals | pachet criptat (AES-256-GCM) și semnat (Ed25519); semnătura se verifică înainte de decriptare | `app/security/sealing.py`, `app/link/scheduler.py` | `tests/security/test_sealing.py`, `tests/link/test_scheduler.py` |
| același mesaj retrimis | acțiune repetată | o măsurătoare (dispozitiv, metrică, oră) intră o singură dată; un pachet are număr de ordine unic, inclus în semnătură | `app/services/security_log.py`, `app/db/models/link.py` | `tests/security/test_ingest.py`, `tests/link/test_enqueue.py` |
| un coleg citește datele altuia | pierderea încrederii, subraportare | cont pe astronaut; rolul și `crew_id` se citesc doar din token; toate căile `/crew/{crew_id}` trec prin aceeași verificare | `app/deps.py`, `app/services/alerts.py` | `tests/security/test_auth_flow.py`, `tests/routers/test_events.py` |
| cineva șterge urmele | acces neobservat | jurnal în care fiecare intrare conține hash-ul celei dinainte; aplicația verifică lanțul și arată rezultatul | `app/security/access_log.py`, `app/services/access.py` | `tests/security/test_access_log_wiring.py` |
| token furat de pe stația comună | acces în numele altcuiva | tokenul stă doar în memoria ferestrei; deconectarea îl revocă, iar revocarea ține și după repornire; expiră în 12 ore | `app/security/tokens.py`, `frontend/src/lib/session.tsx` | `tests/security/test_auth_flow.py`, `tests/security/test_tokens_and_keys.py` |
| parolă ghicită | intrare în contul altcuiva | argon2id; 5 greșeli în 5 minute blochează contul 60 s; același răspuns pentru un cont inexistent | `app/security/passwords.py`, `app/security/lockout.py`, `app/services/auth.py` | `tests/security/test_auth_flow.py` |
| token fabricat | orice rol, fără parolă | un secret lipsă, scurt sau publicat e înlocuit la pornire cu unul aleator; tokenurile de test sunt oprite implicit | `app/config.py`, `app/security/tokens.py` | `tests/security/test_tokens_and_keys.py` |
| textul tastat ajunge în baza de date | pierderea intimității | se trimit doar timpi și clasa tastei; o cerere care conține litera e refuzată | `app/schemas.py` | `tests/routers/test_keystrokes_api.py` |
| medicul AI recomandă un medicament sau o doză | sfat medical periculos | răspunsul modelului e verificat în cod; dacă încalcă regulile, se afișează textul din catalog | `ai/service/guard.py` | `ai/eval/run_eval.py --chat` |

## Ce nu acoperă prototipul

De spus ca atare juriului.

- **Fără limită de cereri.** Cineva din rețeaua navei poate bloca un cont câte 60 s, la nesfârșit, sau poate umple lista de respingeri.
- **Jurnalul de acces:** lanțul arată o intrare modificată sau ștearsă din mijloc. Ștergerea ultimelor intrări se vede doar dacă ultimul hash e păstrat și în altă parte (de exemplu trimis Pământului în fiecare pachet).
- **Retrimiterea unui pachet** e blocată în baza de date, cu test, dar nu a fost încercată printr-un atac: legătura e simulată în același proces, deci nu există o intrare prin care un pachet vechi să sosească din afară.
- **Nava și Pământul rulează în același proces** și au amândouă cheile. Într-un sistem real fiecare parte are doar cheia ei privată și cheia publică a celeilalte.
- **Cheile private stau necriptate pe disc**, iar cheia legăturii e împărțită dinainte și nu se schimbă.
- **Baza de date nu e criptată.** După sosire, conținutul unui pachet e păstrat decriptat.
- **Fără deconectare automată.** O sesiune lăsată deschisă pe stația comună rămâne deschisă cât e fereastra deschisă, cel mult 12 ore.
- **Blocarea conturilor e ținută în memorie** și dispare la repornire.
- **Simularea și demo-ul** (`/sim/*`, `/demo/*`) pot fi pornite de orice cont, nu de un administrator. Într-un sistem real nu există.
- **Modelul AI pe Colab:** întrebarea și contextul alertei părăsesc calculatorul, printr-un tunel HTTPS cu cheie. Pe navă modelul ar rula local (modul `local`).
