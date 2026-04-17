"""CLI for cura-p1s: resolve CuraEngine G-code templates."""

from __future__ import annotations

import argparse
import importlib.resources
import json
import sys
from pathlib import Path


def _defs_path() -> Path:
    """Return the path to bundled printer definition files."""
    return Path(str(importlib.resources.files("cura_p1s") / "data"))


def _cmd_defs(args: argparse.Namespace) -> None:
    if args.path:
        print(_defs_path())
    else:
        for f in sorted(_defs_path().glob("*.def.json")):
            print(f.name)


def _cmd_resolve(args: argparse.Namespace) -> None:
    from cura_p1s.resolver import ResolveError, resolve, resolve_strict

    gcode_path = Path(args.gcode)
    if not gcode_path.exists():
        print(f"error: {gcode_path} not found", file=sys.stderr)
        sys.exit(1)

    settings: dict[str, object] = {}
    if args.settings:
        settings_path = Path(args.settings)
        if not settings_path.exists():
            print(f"error: {settings_path} not found", file=sys.stderr)
            sys.exit(1)
        with open(settings_path) as f:
            raw = json.load(f)
        for k, v in raw.items():
            if isinstance(v, str):
                try:
                    settings[k] = int(v)
                except ValueError:
                    try:
                        settings[k] = float(v)
                    except ValueError:
                        settings[k] = v
            else:
                settings[k] = v

    for kv in args.set or []:
        if "=" not in kv:
            print(f"error: --set value must be key=value, got: {kv}", file=sys.stderr)
            sys.exit(1)
        key, val = kv.split("=", 1)
        try:
            settings[key] = int(val)
        except ValueError:
            try:
                settings[key] = float(val)
            except ValueError:
                settings[key] = val

    gcode = gcode_path.read_text()

    try:
        if args.strict:
            resolved = resolve_strict(gcode, settings)
        else:
            resolved = resolve(gcode, settings)
    except ResolveError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(resolved)
    else:
        gcode_path.write_text(resolved)

    if args.output:
        print(f"Resolved → {args.output}", file=sys.stderr)
    else:
        print(f"Resolved → {gcode_path} (in-place)", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="cura-p1s",
        description="CuraEngine Bambu Lab P1S tools",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )
    sub = parser.add_subparsers(dest="command")

    # defs
    defs_p = sub.add_parser("defs", help="List or locate bundled printer definitions")
    defs_p.add_argument("--path", action="store_true", help="Print definitions directory path")

    # resolve
    res_p = sub.add_parser("resolve", help="Resolve CuraEngine template variables in G-code")
    res_p.add_argument("gcode", help="Path to G-code file")
    res_p.add_argument("--settings", help="Path to CuraEngine settings JSON file")
    res_p.add_argument("--set", action="append", help="Set a variable: key=value (repeatable)")
    res_p.add_argument("-o", "--output", help="Output file (default: in-place)")
    res_p.add_argument("--strict", action="store_true", help="Error if unresolved tokens remain")

    args = parser.parse_args(argv)

    if args.command == "defs":
        _cmd_defs(args)
    elif args.command == "resolve":
        _cmd_resolve(args)
    else:
        parser.print_help()
        sys.exit(1)


def _get_version() -> str:
    try:
        from cura_p1s import __version__

        return __version__
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    main()
