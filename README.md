# cura-p1s

CuraEngine printer definition and G-code template resolver for the Bambu Lab P1S.

## Install

```sh
pipx install cura-p1s
```

## Commands

### `cura-p1s resolve` — resolve G-code template variables

CuraEngine 5.12.x does not resolve template variables (`{material_print_temperature_layer_0}`,
`{if ...}...{endif}`, etc.) in start/end G-code. This command resolves them using the same
syntax as CuraEngine's native `GcodeTemplateResolver` (available on CuraEngine `main`, not yet
released).

```sh
# Resolve templates in-place using a settings JSON file
cura-p1s resolve output.gcode --settings cura_settings.json

# Resolve with individual settings
cura-p1s resolve output.gcode --set material_bed_temperature_layer_0=60 --set material_type=PLA

# Strict mode: error if any unresolved tokens remain
cura-p1s resolve output.gcode --settings cura_settings.json --strict

# Output to a different file instead of in-place
cura-p1s resolve output.gcode --settings cura_settings.json -o resolved.gcode
```

#### With estampo

estampo writes `cura_settings.json` after slicing. Add a command stage to your `estampo.toml`:

```toml
[pipeline]
stages = ["load", "arrange", "plate", "slice", "resolve_templates", "pack"]

[resolve_templates]
command = "cura-p1s resolve {sliced_dir}/plate.gcode --settings {cura_settings}"
```

When CuraEngine ships a release with native template resolution, remove the
`resolve_templates` stage — no other changes needed.

### `cura-p1s defs` — list or locate printer definitions

```sh
# List bundled definition files
cura-p1s defs

# Print the directory path (for importing into estampo)
cura-p1s defs --path
```

## Template syntax

Supports the same syntax as CuraEngine's `GcodeTemplateResolver`:

| Syntax | Example | Description |
|--------|---------|-------------|
| `{variable}` | `{material_bed_temperature_layer_0}` | Variable substitution |
| `{expression}` | `{speed_print * 60}` | Arithmetic (`+`, `-`, `*`, `/`, `%`) |
| `{if cond}...{endif}` | `{if material_type == "PLA"}...{endif}` | Conditional block |
| `{if}...{elif}...{else}...{endif}` | | Full conditional chain |
| Comparisons | `==`, `!=`, `<`, `>`, `<=`, `>=` | In conditions |

## Printer definition files

- `bambox_p1s.def.json` — machine definition for a P1S **without AMS** (single extruder, 0.4mm nozzle). AMS-specific start/end G-code (`M620`/`M621` material-switch sequences) is stripped so the printer does not hang waiting for a non-existent AMS unit.
- `bambox_p1s_ams.def.json` — P1S **with AMS** variant. Inherits from `bambox_p1s` and re-adds the AMS-aware start/end G-code. Select this profile if you print via an AMS / AMS-Lite.
- `bambox_p1s_extruder_0.def.json` — extruder definition (shared by both variants)

## bambox hint

The start G-code includes comment lines for [bambox](https://github.com/estampo/bambox):

```gcode
; BAMBOX_PRINTER=p1s
; BAMBOX_END
```

These allow `bambox pack` to auto-derive the Bambu firmware `printer_model_id`.

## License

AGPL-3.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE) for attribution.
