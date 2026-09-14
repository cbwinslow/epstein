def test_mission_control_module_imports():
    # Importing should not raise
    import importlib

    importlib.import_module("tools.mission_control.app")
