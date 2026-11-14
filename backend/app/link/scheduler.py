"""Planificatorul cozii. Task din fundal, pas 1 s real. TASK T24.

La fiecare pas, cu o sesiune proprie:
  1. fereastra deschisă → pachetele queued pleacă: sent_at = now, arrives_at = now + delay, status = in_transit
     → eveniment packet.sent;
  2. pachetele in_transit cu arrives_at <= now → sealing.open(); reușit → delivered + payload; SealError → rejected
     → packet.arrived / packet.rejected (+ alert.updated dacă e un earth_reply legat de o alertă).
Evenimentele se publică DUPĂ commit.
"""


async def link_scheduler() -> None:
    raise NotImplementedError("T24")
