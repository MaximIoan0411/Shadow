"""Serviciile: logica aplicației. Routerele le apelează; ele folosesc engine/ (pur), db/, security/, clock.
Reguli: tranzacții scurte; commit în serviciu sau în router; evenimentele se întorc ca listă și se publică DUPĂ commit."""
