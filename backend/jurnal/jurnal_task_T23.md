## T23 — Coada: crearea pachetelor

### Pe scurt, ce am făcut (pe înțeles)

Între navă și Pământ nu se poate vorbi „în direct”: un mesaj spre Marte face minute bune pe drum. De aceea mesajele merg ca **pachete** într-o **coadă**. Acum pachetele se creează de-adevăratelea, în tabelul `packets`:
- **Escaladarea unei alerte la nivelul 3** (ofițerul medical o trimite pe Pământ) creează automat un pachet `alert_l3` cu toată alerta înăuntru. Alerta primește `packet_id`, iar în istoricul ei apare „packet_sent”. La fel dacă motorul ar escalada singur la nivelul 3.
- **`POST /link/outbox`** — rezumatul săptămânal aprobat de astronaut (`weekly_summary`), sau retrimiterea unei alerte de nivel 3. Astronautul poate trimite doar despre el.
- **`POST /earth/replies`** — răspunsul medicului de pe Pământ, în sens invers (`up`).

**Fiecare pachet e sigilat:** primește un număr (`pk-0001`…), un număr de ordine pe direcție (`seq` 1, 2, 3… separat pentru navă → Pământ și Pământ → navă, ca să nu poată fi retrimis același pachet) și un „plic” (antet) cu cheia folosită. Conținutul se sigilează cu funcția echipei de securitate și **se salvează doar sigilat**; în clar apare abia la livrare (T24).

**Citirea:**
- `GET /link/packets` — coada, cele mai noi primele, cu filtre; fiecare pachet are bara de progres (`progress`) și câte secunde reale mai are până la sosire (`eta_real_s`), calculate la momentul cererii.
- `GET /link/packets/{id}` — un pachet; conținutul (`payload`) apare doar dacă pachetul a ajuns și rolul are voie să-l citească (Pământul: pachetele de la navă; ofițerul medical: pachetele de pe Pământ și ce a trimis el); altfel `null`.
- `GET /link/status` — starea legăturii, acum cu numărul real de pachete în așteptare.

### Fișiere modificate
- `backend/app/link/queue.py` — `enqueue` (număr, seq, antet, sigilare, salvare) și `configure` (cheile, la pornire)
- `backend/app/services/link.py` — scris tot: trimiterea alertei pe Pământ, outbox, răspunsul Pământului, lista, detaliul, mesajele (T24)
- `backend/app/services/alerts.py` — escaladarea la nivelul 3 creează pachetul
- `backend/app/services/pipeline.py` — escaladarea automată la nivelul 3 creează pachetul
- `backend/app/routers/link.py` — endpoint-urile apelează serviciul (nu mai e mock); textele în engleză
- `scripts/smoke.py` (în afara `backend/`) — `pk-0006` / `pk-0007` din exemple → pachetul real creat de exemplul de escaladare (diff total față de git: +25/−5 rânduri, editat de mână)
- `backend/tests/link/test_enqueue.py` — nou, 7 teste
- `backend/tests/routers/test_alerts_api.py` — istoricul alertei are acum și pasul „packet_sent” la escaladarea la nivelul 3

### Teste adăugate
- `test_escalation_to_level_3_creates_a_sealed_packet` — pachet `queued`, `seq` 1, doar sigilat (fără conținut în clar), antetul cu cheia navei, alerta are `packet_id` și „packet_sent” în istoric
- `test_second_packet_has_seq_2` — al doilea pachet spre Pământ are `seq` 2
- `test_up_direction_has_its_own_seq` — răspunsul Pământului începe de la `seq` 1, cu cheia Pământului
- `test_payload_hidden_until_delivered` — Pământul nu vede conținutul până la livrare
- `test_list_newest_first_and_filters` — lista, filtrul pe direcție, numărul de pachete în așteptare
- `test_outbox_rules` — astronautul nu poate trimite despre altul (403); `alert_l3` fără alertă → 422; alertă inexistentă → 404
- `test_nothing_stored_in_clear` — niciun pachet nu are conținutul în clar înainte de livrare

### Rezultate
pytest **211 trecute / 0 picate** · ruff ok · smoke OK

### Endpointuri devenite reale
- `GET /api/v1/link/status`, `GET /api/v1/link/packets`, `GET /api/v1/link/packets/{packet_id}`
- `POST /api/v1/link/outbox`, `POST /api/v1/earth/replies`
- `POST /api/v1/alerts/{id}/escalate` la nivelul 3 (acum cu pachetul)

### Texte rămase în română
niciunul nou

### Decizii luate singur
- **Cheile:** coada primește cheile o dată, la pornire (`queue.configure`), ca antetul să aibă `key_id`-ul navei sau al Pământului.
- **`crypto.nonce_b64` și `signature_b64`** sunt goale deocamdată: sigilarea echipei de securitate e încă provizorie (fără criptare reală). Se completează singure când securitatea termină `sealing.seal`.
- **Titlurile pachetelor**: „Sentinel · Night pulse +7 bpm, 3 nights in a row”, „Weekly summary · week 14”, „Reply: …”.
- Rezumatul săptămânal fără text primește un text implicit; săptămâna = (ziua − 1) / 7 + 1.
- Un răspuns al Pământului legat de o alertă a altui astronaut → 422.

### Cum verific eu de mână
1. /docs, „Authorize” cu `mock-medic` → `POST /api/v1/alerts/al-0001/escalate` cu `{"to_level": 3}` → `packet_id`
2. „Authorize” cu `mock-earth` → `GET /api/v1/link/packets` → pachetul `queued` / `in_transit`; `GET /api/v1/link/packets/pk-0001` → `payload` e `null` până ajunge

### Mesaj de commit propus
(comun cu T22 și T24, vezi `jurnal_task_T24.md`)
