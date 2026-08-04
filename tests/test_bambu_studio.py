from pathlib import Path

from tools.bambu_studio import absolute_existing_paths, gui_environment


def test_existing_relative_input_is_made_absolute(tmp_path: Path) -> None:
    project = tmp_path / "QuenaCase.3mf"
    project.touch()

    assert absolute_existing_paths([project.name], cwd=tmp_path) == [str(project)]


def test_options_and_missing_outputs_are_unchanged(tmp_path: Path) -> None:
    arguments = ["--debug", "1", "--export-3mf", "new-project.3mf"]

    assert absolute_existing_paths(arguments, cwd=tmp_path) == arguments


def test_gui_disables_webkit_dmabuf_without_forcing_software_gl(
    monkeypatch,
) -> None:
    monkeypatch.setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "0")
    monkeypatch.delenv("LIBGL_ALWAYS_SOFTWARE", raising=False)

    env = gui_environment()

    assert env["WEBKIT_DISABLE_DMABUF_RENDERER"] == "1"
    assert "LIBGL_ALWAYS_SOFTWARE" not in env
