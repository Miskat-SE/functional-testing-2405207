"""Small mutation-testing harness for target.py.

It creates "faulty versions" of target.py (one small change each, such as
``>=`` -> ``>``, ``/`` -> ``//``, a removed ``raise`` or a changed constant),
runs the test suite against every version and reports any mutant that the
tests fail to catch ("survivors").

Usage:
    python scripts/mutation_test.py            # run every mutant
    python scripts/mutation_test.py --list     # only list the mutants

The original target.py is never modified: every mutant is written to a
temporary directory that is put first on PYTHONPATH.
"""

from __future__ import annotations

import argparse
import ast
import copy
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "target.py"

COMPARE_SWAPS = {
    ast.Lt: [ast.LtE, ast.Gt],
    ast.LtE: [ast.Lt],
    ast.Gt: [ast.GtE],
    ast.GtE: [ast.Gt, ast.Lt],
    ast.Eq: [ast.NotEq],
    ast.NotEq: [ast.Eq],
    ast.In: [ast.NotIn],
    ast.NotIn: [ast.In],
}
BINOP_SWAPS = {
    ast.Add: [ast.Sub, ast.Mult],
    ast.Sub: [ast.Add],
    ast.Mult: [ast.Div, ast.Add],
    ast.Div: [ast.FloorDiv, ast.Mult],
    ast.Mod: [ast.FloorDiv],
    ast.Pow: [ast.Mult],
    ast.BitAnd: [ast.BitOr, ast.BitXor, ast.Sub],
}
CALL_SWAPS = {"max": "min", "round": "int", "sum": "len", "len": "sum"}

# Mutants that cannot change behaviour for any input (multiplying by 1 is a
# no-op, so starting the factorial product at 2 gives identical results).
KNOWN_EQUIVALENT = ["math.prod(range(2, n + 1))"]

Mutation = tuple[str, Callable[[ast.Module], None]]


def _node_at(tree: ast.Module, index: int) -> ast.AST:
    return list(ast.walk(tree))[index]


def mutations(tree: ast.Module) -> Iterator[Mutation]:
    for index, node in enumerate(ast.walk(tree)):
        line = getattr(node, "lineno", "?")

        if isinstance(node, ast.Compare):
            for op_index, op in enumerate(node.ops):
                for new in COMPARE_SWAPS.get(type(op), []):

                    def apply(t, i=index, j=op_index, n=new):
                        _node_at(t, i).ops[j] = n()

                    yield f"L{line}: {type(op).__name__} -> {new.__name__}", apply

        elif isinstance(node, ast.BinOp):
            for new in BINOP_SWAPS.get(type(node.op), []):

                def apply(t, i=index, n=new):
                    _node_at(t, i).op = n()

                yield f"L{line}: {type(node.op).__name__} -> {new.__name__}", apply

        elif isinstance(node, ast.BoolOp):
            new = ast.Or if isinstance(node.op, ast.And) else ast.And

            def apply(t, i=index, n=new):
                _node_at(t, i).op = n()

            yield f"L{line}: {type(node.op).__name__} -> {new.__name__}", apply

        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):

            def apply(t, i=index):
                target_node = _node_at(t, i)
                target_node.op = ast.UAdd()
                target_node.operand = ast.Call(
                    ast.Name("bool", ast.Load()), [target_node.operand], []
                )

            yield f"L{line}: remove 'not'", apply

        elif isinstance(node, ast.Constant) and type(node.value) in (int, float):
            for delta in (1, -1):

                def apply(t, i=index, d=delta):
                    _node_at(t, i).value += d

                yield f"L{line}: constant {node.value} -> {node.value + delta}", apply

        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value and "target.py" not in node.value:

                def apply(t, i=index):
                    _node_at(t, i).value = _node_at(t, i).value[:-1]

                yield f"L{line}: string {node.value!r} truncated", apply

        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in CALL_SWAPS:
                new_name = CALL_SWAPS[func.id]

                def apply(t, i=index, n=new_name):
                    call = _node_at(t, i)
                    call.func = ast.Name(n, ast.Load())
                    if n == "int":
                        call.args = call.args[:1]

                yield f"L{line}: {func.id}() -> {new_name}()", apply
            if isinstance(func, ast.Attribute) and func.attr in ("strip", "lower"):

                def apply_drop(t, i=index):
                    call = _node_at(t, i)
                    value = call.func.value
                    call.func = ast.Name("str", ast.Load())
                    call.args = [value]

                yield f"L{line}: drop .{func.attr}()", apply_drop

        elif isinstance(node, ast.Raise):

            def apply(t, i=index):
                _node_at(t, i).exc = ast.Call(
                    ast.Name("RuntimeError", ast.Load()), [], []
                )

            yield f"L{line}: raise RuntimeError instead", apply

        elif isinstance(node, ast.If) and any(
            isinstance(stmt, ast.Raise) for stmt in node.body
        ):

            def apply(t, i=index):
                _node_at(t, i).test = ast.Constant(False)

            yield f"L{line}: guard clause removed", apply

        elif isinstance(node, ast.Return) and node.value is not None:

            def apply(t, i=index):
                _node_at(t, i).value = ast.Constant(None)

            yield f"L{line}: return None", apply

        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            if node.slice.value in (0, 1):

                def apply(t, i=index):
                    sub = _node_at(t, i)
                    sub.slice = ast.Constant(1 - sub.slice.value)

                yield f"L{line}: index [{node.slice.value}] swapped", apply

        elif isinstance(node, ast.Tuple) and isinstance(node.ctx, ast.Load):
            if len(node.elts) == 2:

                def apply(t, i=index):
                    tup = _node_at(t, i)
                    tup.elts.reverse()

                yield f"L{line}: tuple elements reversed", apply

        elif isinstance(node, ast.arguments) and node.defaults:

            def apply(t, i=index):
                _node_at(t, i).defaults = [ast.Constant("")]

            yield f"L{line}: default argument None -> ''", apply


def run_suite(mutant_dir: str) -> bool:
    """Return True when the suite FAILS (i.e. the mutant is killed)."""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([mutant_dir, str(ROOT)]))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-x",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:randomly",
            "--no-cov",
            str(ROOT / "tests" / "test_target.py"),
            "-o",
            "pythonpath=",
        ],
        cwd=mutant_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode != 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="only list mutants")
    args = parser.parse_args()

    source = TARGET.read_text(encoding="utf-8")
    original = ast.parse(source)
    all_mutations = list(mutations(original))

    if args.list:
        for name, _ in all_mutations:
            print(name)
        print(f"{len(all_mutations)} mutants")
        return 0

    survivors: list[str] = []
    equivalent: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for count, (name, apply) in enumerate(all_mutations, start=1):
            tree = copy.deepcopy(original)
            apply(tree)
            ast.fix_missing_locations(tree)
            mutant_source = ast.unparse(tree)
            if mutant_source == ast.unparse(original):
                continue
            Path(tmp, "target.py").write_text(mutant_source, encoding="utf-8")
            if any(snippet in mutant_source for snippet in KNOWN_EQUIVALENT):
                equivalent.append(name)
                print(f"[{count:3}/{len(all_mutations)}] equivalent {name}")
                continue
            killed = run_suite(tmp)
            status = "killed " if killed else "SURVIVED"
            print(f"[{count:3}/{len(all_mutations)}] {status} {name}")
            if not killed:
                survivors.append(name)

    total = len(all_mutations) - len(equivalent)
    print(f"\n{total - len(survivors)}/{total} mutants killed", end="")
    print(f" ({len(equivalent)} equivalent mutant(s) skipped)")
    for name in survivors:
        print(f"  survivor: {name}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
