## T17 — Alertele: endpoint-urile reale

> **Actualizare (la începutul T18): smoke trece din nou.** Ai mers mai departe fără să alegi, așa că am aplicat varianta recomandată (1): `scripts/smoke.py` caută acum alertele reale înainte de exemple (`al-1042` → alerta imunitară a lui `cm-2`; `al-1039` → o alertă activă de nivel 1 a lui `cm-2`, creată de smoke prin codul backend-ului până când T19 o produce pe cea reală). Am redenumit `pipeline._create` în `pipeline.create_alert` (public), ca smoke să nu folosească o funcție privată. Detalii în `jurnal_task_T18.md`.
>
> ~~Stare: implementat, testele trec, dar `smoke.py` PICĂ — aștept decizia ta (vezi „De ce pică smoke”).~~

### Pe scurt, ce am făcut (pe înțeles)

Până acum, ecranele cu alerte arătau alerte inventate, scrise de mână în mock (`al-1042`, `al-1039`). De la T16, alertele adevărate le produce motorul și stau în baza de date (de exemplu `al-0001`, alerta imunitară a lui `cm-2`). Acum **toate endpoint-urile de alerte lucrează cu baza de date**:

- **Lista alertelor unui astronaut** (`GET /crew/{id}/alerts`): cele nerezolvate, cele mai grave primele; se poate filtra după stare și pilon. Ofițerul medical vede la ceilalți doar alertele de nivel 2 și 3.
- **Coada ofițerului medical** (`GET /cmo/queue`): toate alertele de nivel 2 și 3 nerezolvate, din tot echipajul.
- **Alerta completă** (`GET /alerts/{id}`): dovezile, recomandarea din catalog cu sursa ei, planul de pași, data reverificării, istoricul. Citirea de către ofițerul medical se scrie în jurnalul de acces (T08).
- **„Am văzut”** (`ack`): doar dintr-o alertă „active”; altfel 409. Se scrie în istoric.
- **Bifarea unui pas** din plan: se salvează cu ora; în istoric apare `step_done`.
- **Escaladarea**: astronautul poate trimite la ofițerul medical (nivel 2), dar nu pe Pământ (nivel 3 → 403); nivelul nu coboară (409). Pachetul spre Pământ de la nivelul 3 vine la T23.
- **Închiderea**: astronautul închide doar alertele de nivel 1; pe cele de nivel 2 și 3 le închide ofițerul medical. „Monitoring” lasă alerta deschisă și mută reverificarea cu o zi.
- **Catalogul de recomandări** vine din `data/catalog/recommendations.json`, nu din mock.

După fiecare acțiune, alerta se **salvează** și abia apoi se trimite evenimentul live `alert.updated` către frontend.

### Fișiere modificate
- `backend/app/services/alerts.py` — scrise toate operațiile (listă, coadă, detaliu, ack, pas, escaladare, închidere, catalog) și transformarea alertei din bază în forma din contract; `recheck_loop` rămâne schelet pentru T30
- `backend/app/routers/alerts.py` — endpoint-urile apelează serviciul; nu mai folosesc mock-ul
- `backend/tests/routers/test_alerts_api.py` — nou, 9 teste
- `backend/tests/security/test_access_log_wiring.py` — testul meu de la T08 deschidea alerta mock `al-1042`; acum caută id-ul alertei reale (aceeași verificare)

