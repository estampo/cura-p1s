"""Tests for CuraEngine G-code template resolver."""

import pytest

from cura_p1s.resolver import ResolveError, resolve, resolve_strict


class TestSimpleSubstitution:
    def test_single_variable(self):
        settings = {"material_bed_temperature_layer_0": 60}
        assert resolve("M140 S{material_bed_temperature_layer_0}", settings) == "M140 S60"

    def test_multiple_variables(self):
        gcode = (
            "M140 S{material_bed_temperature_layer_0}\nM104 S{material_print_temperature_layer_0}\n"
        )
        settings = {
            "material_bed_temperature_layer_0": 60,
            "material_print_temperature_layer_0": 220,
        }
        result = resolve(gcode, settings)
        assert "M140 S60" in result
        assert "M104 S220" in result

    def test_string_variable(self):
        result = resolve("; type={material_type}", {"material_type": "PLA"})
        assert result == "; type=PLA"

    def test_float_becomes_int_when_whole(self):
        result = resolve("{machine_nozzle_size}", {"machine_nozzle_size": 0.4})
        assert result == "0.4"

    def test_no_templates_unchanged(self):
        gcode = "G28\nG1 X0 Y0 Z0.2\n"
        assert resolve(gcode, {}) == gcode

    def test_unknown_variable_preserved(self):
        result = resolve("{unknown_var}", {})
        assert "{unknown_var}" in result


class TestArithmetic:
    def test_subtraction(self):
        settings = {"material_print_temperature_layer_0": 260}
        result = resolve("{material_print_temperature_layer_0 - 20}", settings)
        assert result == "240"

    def test_multiplication(self):
        result = resolve("{speed_print * 60}", {"speed_print": 100})
        assert result == "6000"

    def test_division(self):
        result = resolve("{speed_print / 2}", {"speed_print": 100})
        assert result == "50"

    def test_addition(self):
        result = resolve("{machine_height + 5}", {"machine_height": 250})
        assert result == "255"

    def test_complex_expression(self):
        result = resolve("{speed_print * 15}", {"speed_print": 60})
        assert result == "900"


class TestConditionals:
    def test_if_true(self):
        gcode = 'G28\n{if material_type == "PLA"}\nM106 S180\n{endif}\nG29\n'
        result = resolve(gcode, {"material_type": "PLA"})
        assert "M106 S180" in result
        assert "{if" not in result
        assert "{endif}" not in result

    def test_if_false(self):
        gcode = 'G28\n{if material_type == "PLA"}\nM106 S180\n{endif}\nG29\n'
        result = resolve(gcode, {"material_type": "PETG"})
        assert "M106 S180" not in result
        assert "G28" in result
        assert "G29" in result

    def test_if_else(self):
        gcode = '{if material_type == "PLA"}\nfan on\n{else}\nfan off\n{endif}\n'
        result_pla = resolve(gcode, {"material_type": "PLA"})
        assert "fan on" in result_pla
        assert "fan off" not in result_pla

        result_petg = resolve(gcode, {"material_type": "PETG"})
        assert "fan off" in result_petg
        assert "fan on" not in result_petg

    def test_if_elif_else(self):
        gcode = (
            '{if material_type == "PLA"}\nPLA mode\n'
            '{elif material_type == "PETG"}\nPETG mode\n'
            "{else}\nother mode\n{endif}\n"
        )
        assert "PLA mode" in resolve(gcode, {"material_type": "PLA"})
        assert "PETG mode" in resolve(gcode, {"material_type": "PETG"})
        assert "other mode" in resolve(gcode, {"material_type": "ABS"})

    def test_numeric_comparison(self):
        gcode = "{if material_bed_temperature_layer_0 > 45}\nM106 P3 S180\n{endif}\n"
        assert "M106 P3 S180" in resolve(gcode, {"material_bed_temperature_layer_0": 60})
        assert "M106 P3 S180" not in resolve(gcode, {"material_bed_temperature_layer_0": 40})

    def test_string_equality(self):
        gcode = '{if machine_buildplate_type == "textured_pei_plate"}\nG29.1 Z-0.04\n{endif}\n'
        assert "G29.1 Z-0.04" in resolve(gcode, {"machine_buildplate_type": "textured_pei_plate"})
        assert "G29.1 Z-0.04" not in resolve(gcode, {"machine_buildplate_type": "cool_plate"})

    def test_sequential_if_blocks(self):
        gcode = (
            '{if material_type == "PLA"}\nPLA block\n{endif}\n'
            "middle\n"
            '{if machine_buildplate_type == "textured_pei_plate"}\ntextured block\n{endif}\n'
        )
        settings = {"material_type": "PLA", "machine_buildplate_type": "textured_pei_plate"}
        result = resolve(gcode, settings)
        assert "PLA block" in result
        assert "middle" in result
        assert "textured block" in result


