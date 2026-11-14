from ..security import signing


def signed_measurement(
    device_id: str, crew_id: str, metric_key: str, value: float, unit: str, measured_at_iso: str, private_key: bytes
) -> dict:
    """The MeasurementIngest shape, signed with security.signing.sign over security.signing.canonical()."""
    obj = {
        "device_id": device_id,
        "crew_id": crew_id,
        "metric_key": metric_key,
        "value": value,
        "unit": unit,
        "measured_at": measured_at_iso,
    }
    return {**obj, "signature_b64": signing.sign(obj, private_key)}
