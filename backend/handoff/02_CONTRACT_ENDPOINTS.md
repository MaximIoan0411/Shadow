# 02 — Contractul endpoint-urilor (compact)

**Generat** de `scripts/build_handoff.py` din `backend/app` (versiunea 1.2.0). Nu editați de mână.

Versiunea completă, cu descrierea fiecărui câmp, exemple reale și regulile (roluri, erori, SSE, fluxuri):
`contract/api/README.md`. Modelele: `backend/app/schemas.py`. Formatul erorilor: `{"error": {"code", "message", "details"}}`.

Prefix: `/api/v1`. Autentificare: `Authorization: Bearer <token>` (în mock: `mock-<utilizator>`).
Roluri: `astronaut` (doar datele lui), `cmo` (ofițerul medical; tot echipajul, cu jurnal), `earth` (doar pachetele sosite).

| Metodă | Cale | Roluri | Cerere | Răspuns | Erori | Task |
|---|---|---|---|---|---|---|
| GET | `/api/v1/auth/accounts` | public | — | `200` list[LoginAccount] | — | T07 |
| POST | `/api/v1/auth/login` | public | LoginRequest | `200` LoginResponse | 401,429 | T07 |
| GET | `/api/v1/auth/me` | astronaut, cmo, earth | — | `200` User | 401 | T07 |
| POST | `/api/v1/auth/logout` | astronaut, cmo, earth | — | `200` Ok | 401 | T07 |
| GET | `/api/v1/mission` | astronaut, cmo, earth | — | `200` MissionState | 401 | T09 |
| GET | `/api/v1/environments` | astronaut, cmo, earth | — | `200` list[EnvironmentInfo] | 401 | T09 |
| PUT | `/api/v1/mission/environment` | astronaut, cmo | EnvironmentUpdate | `200` MissionState | 401,403 | T09 |
| PUT | `/api/v1/sim/clock` | astronaut, cmo | ClockUpdate | `200` MissionState | 401,403,409 | T33 |
| GET | `/api/v1/crew` | cmo | — | `200` list[CrewSummary] | 401,403 | T21 |
| GET | `/api/v1/crew/{crew_id}/dashboard` | astronaut, cmo | ?as_of_day | `200` Dashboard | 401,403,404 | T21 |
| GET | `/api/v1/crew/{crew_id}/pillars/{pillar}` | astronaut, cmo | ?as_of_day | `200` PillarDetail | 401,403,404 | T21 |
| GET | `/api/v1/crew/{crew_id}/pillars/{pillar}/series` | astronaut, cmo | ?metric&from_day&to_day | `200` MetricSeries | 401,403,404 | T21 |
| GET | `/api/v1/crew/{crew_id}/timeline` | astronaut, cmo | ?from_day&to_day | `200` Timeline | 401,403,404 | T21 |
| GET | `/api/v1/checkin/schema` | astronaut, cmo | — | `200` CheckinSchema | 401 | T18 |
| POST | `/api/v1/crew/{crew_id}/checkins` | astronaut, cmo | CheckinCreate | `201` CheckinResult | 401,403,404 | T18 |
| GET | `/api/v1/crew/{crew_id}/checkins` | astronaut, cmo | ?from_day&to_day | `200` list[Checkin] | 401,403,404 | T18 |
| GET | `/api/v1/crew/{crew_id}/checkins/today` | astronaut, cmo | — | `200` Checkin | null | 401,403,404 | T18 |
| POST | `/api/v1/crew/{crew_id}/keystrokes/batches` | astronaut, cmo | KeystrokeBatch | `200` KeystrokeResult | 401,403,404 | T19 |
| GET | `/api/v1/crew/{crew_id}/keystrokes/summary` | astronaut, cmo | ?last | `200` KeystrokeSummary | 401,403,404 | T19 |
| POST | `/api/v1/crew/{crew_id}/pvt` | astronaut, cmo | PvtSubmit | `201` PvtResult | 401,403,404 | T20 |
| GET | `/api/v1/crew/{crew_id}/pvt` | astronaut, cmo | ?limit | `200` list[PvtResult] | 401,403,404 | T20 |
| GET | `/api/v1/crew/{crew_id}/exercise/today` | astronaut, cmo | — | `200` ExerciseToday | 401,403,404 | T28 |
| POST | `/api/v1/crew/{crew_id}/exercise/sessions` | astronaut, cmo | ExerciseSessionCreate | `201` ExerciseSession | 401,403,404 | T28 |
| GET | `/api/v1/crew/{crew_id}/exercise/sessions` | astronaut, cmo | ?from_day&to_day | `200` list[ExerciseSession] | 401,403,404 | T28 |
| GET | `/api/v1/crew/{crew_id}/alerts` | astronaut, cmo | ?state&topic | `200` list[AlertBrief] | 401,403,404 | T17 |
| GET | `/api/v1/cmo/queue` | cmo | — | `200` list[AlertBrief] | 401,403 | T17 |
| GET | `/api/v1/alerts/{alert_id}` | astronaut, cmo | — | `200` Alert | 401,403,404 | T17 |
| POST | `/api/v1/alerts/{alert_id}/ack` | astronaut, cmo | — | `200` Alert | 401,403,404,409 | T17 |
| PUT | `/api/v1/alerts/{alert_id}/plan/steps/{step_id}` | astronaut, cmo | StepUpdate | `200` Alert | 401,403,404 | T17 |
| POST | `/api/v1/alerts/{alert_id}/escalate` | astronaut, cmo | EscalateRequest | `200` Alert | 401,403,404,409 | T17 |
| POST | `/api/v1/alerts/{alert_id}/resolve` | astronaut, cmo | ResolveRequest | `200` Alert | 401,403,404 | T17 |
| GET | `/api/v1/catalog/recommendations` | astronaut, cmo, earth | ?topic&level | `200` list[Recommendation] | 401 | T17 |
| GET | `/api/v1/catalog/recommendations/{rec_id}` | astronaut, cmo, earth | — | `200` Recommendation | 401,404 | T17 |
| GET | `/api/v1/link/status` | astronaut, cmo, earth | — | `200` LinkStatus | 401 | T23 |
| GET | `/api/v1/link/packets` | cmo, earth | ?direction&status&limit | `200` list[Packet] | 401,403 | T23 |
| GET | `/api/v1/link/packets/{packet_id}` | cmo, earth | — | `200` PacketDetail | 401,403,404 | T23 |
| POST | `/api/v1/link/outbox` | astronaut, cmo | OutboxCreate | `201` Packet | 401,403,404 | T23 |
| POST | `/api/v1/earth/replies` | earth | EarthReplyCreate | `201` Packet | 401,403,404 | T23 |
| GET | `/api/v1/crew/{crew_id}/messages` | astronaut, cmo | — | `200` list[CrewMessage] | 401,403,404 | T23 |
| GET | `/api/v1/radiation/status` | astronaut, cmo | — | `200` RadiationStatus | 401,403 | T25 |
| GET | `/api/v1/radiation/series` | astronaut, cmo | ?hours&step_min | `200` RadiationSeries | 401,403 | T25 |
| GET | `/api/v1/radiation/events` | astronaut, cmo, earth | — | `200` text/event-stream | 401 | T25 |
| POST | `/api/v1/radiation/shelter-ack` | astronaut, cmo | ShelterAck | `200` RadiationStatus | 401,403 | T25 |
| GET | `/api/v1/ai/status` | astronaut, cmo | — | `200` AiStatus | 401 | T31 |
| POST | `/api/v1/ai/chat` | astronaut, cmo | AiChatRequest | `200` AiChatResponse | 401,403 | T31 |
| GET | `/api/v1/access-log` | astronaut, cmo | ?crew_id&limit | `200` list[AccessLogEntry] | 401,403 | T08 |
| GET | `/api/v1/security/rejections` | astronaut, cmo | ?limit | `200` list[Rejection] | 401,403 | T32 |
| POST | `/api/v1/ingest/measurements` | device | MeasurementIngest | `200` IngestResult | — | T32 |
| GET | `/api/v1/evidence/tests` | astronaut, cmo, earth | — | `200` TestReport | 401 | T32 |
| GET | `/api/v1/evidence/parameters` | astronaut, cmo, earth | ?topic&key_only | `200` list[Parameter] | 401 | T32 |
| POST | `/api/v1/sim/sep/start` | astronaut, cmo, earth | SepStart | `200` RadiationStatus | 401,403 | T26 |
| POST | `/api/v1/sim/sep/stop` | astronaut, cmo, earth | — | `200` RadiationStatus | 401,403 | T26 |
| POST | `/api/v1/demo/inject-spoof` | astronaut, cmo, earth | — | `200` Packet | 401,403 | T33 |
| POST | `/api/v1/demo/frozen-sensor` | astronaut, cmo, earth | — | `200` Rejection | 401,403 | T33 |
| POST | `/api/v1/sim/reset` | astronaut, cmo, earth | — | `200` Ok | 401,403 | T33 |
| GET | `/api/v1/events` | astronaut, cmo, earth | — | `200` text/event-stream | 401 | T22 |
| GET | `/health` | public | — | `200` — | — | T03 |

