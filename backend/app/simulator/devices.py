"""Dispozitivele simulate: trimit măsurători semnate la /ingest/measurements (sau direct prin serviciu). TASK T32."""


def signed_measurement(device_id: str, crew_id: str, metric_key: str, value: float, unit: str, measured_at_iso: str,
                       private_key: bytes) -> dict:
    """Forma MeasurementIngest, semnată cu security.signing.sign peste security.signing.canonical()."""
    raise NotImplementedError("T32")
