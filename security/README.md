# security — ce NU rulează în aplicație

**Cine lucrează aici:** securitate (2)

Modelul de amenințări, arhitectura de securitate, auditul, scripturile de atac pentru demo și generarea cheilor. Codul care rulează în aplicație stă în backend/app/security/.

## Ce e aici

| Folder | Ce face |
|---|---|
| `keys/` | `generate_keys.py` generează toate cheile (Ed25519 și AES-256). Cheile nu intră în git. |
| `tokens/` | tokenurile de acces (JWT semnat EdDSA) și autentificarea cu blocarea contului |
| `encryption/` | criptarea înregistrărilor (`storage.py`) și sigilarea pachetelor navă → Pământ (`packets.py`) |
| `measurements/` | semnătura, vechimea, retrimiterea și valorile imposibile ale măsurătorilor |
| `audit/` | jurnalul de acces cu lanț de hash-uri |
| `attacks/` | scripturile de atac pentru demo (de scris) |

## Cum se rulează

```bash
pip install -r security/requirements.txt
python security/run_tests.py                # toate testele, cu chei de probă: nu cere nimic pregătit
python security/keys/generate_keys.py       # cheile reale, o singură dată (în security/keys/keys_files/)
```

Un test picat oprește scriptul cu cod de eroare. Fiecare test se poate rula și singur, din folderul lui
(`cd security/tokens && python test_login.py`), după ce cheile au fost generate.

## Ce nu acoperă încă (de spus onest juriului)

- **Jurnalul de acces:** lanțul arată o intrare modificată sau ștearsă din mijloc. Ștergerea ultimelor intrări sau
  rescrierea întregului jurnal se văd doar dacă `head()` e păstrat în altă parte (de exemplu trimis Pământului în
  fiecare pachet) și dat înapoi lui `verify()`.
- **Retrimiterea unui pachet** nu se verifică în `packets.py`; în aplicație o detectează backend-ul (`direction` + `seq`).
- **Retrimiterea unei măsurători** se ține minte doar în memorie: după o repornire, o măsurătoare mai nouă de
  2 minute poate fi trimisă din nou.
- **Cheile private** stau necriptate pe disc, citibile doar de proprietar.