## Pe task

| Task | Endpoint-uri |
|---|---|
| T03 | `GET /health` |
| T07 | `GET /api/v1/auth/accounts`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout` |
| T08 | `GET /api/v1/access-log` |
| T09 | `GET /api/v1/mission`, `GET /api/v1/environments`, `PUT /api/v1/mission/environment` |
| T17 | `GET /api/v1/crew/{crew_id}/alerts`, `GET /api/v1/cmo/queue`, `GET /api/v1/alerts/{alert_id}`, `POST /api/v1/alerts/{alert_id}/ack`, `PUT /api/v1/alerts/{alert_id}/plan/steps/{step_id}`, `POST /api/v1/alerts/{alert_id}/escalate`, `POST /api/v1/alerts/{alert_id}/resolve`, `GET /api/v1/catalog/recommendations`, `GET /api/v1/catalog/recommendations/{rec_id}` |
| T18 | `GET /api/v1/checkin/schema`, `POST /api/v1/crew/{crew_id}/checkins`, `GET /api/v1/crew/{crew_id}/checkins`, `GET /api/v1/crew/{crew_id}/checkins/today` |
| T19 | `POST /api/v1/crew/{crew_id}/keystrokes/batches`, `GET /api/v1/crew/{crew_id}/keystrokes/summary` |
| T20 | `POST /api/v1/crew/{crew_id}/pvt`, `GET /api/v1/crew/{crew_id}/pvt` |
| T21 | `GET /api/v1/crew`, `GET /api/v1/crew/{crew_id}/dashboard`, `GET /api/v1/crew/{crew_id}/pillars/{pillar}`, `GET /api/v1/crew/{crew_id}/pillars/{pillar}/series`, `GET /api/v1/crew/{crew_id}/timeline` |
| T22 | `GET /api/v1/events` |
| T23 | `GET /api/v1/link/status`, `GET /api/v1/link/packets`, `GET /api/v1/link/packets/{packet_id}`, `POST /api/v1/link/outbox`, `POST /api/v1/earth/replies`, `GET /api/v1/crew/{crew_id}/messages` |
| T25 | `GET /api/v1/radiation/status`, `GET /api/v1/radiation/series`, `GET /api/v1/radiation/events`, `POST /api/v1/radiation/shelter-ack` |
| T26 | `POST /api/v1/sim/sep/start`, `POST /api/v1/sim/sep/stop` |
| T28 | `GET /api/v1/crew/{crew_id}/exercise/today`, `POST /api/v1/crew/{crew_id}/exercise/sessions`, `GET /api/v1/crew/{crew_id}/exercise/sessions` |
| T31 | `GET /api/v1/ai/status`, `POST /api/v1/ai/chat` |
| T32 | `GET /api/v1/security/rejections`, `POST /api/v1/ingest/measurements`, `GET /api/v1/evidence/tests`, `GET /api/v1/evidence/parameters` |
| T33 | `PUT /api/v1/sim/clock`, `POST /api/v1/demo/inject-spoof`, `POST /api/v1/demo/frozen-sensor`, `POST /api/v1/sim/reset` |

## Evenimente live (`GET /api/v1/events`)

Plic: `{id, type, at, crew_id, data}`. Se publică **după commit**. Tipuri și forma lui `data`: `contract/api/README.md`, secțiunea 6.

`mission.tick`, `environment.changed`, `alert.created`, `alert.updated`, `packet.sent`, `packet.arrived`, `packet.rejected`, `radiation.alert`, `radiation.reading`, `radiation.cleared`, `measurement.rejected`, `reminder.due`, `dashboard.changed`
