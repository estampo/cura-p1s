# cura-p1s

CuraEngine printer definition for the Bambu Lab P1S.

## Files

- `bambox_p1s.def.json` — machine definition (single extruder, 0.4mm nozzle)
- `bambox_p1s_extruder_0.def.json` — extruder definition

## Usage

Pass the directory containing these files to CuraEngine's `-d` flag:

```sh
CuraEngine slice \
  -d /path/to/cura-p1s:/path/to/cura/definitions \
  -j /path/to/cura-p1s/bambox_p1s.def.json \
  -s material_type=PLA \
  -s material_print_temperature_layer_0=220 \
  -s material_bed_temperature_layer_0=55 \
  -o output.gcode \
  -g -e0 -l model.stl
```

## Template variables

The start/end gcode uses standard CuraEngine template syntax:

- `{material_print_temperature_layer_0}`, `{material_bed_temperature_layer_0}` — temperatures
- `{material_type}` — filament type (used for PLA fan prevention)
- `{machine_buildplate_type}` — build plate (used for textured PEI Z offset)
- `{machine_height}` — Z height for bed drop in end gcode
- `{speed_print}` — print speed (used for purge line feedrate)
- `{if condition}`/`{endif}` — conditionals

These require CuraEngine built with `cura-formulae-engine` (not available in CuraEngine 5.12.0; available on CuraEngine main as of April 2026).

## bambox hint

The start gcode includes two comment lines for [bambox](https://github.com/estampo/bambox) integration:

```gcode
; BAMBOX_PRINTER=p1s
; BAMBOX_END
```

These allow `bambox pack` to auto-derive the Bambu firmware `printer_model_id` (`C12` for P1S). They are plain gcode comments and have no effect on CuraEngine or the printer.

## License

MIT
