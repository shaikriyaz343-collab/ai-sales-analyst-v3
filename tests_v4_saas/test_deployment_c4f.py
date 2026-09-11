from pathlib import Path


def test_v4_production_runner_exists() -> None:
    path = Path("backend/run_production.py")
    assert path.is_file()


def test_v4_production_runner_imports_cleanly() -> None:
    import backend.run_production as runner

    assert callable(runner.main)


def test_v4_production_runner_invokes_fastapi_without_reload(monkeypatch) -> None:
    import backend.run_production as runner

    calls = []

    def fake_run(application, **kwargs):
        calls.append((application, kwargs))

    monkeypatch.setattr(runner.uvicorn, "run", fake_run)
    monkeypatch.setenv("V4_BIND_HOST", "127.0.0.1")
    monkeypatch.setenv("V4_BIND_PORT", "8123")

    runner.main()

    assert calls == [
        (
            "backend.api.main:app",
            {
                "host": "127.0.0.1",
                "port": 8123,
                "reload": False,
            },
        )
    ]