from pathlib import Path

from epstein.image_ocr import ocr_image, run_image_ocr


def test_ocr_image_missing_tool(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr("shutil.which", lambda _: None)

    result = ocr_image(image_path, tmp_path)
    assert result.success is False
    assert "tesseract" in result.message


def test_run_image_ocr_success(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake")

    def fake_which(_: str) -> str:
        return "/usr/bin/tesseract"

    def fake_run(cmd, capture_output, text, check):
        output_base = Path(cmd[2])
        output_base.with_suffix(".txt").write_text("ok", encoding="utf-8")
        class Result:
            returncode = 0
            stderr = ""
            stdout = ""
        return Result()

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("subprocess.run", fake_run)

    successes, failures = run_image_ocr(tmp_path, tmp_path, [".jpg"])
    assert len(successes) == 1
    assert not failures
    assert successes[0].text_path.read_text(encoding="utf-8") == "ok"
