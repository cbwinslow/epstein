import json
from pathlib import Path

from epstein.pipeline_orchestrator import OrchestratorOptions, run_orchestrator


def test_orchestrator_runs_steps(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({
            "seed_urls": [],
            "output_dir": str(tmp_path / "artifacts"),
            "allow_domains": ["justice.gov"],
        }),
        encoding="utf-8",
    )

    calls = {"pipeline": 0, "ingest": 0, "relationships": 0, "image_ocr": 0, "embeddings": 0}
    execution_order = []

    def fake_run_pipeline(cfg, verbose=False):
        calls["pipeline"] += 1
        execution_order.append(("pipeline", verbose))

    def fake_ingest_artifacts(artifacts_dir, dsn, truncate=False):
        calls["ingest"] += 1
        execution_order.append("ingest")

    def fake_run_relationship_analysis(**kwargs):
        calls["relationships"] += 1
        execution_order.append("relationships")
        return 1

    def fake_run_image_ocr(*args, **kwargs):
        calls["image_ocr"] += 1
        execution_order.append("image_ocr")
        return [], []

    def fake_run_embeddings(*args, **kwargs):
        calls["embeddings"] += 1
        execution_order.append("embeddings")

    monkeypatch.setattr("epstein.pipeline_orchestrator.run_pipeline", fake_run_pipeline)
    monkeypatch.setattr("epstein.pipeline_orchestrator.ingest_artifacts", fake_ingest_artifacts)
    monkeypatch.setattr("epstein.pipeline_orchestrator.run_relationship_analysis", fake_run_relationship_analysis)
    monkeypatch.setattr("epstein.pipeline_orchestrator.run_image_ocr", fake_run_image_ocr)
    monkeypatch.setattr("epstein.pipeline_orchestrator.run_embeddings", fake_run_embeddings)

    opts = OrchestratorOptions(
        config_path=config_path,
        artifacts_dir=tmp_path / "artifacts",
        dsn="postgresql://analysis:analysis@localhost:5432/analysis",
        qdrant_url="http://localhost:6333",
        collection="epstein_chunks",
        run_ingest=True,
        run_embeddings=True,
        run_relationships=True,
        run_image_ocr=True,
        image_input_dir=tmp_path / "images",
        image_output_dir=tmp_path / "image_text",
        image_extensions=[".png"],
        relationship_min_count=2,
        relationship_max_evidence=5,
        truncate=False,
        verbose=True,
    )

    run_orchestrator(opts)

    assert calls["pipeline"] == 1
    assert calls["ingest"] == 1
    assert calls["relationships"] == 1
    assert calls["image_ocr"] == 1
    assert calls["embeddings"] == 1
    
    # Verify execution order: pipeline first, then image_ocr, then ingest, then relationships, then embeddings
    assert execution_order[0] == ("pipeline", True)  # Verify verbose is passed correctly
    assert execution_order.index("ingest") > execution_order.index(("pipeline", True))
    assert execution_order.index("embeddings") > execution_order.index("ingest")


def test_orchestrator_error_handling(tmp_path: Path, monkeypatch) -> None:
    """Test that orchestrator handles failures in pipeline steps gracefully."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({
            "seed_urls": [],
            "output_dir": str(tmp_path / "artifacts"),
            "allow_domains": ["justice.gov"],
        }),
        encoding="utf-8",
    )

    def fake_run_pipeline(cfg, verbose=False):
        pass  # Pipeline runs successfully

    def fake_ingest_artifacts(artifacts_dir, dsn, truncate=False):
        pass

    def fake_run_embeddings(*args, **kwargs):
        raise RuntimeError("Embeddings failed")

    monkeypatch.setattr("epstein.pipeline_orchestrator.run_pipeline", fake_run_pipeline)
    monkeypatch.setattr("epstein.pipeline_orchestrator.ingest_artifacts", fake_ingest_artifacts)
    monkeypatch.setattr("epstein.pipeline_orchestrator.run_embeddings", fake_run_embeddings)

    opts = OrchestratorOptions(
        config_path=config_path,
        artifacts_dir=tmp_path / "artifacts",
        dsn="postgresql://analysis:analysis@localhost:5432/analysis",
        qdrant_url="http://localhost:6333",
        collection="epstein_chunks",
        run_ingest=True,
        run_embeddings=True,
        run_relationships=False,
        run_image_ocr=False,
        image_input_dir=tmp_path / "images",
        image_output_dir=tmp_path / "image_text",
        image_extensions=[".png"],
        relationship_min_count=2,
        relationship_max_evidence=5,
        truncate=False,
        verbose=False,
    )

    # Orchestrator should propagate the error from embeddings
    try:
        run_orchestrator(opts)
        assert False, "Expected RuntimeError to be raised"
    except RuntimeError as e:
        assert "Embeddings failed" in str(e)
