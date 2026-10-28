from __future__ import annotations

import json
from pathlib import Path

from tests.unit.cli.conftest import FakeContainerRuntime, load_theme, make_image
from theme_producer.adapters.container_processor import ContainerProcessor
from theme_producer.domain.generation import GenerationRequest
from theme_producer.domain.settings import (
    AppSettings,
    ContainerEngine,
    ContainerSettings,
    GenerationSettings,
    OutputSettings,
    RuntimeMode,
    RuntimeSettings,
    TemplatesSettings,
)

IMAGE = "tpr-matugen-podman:latest"


def _settings(output_dir: Path) -> AppSettings:
    return AppSettings(
        output=OutputSettings(
            directory=output_dir, default_formats=(), overwrite=False
        ),
        generation=GenerationSettings(engine="matugen", default_params={}),
        templates=TemplatesSettings(),
        runtime=RuntimeSettings(mode=RuntimeMode.CONTAINER),
        container=ContainerSettings(engine=ContainerEngine.PODMAN),
    )


def test_container_generate_mounts_runs_inner_cli_and_maps_paths(
    tmp_path: Path,
) -> None:
    image = make_image(tmp_path / "wall.png")
    output = tmp_path / "out"
    output.mkdir()
    theme = load_theme()
    (output / "theme.json").write_text(json.dumps(theme.to_dict()), encoding="utf-8")
    (output / "colors.yaml").write_text("background: x\n", encoding="utf-8")
    payload = {
        "success": True,
        "command": "generate",
        "engine": "matugen",
        "theme": theme.to_dict(),
        "output_files": ["/output/theme.json", "/output/colors.yaml"],
        "duration": 0.1,
    }
    runtime = FakeContainerRuntime(
        images={IMAGE}, run_stdout=json.dumps(payload)
    )
    templates = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "theme_producer"
        / "defaults"
        / "templates"
    )
    processor = ContainerProcessor(runtime, templates)
    settings = _settings(output)
    request = GenerationRequest(
        image_path=image,
        engine="matugen",
        params={"mode": "dark"},
        formats=("yaml",),
        output_dir=output,
        runtime=RuntimeMode.CONTAINER,
    )

    result = processor.process_generate(request, settings)

    assert result.success is True
    assert result.output_files == (output / "theme.json", output / "colors.yaml")
    run = runtime.runs[0]
    assert run["image"] == IMAGE
    assert run["command"][:7] == [
        "tpr",
        "--output-format",
        "json",
        "generate",
        str(Path("/input") / "wall.png"),
        "--engine",
        "matugen",
    ]
    assert "--runtime" in run["command"]
    assert run["command"][run["command"].index("--runtime") + 1] == "local"
    assert "--no-summary" in run["command"]
    assert run["environment"]["THEME_CONFIG_FILE_PATH"] == "/tpr-config/settings.toml"
    assert run["environment"]["THEME_TEMPLATES_TEMPLATES_DIR"] == "/templates"
    assert run["environment"]["THEME__RUNTIME__MODE"] == "local"

    mounts = {mount.target: mount for mount in run["mounts"]}
    assert set(mounts) == {"/input", "/output", "/tpr-config/settings.toml", "/templates"}
    assert mounts["/input"].read_only is True
    assert mounts["/output"].read_only is False
    assert mounts["/tpr-config/settings.toml"].source.exists() is False  # cleaned in finally
    config_text = mounts["/tpr-config/settings.toml"].source
    assert not config_text.exists()