class TestBamboxP1sTemplates:
    """Test against actual templates from bambox_p1s.def.json."""

    SETTINGS = {
        "material_bed_temperature_layer_0": 60,
        "material_print_temperature_layer_0": 220,
        "material_print_temperature": 220,
        "material_type": "PLA",
        "machine_buildplate_type": "textured_pei_plate",
        "machine_height": 250,
        "machine_nozzle_size": 0.4,
        "speed_print": 100,
    }

    def test_bed_temp(self):
        gcode = (
            "M140 S{material_bed_temperature_layer_0}\nM190 S{material_bed_temperature_layer_0}\n"
        )
        result = resolve(gcode, self.SETTINGS)
        assert "M140 S60" in result
        assert "M190 S60" in result

    def test_nozzle_temp(self):
        gcode = "M104 S{material_print_temperature_layer_0}\n"
        result = resolve(gcode, self.SETTINGS)
        assert "M104 S220" in result

    def test_temp_minus_20(self):
        gcode = "M109 S{material_print_temperature_layer_0 - 20}\n"
        result = resolve(gcode, self.SETTINGS)
        assert "M109 S200" in result

    def test_speed_expressions(self):
        gcode = "G0 X240 E15 F{speed_print * 60}\nG0 Y11 E0.700 F{speed_print * 15}\n"
        result = resolve(gcode, self.SETTINGS)
        assert "F6000" in result
        assert "F1500" in result

    def test_machine_height(self):
        gcode = "G1 Z{machine_height} F600\nG1 Z{machine_height - 2}\n"
        result = resolve(gcode, self.SETTINGS)
        assert "G1 Z250 F600" in result
        assert "G1 Z248" in result

    def test_buildplate_comment(self):
        gcode = ";curr_bed_type={machine_buildplate_type}\n"
        result = resolve(gcode, self.SETTINGS)
        assert ";curr_bed_type=textured_pei_plate" in result

    def test_pla_fan_conditional(self):
        gcode = (
            '{if material_type == "PLA"}\n'
            "{if material_bed_temperature_layer_0 > 45}\n"
            "M106 P3 S180\n"
            "{endif}\n"
            ";Prevent PLA from jamming\n"
            "{endif}\n"
        )
        result = resolve(gcode, self.SETTINGS)
        assert "M106 P3 S180" in result
        assert ";Prevent PLA from jamming" in result

    def test_textured_pei_offset(self):
        gcode = (
            '{if machine_buildplate_type == "textured_pei_plate"}\n'
            "G29.1 Z-0.04 ; for Textured PEI Plate\n"
            "{endif}\n"
        )
        result = resolve(gcode, self.SETTINGS)
        assert "G29.1 Z-0.04" in result


class TestResolveStrict:
    def test_all_resolved_passes(self):
        result = resolve_strict("M140 S{temp}", {"temp": 60})
        assert result == "M140 S60"

    def test_unresolved_raises(self):
        with pytest.raises(ResolveError, match="Unresolved"):
            resolve_strict("{unknown_var}", {})

    def test_conditionals_not_flagged(self):
        gcode = "{if x == 1}\nhello\n{endif}\n"
        resolve_strict(gcode, {"x": 1})


class TestSafety:
    def test_rejects_function_calls(self):
        result = resolve("{__import__('os')}", {})
        assert "{__import__" in result

    def test_rejects_attribute_access(self):
        result = resolve("{foo.bar}", {})
        assert "{foo.bar}" in result
