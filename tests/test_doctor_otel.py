import scripts.doctor as doctor


class DummySocket:
    def __init__(self, succeed=True):
        self.succeed = succeed

    def create_connection(self, *a, **k):
        if not self.succeed:
            raise OSError("cannot connect")
        return True


def test_doctor_with_otel_endpoint_reachable(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")

    # Patch socket.create_connection to succeed
    import socket

    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: True)

    # Patch external checks (docker, qdrant) to succeed so the only OTEL check is under test
    monkeypatch.setattr(doctor, "run", lambda cmd: (0, "ok"))
    monkeypatch.setattr(doctor, "http_json", lambda url, timeout=3: (True, {}))

    rc = doctor.main()
    # With everything else OK and OTEL reachable, expect rc == 0
    assert rc == 0


def test_doctor_with_otel_endpoint_unreachable(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")

    # Patch socket.create_connection to fail
    import socket

    def fail(*a, **k):
        raise OSError("no route")

    monkeypatch.setattr(socket, "create_connection", fail)

    # Patch external checks (docker, qdrant) to succeed
    monkeypatch.setattr(doctor, "run", lambda cmd: (0, "ok"))
    monkeypatch.setattr(doctor, "http_json", lambda url, timeout=3: (True, {}))

    rc = doctor.main()
    # OTEL enabled but endpoint unreachable should return a warning code 2
    assert rc == 2
