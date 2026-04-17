"""Tests for cura-p1s CLI."""

import json

from cura_p1s.cli import main


def test_resolve_in_place(tmp_path):
    gcode = tmp_path / "test.gcode"
    gcode.write_text("M140 S{material_bed_temperature_layer_0}\n")
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"material_bed_temperature_layer_0": 60}))

    main(["resolve", str(gcode), "--settings", str(settings)])
    assert "M140 S60" in gcode.read_text()


def test_resolve_with_output(tmp_path):
    gcode = tmp_path / "test.gcode"
    gcode.write_text("M140 S{material_bed_temperature_layer_0}\n")
    out = tmp_path / "resolved.gcode"
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"material_bed_temperature_layer_0": 60}))

    main(["resolve", str(gcode), "--settings", str(settings), "-o", str(out)])
    assert "M140 S60" in out.read_text()
    assert "{material_bed_temperature_layer_0}" in gcode.read_text()


def test_resolve_with_set_flag(tmp_path):
    gcode = tmp_path / "test.gcode"
    gcode.write_text("M140 S{material_bed_temperature_layer_0}\n")

    main(["resolve", str(gcode), "--set", "material_bed_temperature_layer_0=60"])
    assert "M140 S60" in gcode.read_text()


def test_resolve_strict_fails(tmp_path):
    import pytest

    gcode = tmp_path / "test.gcode"
    gcode.write_text("{unknown_var}\n")

    with pytest.raises(SystemExit):
        main(["resolve", str(gcode), "--strict"])


def test_defs_list(capsys):
    main(["defs"])
    output = capsys.readouterr().out
    assert "bambox_p1s.def.json" in output
    assert "bambox_p1s_extruder_0.def.json" in output


def test_defs_path(capsys):
    main(["defs", "--path"])
    output = capsys.readouterr().out.strip()
    assert output.endswith("data")
