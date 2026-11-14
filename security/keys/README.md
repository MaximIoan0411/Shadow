# keys — generarea cheilor (cheile NU intră în git)

**Cine lucrează aici:** securitate

Aici stă doar scriptul de generare. Cheile generate sunt în .gitignore.

```bash
python security/keys/generate_keys.py           # creează cheile care lipsesc, în keys_files/
python security/keys/generate_keys.py --env     # afișează și rândul LINK_AES_KEY_B64 pentru .env
python security/keys/generate_keys.py --force   # înlocuiește TOATE cheile
```

Cu `--force`, tokenurile emise și înregistrările criptate cu cheile vechi nu mai pot fi citite.
