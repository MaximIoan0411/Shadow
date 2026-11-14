# Reguli pentru Claude în backend/

Se aplică la fiecare task din `handoff/tasks/`. Au prioritate față de `CUM_LUCRAM.MD` și `handoff/` acolo unde diferă.

## Lucrul
- Câte **două taskuri o dată**, în ordinea din `handoff/00_CITESTE_INTAI.md`. După ele te oprești și aștepți să ți se spună să începi următoarele.
- Fiecare task are jurnalul lui (`jurnal_task_Txx.md`), dar mesajul de commit e unul singur pentru ambele: `backend: T20, T21 <ce s-a făcut la fiecare, scurt>`.
- Lucrezi doar în `backend/`. Nu modifici `frontend/`, `ai/`, `security/`, `contract/`, `data/`, nici altceva din afara `backend/`.
- Lucrăm pe `main`. Nu creezi ramuri, nu faci `git commit`, nu faci `git push`.
- Contractul nu se schimbă: căile, parametrii, `response_model`, `app/schemas.py`, `app/ai_schemas.py`, `app/datafiles.py`, semnăturile din `app/security/`.

## Limba
- Tot ce ajunge la frontend (răspunsuri API, mesaje de eroare, evenimente, texte din Swagger) e în engleză.
- Textele din `data/` nu se traduc în cod și nu se modifică.

## Comentariile
- Comentariile ajutătoare în română (`# ...`, docstring-uri) se scot din fiecare fișier în care intri la un task.
- Nu se adaugă comentarii noi în română. Codul trebuie să se înțeleagă singur; un comentariu scurt în engleză doar unde e cu adevărat necesar.
- Nu se șterg texte care ajung la frontend sau în OpenAPI (de exemplu docstring-urile endpoint-urilor și `Field(description=...)`): acelea se traduc în engleză, nu se șterg.

## Verificarea: totul trebuie să meargă înainte de raport
Din `backend/`:
```
uv run ruff format <fișierele atinse> && uv run ruff check --fix app tests
uv run pytest -q
cd .. && uv run --project backend python scripts/smoke.py
```
Plus: serverul pornește (`uv run uvicorn app.main:app --port 8000`, `/health` răspunde) și editorul nu arată erori noi în fișierele atinse. Nu declari taskul gata cu ceva picat și nu slăbești teste.

## Raportul și jurnalul
- La finalul fiecărui task scrii raportul (formatul din `CUM_LUCRAM.MD`, pasul 4) într-un fișier nou: `backend/jurnal/jurnal_task_Txx.md`. Nu modifici jurnalele vechi.
- Jurnalul începe cu o secțiune **„Pe scurt, ce am făcut (pe înțeles)”**: explicație în română simplă, fără jargon, ce face codul nou și de ce, ca să se înțeleagă fără să citești codul.
- În chat spui doar, pe scurt, ce ai făcut, plus **mesajul de commit propus**: `backend: Txx <titlu scurt>`. Detaliile stau în jurnal.
