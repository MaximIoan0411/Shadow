"""Pragurile ALESE DE ECHIPĂ (nu sunt în literatură). Singurul loc din motor cu cifre scrise direct.
Toate apar ca „derivat” în ecranul Evidence și în prezentare. Gata, nu e un task."""

# Decalajul de percepție (T18)
PERCEPTION_GAP_WATCH = 15        # puncte
PERCEPTION_GAP_ALERT = 25

# Cauza de mediu (T29): aceeași abatere la cel puțin atâția membri, în aceeași zi
ENVIRONMENTAL_MIN_CREW = 3

# Radiații (T25): câte citiri consecutive peste prag declanșează alerta
SEP_CONSECUTIVE_READINGS = 3

# Tastare (T19)
FLIGHT_PAUSE_MS = 2000           # pauzele mai lungi nu intră în flight time
KEYSTROKE_WATCH_FATIGUE = 50     # indicele de oboseală de la care status = watch
KEYSTROKE_ALERT_FATIGUE = 75

# Semnale încrucișate (T29): fereastra în zile
CROSS_SIGNAL_WINDOW_DAYS = 3

# Baseline (T12): deviația minimă, ca un om foarte constant să nu dea alarme la o variație de zgomot
MIN_SPREAD = {"night_pulse_bpm": 1.5, "temperature_c": 0.15, "sleep_hours": 0.4, "keys_per_min": 8.0}
