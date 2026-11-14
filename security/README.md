# security — ce NU rulează în aplicație

**Cine lucrează aici:** securitate (2)

Modelul de amenințări, arhitectura de securitate, auditul și generarea cheilor. Codul care rulează în aplicație stă în `backend/app/security/`.

## Documentele

| Citește | Pentru |
|---|---|
| `threat-model.md` | ce apărăm, de cine, fiecare amenințare cu apărarea, codul și testul ei; ce nu acoperă prototipul |
| `architecture.md` | cheile, semnarea măsurătorilor, sigilarea pachetelor, conturile, cine vede ce, jurnalul |
| `checklist.md` | fiecare cerință, cu starea ei: făcut, parțial, nefăcut |
| `audit/findings.md` | ce s-a găsit la audit, ce s-a reparat, ce a rămas deschis |

## Ce e aici

| Folder | Ce face |
|---|---|
| `keys/` | `generate_keys.py` generează toate cheile (Ed25519 și AES-256). Cheile nu intră în git. |
| `tokens/` | tokenurile de acces (JWT semnat EdDSA) și autentificarea cu blocarea contului |
| `encryption/` | criptarea înregistrărilor (`storage.py`) și sigilarea pachetelor navă → Pământ (`packets.py`) |
| `measurements/` | semnătura, vechimea, retrimiterea și valorile imposibile ale măsurătorilor |
| `audit/` | jurnalul de acces cu lanț de hash-uri (`audit.py`); raportul de audit și verificarea permisiunilor (`check_endpoints.py`) |

## Cum se rulează

```bash
pip install -r security/requirements.txt
python security/run_tests.py                # toate testele, cu chei de probă: nu cere nimic pregătit
python security/keys/generate_keys.py       # cheile reale, o singură dată (în security/keys/keys_files/)
uv run --project backend python security/audit/check_endpoints.py   # permisiunile, pe aplicația reală
```

Un test picat oprește scriptul cu cod de eroare. Fiecare test se poate rula și singur, din folderul lui
(`cd security/tokens && python test_login.py`), după ce cheile au fost generate.

## Legătura cu aplicația

Backend-ul folosește aceleași chei: la pornire citește `security/keys/keys_files/` și creează cu
`generate_keys.py` ce lipsește (inclusiv câte o cheie pe dispozitiv, `wearable-cm-1` … `wearable-cm-4`). Codul
care rulează în aplicație e în `backend/app/security/` și are testele lui în `backend/tests/security/`.

Scripturi de atac nu există: atacurile se arată din panoul *Demo* al aplicației (*Spoofed packet*, *Frozen sensor*)
și sunt acoperite de teste. Lista e în `checklist.md`.

## Ce nu acoperă încă prototipurile de aici

Limitele aplicației sunt în `threat-model.md`. Cele de mai jos sunt ale codului din acest folder.

- **Jurnalul de acces:** lanțul arată o intrare modificată sau ștearsă din mijloc. Ștergerea ultimelor intrări sau
  rescrierea întregului jurnal se văd doar dacă `head()` e păstrat în altă parte (de exemplu trimis Pământului în
  fiecare pachet) și dat înapoi lui `verify()`.
- **Retrimiterea unui pachet** nu se verifică în `packets.py`; în aplicație o detectează backend-ul (`direction` + `seq`).
- **Retrimiterea unei măsurători** se ține minte doar în memorie: după o repornire, o măsurătoare mai nouă de
  2 minute poate fi trimisă din nou.
- **Cheile private** stau necriptate pe disc, citibile doar de proprietar.
