"""Cereri de exemplu pentru fiecare endpoint (API și serviciul AI). Folosite de build_docs.py ca să apeleze
mock-urile și să pună în documentație răspunsuri REALE, și de smoke.py ca să verifice că toate răspund.
Un endpoint nou fără exemplu aici face smoke.py să pice."""

# câte un cont pe astronaut: A = Specialist de misiune 2 (cm-2), C = ofițerul medical (cm-3), E = medicul de zbor
A, C, E = "specialist2", "medic", "earth"
P = "/api/v1"

KEYS = [{"t_down_ms": 10234.5, "t_up_ms": 10321.1, "key_class": "char"},
        {"t_down_ms": 10412.0, "t_up_ms": 10498.7, "key_class": "char"},
        {"t_down_ms": 10655.3, "t_up_ms": 10731.9, "key_class": "backspace"}]

# (metodă, cale-șablon) -> dict(as=rol, path=..., query=..., json=...)
REQUESTS = {
    ("GET", f"{P}/auth/accounts"): dict(as_=None),
    ("POST", f"{P}/auth/login"): dict(as_=None, json={"username": "specialist2", "password": "cm2-shadow"}),
    ("POST", f"{P}/auth/logout"): dict(as_=A),
    ("GET", f"{P}/auth/me"): dict(as_=A),
    ("GET", f"{P}/mission"): dict(as_=A),
    ("GET", f"{P}/environments"): dict(as_=A),
    ("PUT", f"{P}/mission/environment"): dict(as_=C, json={"environment": "mars_transit"}),
    ("PUT", f"{P}/sim/clock"): dict(as_=C, json={"time_scale": 60}),
    ("GET", f"{P}/crew"): dict(as_=C),
    ("GET", f"{P}/crew/{{crew_id}}/dashboard"): dict(as_=A, path={"crew_id": "cm-2"}),
    ("GET", f"{P}/crew/{{crew_id}}/pillars/{{pillar}}"): dict(as_=A, path={"crew_id": "cm-2", "pillar": "immune"}),
    ("GET", f"{P}/crew/{{crew_id}}/pillars/{{pillar}}/series"): dict(as_=A, path={"crew_id": "cm-2", "pillar": "immune"}, query={"metric": "night_pulse_bpm", "from_day": 87}),
    ("GET", f"{P}/crew/{{crew_id}}/timeline"): dict(as_=A, path={"crew_id": "cm-2"}, query={"from_day": 94}),
    ("GET", f"{P}/checkin/schema"): dict(as_=A),
    ("POST", f"{P}/crew/{{crew_id}}/checkins"): dict(as_=A, path={"crew_id": "cm-2"}, json={"mood": 4, "systolic_mmhg": 112, "diastolic_mmhg": 72, "pulse_bpm": 58, "glucose_mg_dl": 92, "temperature_c": 41.9, "sleep_hours": 5.5, "meals_eaten": "some"}),
    ("GET", f"{P}/crew/{{crew_id}}/checkins"): dict(as_=A, path={"crew_id": "cm-2"}, query={"from_day": 90}),
    ("GET", f"{P}/crew/{{crew_id}}/checkins/today"): dict(as_=A, path={"crew_id": "cm-2"}),
    ("POST", f"{P}/crew/{{crew_id}}/keystrokes/batches"): dict(as_=A, path={"crew_id": "cm-2"}, json={"session_id": "8b1f0c1e-6f0a-4f0e-9d53-2c1a7f1b9e10", "context": "free_typing", "events": KEYS}),
    ("GET", f"{P}/crew/{{crew_id}}/keystrokes/summary"): dict(as_=A, path={"crew_id": "cm-2"}, query={"last": 6}),
    ("POST", f"{P}/crew/{{crew_id}}/pvt"): dict(as_=A, path={"crew_id": "cm-2"}, json={"started_at": "2027-04-15T09:00:00Z", "duration_s": 180, "trials": [{"stimulus_at_ms": 3200, "rt_ms": 287, "false_start": False}, {"stimulus_at_ms": 8900, "rt_ms": 402, "false_start": False}, {"stimulus_at_ms": 14100, "rt_ms": None, "false_start": True}]}),
    ("GET", f"{P}/crew/{{crew_id}}/pvt"): dict(as_=A, path={"crew_id": "cm-2"}),
    ("GET", f"{P}/crew/{{crew_id}}/exercise/today"): dict(as_=A, path={"crew_id": "cm-2"}),
    ("POST", f"{P}/crew/{{crew_id}}/exercise/sessions"): dict(as_=A, path={"crew_id": "cm-2"}, json={"kind": "resistance", "started_at": "2027-04-15T16:00:00Z", "duration_min": 35, "sets": [{"exercise": "genuflexiuni ARED", "reps": 10, "load_kg": 85}]}),
    ("GET", f"{P}/crew/{{crew_id}}/exercise/sessions"): dict(as_=A, path={"crew_id": "cm-2"}, query={"from_day": 90}),
    ("GET", f"{P}/crew/{{crew_id}}/alerts"): dict(as_=A, path={"crew_id": "cm-2"}),
    ("GET", f"{P}/cmo/queue"): dict(as_=C),
    ("GET", f"{P}/alerts/{{alert_id}}"): dict(as_=A, path={"alert_id": "al-1042"}),
    ("POST", f"{P}/alerts/{{alert_id}}/ack"): dict(as_=A, path={"alert_id": "al-1039"}),
    ("PUT", f"{P}/alerts/{{alert_id}}/plan/steps/{{step_id}}"): dict(as_=A, path={"alert_id": "al-1042", "step_id": "st-2"}, json={"done": True}),
    ("POST", f"{P}/alerts/{{alert_id}}/escalate"): dict(as_=C, path={"alert_id": "al-1042"}, json={"to_level": 3, "note": "A treia noapte la rând, temperatură în creștere."}),
    ("POST", f"{P}/alerts/{{alert_id}}/resolve"): dict(as_=A, path={"alert_id": "al-1039"}, json={"outcome": "resolved", "note": "Testul de reacție a revenit la normal."}),
    ("GET", f"{P}/catalog/recommendations"): dict(as_=A, query={"topic": "immune"}),
    ("GET", f"{P}/catalog/recommendations/{{rec_id}}"): dict(as_=A, path={"rec_id": "immune-2-1"}),
    ("GET", f"{P}/link/status"): dict(as_=E),
    ("GET", f"{P}/link/packets"): dict(as_=E, query={"direction": "down"}),
    ("GET", f"{P}/link/packets/{{packet_id}}"): dict(as_=E, path={"packet_id": "pk-0006"}),
    ("POST", f"{P}/link/outbox"): dict(as_=A, json={"kind": "weekly_summary", "crew_id": "cm-2", "body": "Săptămâna 14: aprob trimiterea rezumatului."}),
    ("POST", f"{P}/earth/replies"): dict(as_=E, json={"in_reply_to": "pk-0007", "crew_id": "cm-2", "alert_id": "al-1042", "body": "De acord cu odihna. Temperatura de două ori pe zi; dacă depășește 38 °C, anunțați-ne."}),
    ("GET", f"{P}/crew/{{crew_id}}/messages"): dict(as_=A, path={"crew_id": "cm-2"}),
    ("POST", f"{P}/sim/sep/start"): dict(as_=C, json={"event_id": "2024-05-11T02:10:00-SEP-001", "starts_in_min": 0}),
    ("GET", f"{P}/radiation/status"): dict(as_=A),
    ("GET", f"{P}/radiation/series"): dict(as_=A, query={"hours": 1, "step_min": 10}),
    ("GET", f"{P}/radiation/events"): dict(as_=A),
    ("POST", f"{P}/radiation/shelter-ack"): dict(as_=A, json={"sheltered": True}),
    ("POST", f"{P}/sim/sep/stop"): dict(as_=C),
    ("GET", f"{P}/ai/status"): dict(as_=A),
    ("POST", f"{P}/ai/chat"): dict(as_=A, json={"crew_id": "cm-2", "message": "De ce mi-a crescut pulsul de noapte?", "alert_id": "al-1042", "history": []}),
    ("GET", f"{P}/access-log"): dict(as_=A),
    ("GET", f"{P}/security/rejections"): dict(as_=C),
    ("POST", f"{P}/ingest/measurements"): dict(as_=None, json={"device_id": "wearable-cm-2", "crew_id": "cm-2", "metric_key": "night_pulse_bpm", "value": 61, "unit": "bpm", "measured_at": "2027-04-15T03:00:00Z", "signature_b64": "MEUCIQDc...trunchiat..."}),
    ("GET", f"{P}/evidence/tests"): dict(as_=A),
    ("GET", f"{P}/evidence/parameters"): dict(as_=A, query={"key_only": True}),
    ("POST", f"{P}/demo/inject-spoof"): dict(as_=E),
    ("POST", f"{P}/demo/frozen-sensor"): dict(as_=C),
    ("POST", f"{P}/sim/reset"): dict(as_=C),
    ("GET", "/health"): dict(as_=None),
}
# ordinea în care se execută (unele schimbă starea mock-ului)
ORDER = list(REQUESTS)

_CTX = {"topic": "immune", "level": 2, "alert_title": "Puls de noapte +7 bpm, 3 nopți la rând", "mission_day": 96,
        "environment": "mars_transit",
        "evidence": [{"label": "Puls de noapte", "value": 61, "unit": "bpm", "deviation_text": "+7 bpm peste mediana personală, 3 nopți"}],
        "recommendation": {"id": "immune-2-1", "level": 2,
                           "trigger": "Puls mediu de noapte ≥ +4 bpm peste mediana personală, două nopți la rând.",
                           "action": "Anunță ofițerul medical de la bord, cu graficul de puls și temperatură și jurnalul de simptome.",
                           "source_citation": "Alavi et al. (2022), Nature Medicine 28:175–184",
                           "source_url": "https://www.nature.com/articles/s41591-021-01593-2"}}
AI_REQUESTS = {
    ("GET", "/status"): dict(),
    ("POST", "/chat"): dict(json={"message": "De ce mi-a crescut pulsul de noapte?", "history": [], "context": _CTX}),
}
