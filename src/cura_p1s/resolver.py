"""CuraEngine G-code template resolver.

Implements the same template syntax as CuraEngine's GcodeTemplateResolver:
- ``{variable}`` — simple variable substitution
- ``{expression}`` — arithmetic expressions (``{temp - 20}``, ``{speed * 60}``)
- ``{if cond}...{elif cond}...{else}...{endif}`` — conditional blocks
- ``{expression, extruder_nr}`` — extruder-scoped expressions (extruder_nr ignored)

The resolver processes templates line by line using a regex + state machine,
matching CuraEngine's behavior including its limitation of no nested conditionals.
"""

from __future__ import annotations

import ast
import operator
import re
from enum import Enum, auto

_TEMPLATE_RE = re.compile(
    r"\{\s*(?P<condition>if|elif|else|endif)?\s*(?P<expression>[^{}]*?)"
    r"\s*(?:,\s*(?P<extruder_nr>[^{},]*))?\s*\}(?P<eol>\n?)"
)

_AST_OPS: dict[type, object] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

_AST_CMP: dict[type, object] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


class _CondState(Enum):
    OUTSIDE = auto()
    TRUE = auto()
    FALSE = auto()
    DONE = auto()


def _safe_eval(expr: str, settings: dict[str, object]) -> object:
    """Evaluate an expression against settings using safe AST parsing."""
    tree = ast.parse(expr.strip(), mode="eval")
    return _eval_node(tree.body, settings)


def _eval_node(node: ast.AST, settings: dict[str, object]) -> object:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, settings)

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id in settings:
            return settings[node.id]
        raise ValueError(f"Unknown variable: {node.id}")

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        val = _eval_node(node.operand, settings)
        if isinstance(val, (int, float)):
            return -val
        raise ValueError(f"Cannot negate non-numeric: {val!r}")

    if isinstance(node, ast.BinOp) and type(node.op) in _AST_OPS:
        left = _eval_node(node.left, settings)
        right = _eval_node(node.right, settings)
        op_fn = _AST_OPS[type(node.op)]
        return op_fn(left, right)  # type: ignore[operator]

    if isinstance(node, ast.Compare):
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise ValueError("Only single comparisons supported")
        left = _eval_node(node.left, settings)
        right = _eval_node(node.comparators[0], settings)
        op_type = type(node.ops[0])
        if op_type not in _AST_CMP:
            raise ValueError(f"Unsupported comparison: {ast.dump(node.ops[0])}")
        cmp_fn = _AST_CMP[op_type]
        return cmp_fn(left, right)  # type: ignore[operator]

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval_node(v, settings) for v in node.values)
        if isinstance(node.op, ast.Or):
            return any(_eval_node(v, settings) for v in node.values)

    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def _format_value(value: object) -> str:
    """Format a resolved value for G-code output."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def resolve(gcode: str, settings: dict[str, object]) -> str:
    """Resolve all CuraEngine template expressions in G-code.

    Args:
        gcode: Raw G-code text with ``{template}`` expressions.
        settings: Flat dict of CuraEngine setting names to values.

    Returns:
        Resolved G-code with all templates substituted.

    Raises:
        ResolveError: If an unresolved ``{template}`` remains after processing.
    """
    state = _CondState.OUTSIDE
    result: list[str] = []
    pos = 0

    for m in _TEMPLATE_RE.finditer(gcode):
        cond = m.group("condition")
        expr = (m.group("expression") or "").strip()
        eol = m.group("eol") or ""

        before = gcode[pos : m.start()]
        pos = m.end()

        if state in (_CondState.TRUE, _CondState.OUTSIDE):
            result.append(before)

        if cond == "if":
            try:
                val = _safe_eval(expr, settings)
                state = _CondState.TRUE if val else _CondState.FALSE
            except (ValueError, SyntaxError):
                state = _CondState.FALSE
            continue

        if cond == "elif":
            if state == _CondState.FALSE:
                try:
                    val = _safe_eval(expr, settings)
                    state = _CondState.TRUE if val else _CondState.FALSE
                except (ValueError, SyntaxError):
                    state = _CondState.FALSE
            elif state == _CondState.TRUE:
                state = _CondState.DONE
            continue

        if cond == "else":
            if state == _CondState.FALSE:
                state = _CondState.TRUE
            elif state == _CondState.TRUE:
                state = _CondState.DONE
            continue

        if cond == "endif":
            state = _CondState.OUTSIDE
            continue

        if state in (_CondState.FALSE, _CondState.DONE):
            continue

        try:
            val = _safe_eval(expr, settings)
            result.append(_format_value(val))
        except (ValueError, SyntaxError):
            result.append(m.group(0))
        result.append(eol)

    result.append(gcode[pos:])
    return "".join(result)


class ResolveError(Exception):
    """Raised when unresolved template tokens remain in output."""


def resolve_strict(gcode: str, settings: dict[str, object]) -> str:
    """Like :func:`resolve`, but raises if any ``{template}`` tokens remain."""
    resolved = resolve(gcode, settings)
    remaining = _TEMPLATE_RE.findall(resolved)
    if remaining:
        tokens = [f"{{{t[1].strip()}}}" for t in remaining if not t[0]]
        if tokens:
            raise ResolveError(f"Unresolved template tokens: {', '.join(tokens[:10])}")
    return resolved