### Teste adăugate
- `test_list_and_detail_come_from_database` — lista și detaliul vin din bază: alerta imunitară, nivel 2, recomandarea `immune-2-1`, pașii, istoricul, dovezile
- `test_cmo_queue_and_level_filter` — coada ofițerului are doar nivel ≥ 2; el nu vede alertele de nivel 1 ale altora; filtrul `topic` merge
- `test_full_flow_ack_step_escalate_resolve` — tot firul: ack (al doilea ack → 409) → pas bifat → escaladare la 2 de astronaut → la 3 astronautul primește 403, ofițerul reușește → închiderea: astronautul 403, ofițerul reușește; istoricul are toți pașii cu numele fiecăruia; 5 evenimente `alert.updated`
- `test_level_cannot_go_down` — escaladare la același nivel → 409
- `test_ack_on_escalated_alert_is_409` — ack pe alertă escaladată → 409
- `test_monitoring_moves_recheck_by_one_day` — „monitoring” mută reverificarea și nu închide alerta
- `test_other_crew_and_unknown_alert` — alt astronaut sau Pământul → 403; alertă inexistentă → 404; pas inexistent → 404
- `test_catalog_comes_from_data` — catalogul vine din `data/`; câmpurile interne (`steps`) nu ajung la frontend; recomandare inexistentă → 404
- `test_actions_are_saved` — acțiunea chiar se salvează în bază

### Rezultate
pytest **136 trecute / 0 picate** · ruff ok · **smoke: PICĂ** · serverul pornește; `GET /crew/cm-2/alerts` → `al-0001` (immune, nivel 2, escalated), `GET /cmo/queue` → `al-0001` · editorul: fără probleme

### De ce pică smoke
`scripts/request_examples.py` (folosit de smoke) cere alerte cu **id-urile fixe din mock**:
- `al-1042` (alerta imunitară a lui `cm-2`) — pentru detaliu, bifarea pasului `st-2`, escaladarea la 3; în bază, alerta reală se numește `al-0001`;
- `al-1039` (o alertă de **tastare**, nivel 1, „active”, a lui `cm-2`) — pentru „ack” și pentru închiderea de către astronaut; **în bază nu există încă**: o va produce motorul abia la T19 (tastarea mai lentă din zilele 95–97).

Deci nu e o greșeală în endpoint-uri: exemplele de test cer date care, pe backend-ul real, ori au alt nume, ori nu există încă.

### Endpointuri devenite reale
- `GET /api/v1/crew/{crew_id}/alerts`
- `GET /api/v1/cmo/queue`
- `GET /api/v1/alerts/{alert_id}`
- `POST /api/v1/alerts/{alert_id}/ack`
- `PUT /api/v1/alerts/{alert_id}/plan/steps/{step_id}`
- `POST /api/v1/alerts/{alert_id}/escalate` (fără pachetul de la nivelul 3, care vine la T23)
- `POST /api/v1/alerts/{alert_id}/resolve`
- `GET /api/v1/catalog/recommendations`, `GET /api/v1/catalog/recommendations/{rec_id}`

### Texte rămase în română
- Textele recomandărilor (declanșator, acțiune) și pașii planului vin din `data/catalog/recommendations.json`; nu le traduc în cod.
- Tabloul de bord și panourile (mock, T21) arată încă alertele mock `al-1042` / `al-1039`, nu `al-0001`.

### Decizii luate singur
- „Monitoring” scrie în istoric `rechecked` (nu `resolved`), pentru că alerta rămâne deschisă.
- Escaladarea sau închiderea unei alerte deja rezolvate → 409 `invalid_state`.
- La debifarea unui pas nu se scrie nimic în istoric (doar bifarea e o acțiune).
- La escaladarea manuală, culoarea alertei devine „alert”.
- Ora evenimentelor live (`at`) vine încă din mock (fixă, 07:42); devine ora reală la T22.

### Cum verific eu de mână
1. `cd backend; uv run uvicorn app.main:app --port 8000` → /docs, „Authorize” cu `mock-specialist2`
2. `GET /api/v1/crew/cm-2/alerts` → `al-0001`; `GET /api/v1/alerts/al-0001` → alerta completă
3. „Authorize” cu `mock-medic` → `POST /api/v1/alerts/al-0001/escalate` cu `{"to_level": 3}` → nivel 3

### Mesaj de commit propus
backend: T17 alertele: endpoint-urile reale (după ce rezolvăm smoke)

### Următorul task
T18 (dependențele lui sunt gata: da, T16)
