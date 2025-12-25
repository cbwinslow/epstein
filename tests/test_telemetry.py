from epstein import telemetry


def test_get_tracer_has_context_manager():
    tracer = telemetry.get_tracer("test")
    # Should provide start_as_current_span (Noop or real)
    assert hasattr(tracer, "start_as_current_span")
    with tracer.start_as_current_span("unit-test"):
        pass
