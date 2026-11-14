# keys — generarea cheilor (cheile NU intră în git)

**Cine lucrează aici:** securitate

Aici stă doar scriptul de generare. Cheile generate sunt în .gitignore.

```bash
python security/keys/generate_keys.py           # creează cheile care lipsesc, în keys_files/
python security/keys/generate_keys.py --env     # afișează și rândul LINK_AES_KEY_B64 pentru .env
python security/keys/generate_keys.py --force   # înlocuiește TOATE cheile
```

Cu `--force`, tokenurile emise și înregistrările criptate cu cheile vechi nu mai pot fi citite.

Backend-ul rulează singur acest script la pornire, pentru cheile care lipsesc; nu e nevoie să-l porniți de mână.
Fiecare dispozitiv (`wearable-cm-1` … `wearable-cm-4`) are cheia lui și poate semna doar pentru membrul lui de echipaj.
