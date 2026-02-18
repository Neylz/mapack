from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(slots=True)
class ExpressionContext:
    cwd: Path


_ALLOWED_BOOL_NAMES = {
    "true": True,
    "false": False,
    "null": None,
    "none": None,
}


class SafeExpressionEvaluator(ast.NodeVisitor):
    def __init__(self, *, functions: dict[str, Callable[..., Any]]) -> None:
        self.functions = functions

    def visit_Expression(self, node: ast.Expression) -> Any:  # noqa: N802
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:  # noqa: N802
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:  # noqa: N802
        key = node.id.casefold()
        if key in _ALLOWED_BOOL_NAMES:
            return _ALLOWED_BOOL_NAMES[key]
        raise ValueError(f"Unknown name in expression: {node.id}")

    def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are supported")
        if node.func.id not in self.functions:
            raise ValueError(f"Function not allowed: {node.func.id}")

        fn = self.functions[node.func.id]
        args = [self.visit(arg) for arg in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords if kw.arg is not None}
        return fn(*args, **kwargs)

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def evaluate_expression(text: str, *, context: ExpressionContext) -> Any:
    def count_files(path: str, recursive: bool = True, include_dirs: bool = False) -> int:
        root = (context.cwd / path).resolve()
        if not root.exists():
            return 0

        total = 0
        if recursive:
            for child in root.rglob("*"):
                if child.is_file() or (include_dirs and child.is_dir()):
                    total += 1
        else:
            for child in root.iterdir():
                if child.is_file() or (include_dirs and child.is_dir()):
                    total += 1
        return total

    tree = ast.parse(text, mode="eval")
    evaluator = SafeExpressionEvaluator(functions={"count_files": count_files})
    return evaluator.visit(tree)
