from pathlib import Path

from scripts import check_build_environment


def test_build_environment_declares_embedded_service_dependencies():
    modules = {module for module, _ in check_build_environment.REQUIRED_BUILD_MODULES}
    assert {
        "PyInstaller",
        "PyQt5.QtWidgets",
        "fastapi",
        "uvicorn",
        "pydantic_settings",
        "sse_starlette",
        "playwright",
        "openai",
    } <= modules
    assert "musicdl" not in modules


def test_runtime_requirements_do_not_install_insecure_musicdl_chain():
    requirements = (
        Path(__file__).resolve().parents[1]
        / "install"
        / "requirements.txt"
    ).read_text(encoding="utf-8")
    active_lines = {
        line.strip().casefold()
        for line in requirements.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert not any(line.startswith("musicdl") for line in active_lines)


def test_missing_build_modules_reports_unavailable_module(monkeypatch):
    real_find_spec = check_build_environment.importlib.util.find_spec

    def fake_find_spec(name: str):
        if name == "fastapi":
            return None
        return real_find_spec(name)

    monkeypatch.setattr(check_build_environment.importlib.util, "find_spec", fake_find_spec)
    missing = check_build_environment.missing_build_modules()
    assert ("fastapi", "fastapi") in missing
    assert "install/requirements.txt" in check_build_environment.format_missing_modules(missing)
