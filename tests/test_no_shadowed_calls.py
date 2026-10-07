"""No function assigns (or takes as a parameter) a name it also calls as a module-level function or import: the local
name would hide it and the call fails only when that path first runs (`playoffs.build(write=...)` and
`season_close.close` with a local `path`, both found on the career's first 2005 playoff day)."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _bound_names(target):
    """Names a target binds: a bare name or a tuple of them (not names used inside a subscript or attribute)."""
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return set().union(*(_bound_names(t) for t in target.elts)) if target.elts else set()
    if isinstance(target, ast.Starred):
        return _bound_names(target.value)
    return set()


def shadowed(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    module = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            module |= {(a.asname or a.name).split(".")[0] for a in n.names}
    out = []
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        bound = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    bound |= _bound_names(t)
            elif isinstance(n, (ast.AnnAssign, ast.AugAssign, ast.For)):
                bound |= _bound_names(n.target)
            elif isinstance(n, ast.With):
                for item in n.items:
                    if item.optional_vars is not None:
                        bound |= _bound_names(item.optional_vars)
        called = {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        clash = bound & module & called
        if clash:
            out.append(f"{path.relative_to(ROOT)}: {fn.name} hides {sorted(clash)}")
    return out


class ShadowedCallTests(unittest.TestCase):
    def test_no_local_name_hides_a_called_function(self):
        problems = [p for f in sorted(ROOT.glob("runtime/*.py")) + sorted(ROOT.glob("scripts/*.py")) for p in shadowed(f)]
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
