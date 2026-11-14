# Thresholds CHOSEN BY THE TEAM (not from the literature). The only place in the engine with hard-coded numbers.
# All of them are shown as "derived" on the Evidence screen.

# Perception gap (T18), in points
PERCEPTION_GAP_WATCH = 15
PERCEPTION_GAP_ALERT = 25

# Environmental cause (T29): the same deviation in at least this many crew members, on the same day
ENVIRONMENTAL_MIN_CREW = 3

# Radiation (T25): consecutive readings above the threshold that trigger the alert
SEP_CONSECUTIVE_READINGS = 3

# Typing (T19)
FLIGHT_PAUSE_MS = 2000
KEYSTROKE_WATCH_FATIGUE = 50
KEYSTROKE_ALERT_FATIGUE = 75

# Cross signals (T29): window in days
CROSS_SIGNAL_WINDOW_DAYS = 3

# Baseline (T12): minimum spread, so a very steady person does not raise alarms on noise
MIN_SPREAD = {"night_pulse_bpm": 1.5, "temperature_c": 0.15, "sleep_hours": 0.4, "keys_per_min": 8.0}

# Sentinel pillar (T14): stress index weights (sum = 1) and the scale of each component
STRESS_WEIGHTS = {"fatigue": 0.5, "isolation": 0.2, "dose": 0.3}
STRESS_ISOLATION_FULL_DAYS = 140
STRESS_DOSE_RATIO_FULL = 6.0

# Sentinel pillar (T14): score points lost per bpm of night pulse above the personal median
SENTINEL_SCORE_PENALTY_PER_BPM = 6.0
