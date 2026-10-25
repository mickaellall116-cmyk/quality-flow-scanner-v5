"""P4 proof: the pine_backtest.py erratum is docstring-only.

Compares two versions of the file (argv: OLD NEW). Walks every code
object recursively and compares co_code, co_names, co_varnames,
co_flags and all constants EXCEPT docstrings (co_consts[0] of a code
object whose docstring changed, and the module docstring). Also diffs
the source with comment/docstring awareness: every changed line must
lie inside the module docstring.

Exit 0 iff executable content is identical.
"""
import difflib
import dis
import io
import sys
import types


def _norm_consts(code):
    out = []
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            out.append(("<code>", c.co_name))
        elif isinstance(c, str) and c == code.co_consts[0] \
                and code.co_name in ("<module>",) :
            out.append("<docstring>")
        else:
            out.append(repr(c))
    return out


def walk(code, path, acc):
    acc[path] = (
        code.co_code.hex(), code.co_names, code.co_varnames,
        code.co_flags, tuple(_norm_consts(code)))
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            walk(c, f"{path}.{c.co_name}", acc)


def code_map(src):
    code = compile(src, "<cmp>", "exec")
    acc = {}
    walk(code, "<module>", acc)
    return acc


def main():
    old_src = open(sys.argv[1]).read()
    new_src = open(sys.argv[2]).read()
    a, b = code_map(old_src), code_map(new_src)
    keys = set(a) | set(b)
    diffs = [k for k in sorted(keys) if a.get(k) != b.get(k)]
    # Second opinion: instruction streams with LOAD_CONST operands
    # masked and line numbers ignored (the docstring edit shifts the
    # line numbers of everything below it; co_code comparison above is
    # the primary evidence).
    def disasm(src):
        code = compile(src, "<cmp>", "exec")
        out = []
        def rec(c):
            for ins in dis.get_instructions(c):
                arg = type(ins.argval).__name__ \
                    if ins.opname == "LOAD_CONST" else ins.argrepr
                out.append((ins.opname, arg))
            for k in c.co_consts:
                if isinstance(k, types.CodeType):
                    rec(k)
        rec(code)
        return out
    da = disasm(old_src)
    db = disasm(new_src)
    # Changed source lines must all be inside the module docstring.
    sm = difflib.SequenceMatcher(None, old_src.splitlines(),
                                 new_src.splitlines())
    doc_end = old_src.split('"""')[0].count("\n"), None
    # module docstring spans from line 1 to the closing triple quote.
    close_line = None
    cnt = 0
    for i, ln in enumerate(old_src.splitlines(), 1):
        cnt += ln.count('"""')
        if cnt >= 2:
            close_line = i
            break
    changed_outside = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            for i in range(i1, i2):
                if not (1 <= i + 1 <= close_line):
                    changed_outside.append(i + 1)
    ok = not diffs and not changed_outside and da == db
    print(f"code objects compared: {len(keys)}; differing: {diffs}")
    print(f"instruction streams (LOAD_CONST masked, line numbers "
          f"ignored) identical: {da == db}")
    print(f"module docstring closes at line {close_line}; "
          f"changed lines outside docstring: {changed_outside}")
    print("P4_BYTECODE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
