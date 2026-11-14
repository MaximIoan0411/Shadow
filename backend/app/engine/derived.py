# Thresholds CHOSEN BY THE TEAM (not from the literature). The only place in the engine with hard-coded numbers.
# All of them are shown as "derived" on the Evidence screen.

# Perception gap (T18), in points
PERCEPTION_GAP_WATCH = 15
PERCEPTION_GAP_ALERT = 25
# weights of the objective scores in the perception gap, and the score below which a signal is listed as a cause
PERCEPTION_WEIGHTS = {"keystrokes": 1.0, "pvt": 1.0, "night_pulse": 1.0, "sleep": 1.0}
PERCEPTION_SIGNAL_BELOW = 85
# sleep score (T18): points lost per hour of sleep below the personal median
SLEEP_SCORE_PENALTY_PER_HOUR = 25.0
# check-in (T18): the exact same value on this many days in a row = frozen sensor
CHECKIN_FROZEN_DAYS = 3

# Environmental cause (T29): the same deviation in at least this many crew members, on the same day
ENVIRONMENTAL_MIN_CREW = 3

# Radiation (T25): consecutive readings above the threshold that trigger the alert
SEP_CONSECUTIVE_READINGS = 3

# Heart pillar (T27): landing readiness score, points lost per bpm of resting pulse above the in-flight baseline,
# per ln unit of HRV below it, and when the systolic pressure is beyond the in-flight drop threshold;
# the first days of flight are adaptation and do not enter the in-flight baseline
CARDIO_PENALTY_PER_BPM = 3.0
CARDIO_PENALTY_PER_LN_HRV = 40.0
CARDIO_PENALTY_SYSTOLIC = 10.0
CARDIO_ADAPTATION_DAYS = 14
CARDIO_WINDOW_DAYS = 7
# minimum personal CV, so day-to-day noise of a very steady person does not cross the 1×CV / 0.5×CV thresholds
CARDIO_MIN_CV = {"resting_pulse_bpm": 0.03, "hrv_lnrmssd": 0.04}

# Typing (T19)
FLIGHT_PAUSE_MS = 2000
KEYSTROKE_WATCH_FATIGUE = 50
KEYSTROKE_ALERT_FATIGUE = 75
# fatigue index: weight of each feature (sum = 1), the weighted deviation (in personal spreads) that gives 100,
# the most one feature can count, and the keys a session needs before it is judged
KEYSTROKE_WEIGHTS = {"hold_ms_mean": 0.4, "keys_per_min": 0.4, "flight_ms_mean": 0.1, "backspace_rate": 0.1}
KEYSTROKE_FULL_Z = 5.0
KEYSTROKE_Z_CAP = 6.0
KEYSTROKE_MIN_KEYS = 30
# behavioral pillar score: points lost per personal spread below the baseline reaction speed (PVT, T20)
PVT_SCORE_PENALTY_PER_SD = 20.0
# PVT baseline (T20): non-practice tests needed, and the minimum spread of the reaction speed (1/s)
PVT_MIN_BASELINE_TESTS = 2
PVT_MIN_SPEED_SD = 0.15

# Cross signals (T29): window in days
CROSS_SIGNAL_WINDOW_DAYS = 3

# Baseline (T12): minimum spread, so a very steady person does not raise alarms on noise
MIN_SPREAD = {
    "night_pulse_bpm": 1.5,
    "temperature_c": 0.15,
    "sleep_hours": 0.4,
    "keys_per_min": 8.0,
    "hold_ms_mean": 6.0,
    "flight_ms_mean": 15.0,
    "backspace_rate": 0.02,
}

# Sentinel pillar (T14): stress index weights (sum = 1) and the scale of each component
STRESS_WEIGHTS = {"fatigue": 0.5, "isolation": 0.2, "dose": 0.3}
STRESS_ISOLATION_FULL_DAYS = 140
STRESS_DOSE_RATIO_FULL = 6.0

# Sentinel pillar (T14): score points lost per bpm of night pulse above the personal median
SENTINEL_SCORE_PENALTY_PER_BPM = 6.0
