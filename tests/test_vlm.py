from pathlib import Path

import pytest

from cua_lark.adapters.vlm import OpenAIResponsesVisionModel, OpenAIVisionModel, build_vlm
from cua_lark.runtime.config import Settings


def _settings(vlm: dict) -> Settings:
    root = Path(".").resolve()
    return Settings(
        repo_root=root,
        new_root=root,
        config_path=root / "configs" / "config.example.yaml",
        default_cases=root / "tests" / "test_cases" / "phase2-im.yaml",
        default_scenario=root / "cua_lark" / "scenarios" / "im.md",
        results_root=root / "results",
        output_root=root / "outputs",
        vlm=vlm,
        screenshot={},
        executor={},
    )


def test_build_chat_model_uses_environment_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = _settings(
        {
            "default_backend": "demo",
            "demo": {"base_url": "https://example.invalid/v1", "model": "vision-demo", "wire_api": "chat"},
        }
    )

    model = build_vlm(settings)

    assert isinstance(model, OpenAIVisionModel)
    assert model.model == "vision-demo"


def test_build_responses_model_from_config(monkeypatch):
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = _settings(
        {
            "default_backend": "demo",
            "demo": {
                "api_key": "test-key",
                "base_url": "https://example.invalid/v1",
                "model": "vision-demo",
                "wire_api": "responses",
            },
        }
    )

    model = build_vlm(settings)

    assert isinstance(model, OpenAIResponsesVisionModel)
    assert model.model == "vision-demo"


def test_build_model_fails_clearly_without_credentials(monkeypatch):
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = _settings(
        {"default_backend": "demo", "demo": {"base_url": "https://example.invalid/v1", "model": "vision-demo"}}
    )

    with pytest.raises(RuntimeError, match="No VLM API key configured"):
        build_vlm(settings)
