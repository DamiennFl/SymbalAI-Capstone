import os
import io
import re
import ast
import tokenize

CODING_RE = re.compile(r"coding[:=]\s*([-\w.]+)")

def normalize_ws(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    out = []
    blank = False
    for ln in lines:
        if ln.strip() == "":
            if not blank:
                out.append("")
                blank = True
        else:
            out.append(ln)
            blank = False
    while out and out[0] == "":
        out.pop(0)
    return ("\n".join(out) + "\n") if out else ""

def extract_preamble(code: str):
    lines = code.splitlines()
    pre, i = [], 0
    if i < len(lines) and lines[i].startswith("#!"):
        pre.append(lines[i]); i += 1
    for j in range(i, min(i + 2, len(lines))):
        if CODING_RE.search(lines[j]) and lines[j].lstrip().startswith("#"):
            pre.append(lines[j])
            i = j + 1
            break
    rest = "\n".join(lines[i:]) + ("\n" if i < len(lines) else "")
    return pre, rest

class StripStringExpr(ast.NodeTransformer):
    def _strip_in_body(self, body):
        new = []
        for stmt in body:
            stmt = self.visit(stmt) or stmt
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue
            new.append(stmt)
        if not new:
            new = [ast.Pass()]
            ast.copy_location(new[0], body[0] if body else ast.parse("pass").body[0])
        return new

    def _maybe_strip_attr(self, node, attr):
        if hasattr(node, attr):
            seq = getattr(node, attr)
            if isinstance(seq, list):
                setattr(node, attr, self._strip_in_body(seq))
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        node.body = [s for s in node.body
                     if not (isinstance(s, ast.Expr)
                             and isinstance(s.value, ast.Constant)
                             and isinstance(s.value.value, str))]
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return self._maybe_strip_attr(node, "body")

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        return self._maybe_strip_attr(node, "body")

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        return self._maybe_strip_attr(node, "body")

    def visit_With(self, node):
        self.generic_visit(node)
        return self._maybe_strip_attr(node, "body")

    def visit_AsyncWith(self, node):
        self.generic_visit(node)
        return self._maybe_strip_attr(node, "body")

    def visit_For(self, node):
        self.generic_visit(node)
        self._maybe_strip_attr(node, "body")
        self._maybe_strip_attr(node, "orelse")
        return node

    def visit_AsyncFor(self, node):
        self.generic_visit(node)
        self._maybe_strip_attr(node, "body")
        self._maybe_strip_attr(node, "orelse")
        return node

    def visit_While(self, node):
        self.generic_visit(node)
        self._maybe_strip_attr(node, "body")
        self._maybe_strip_attr(node, "orelse")
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        self._maybe_strip_attr(node, "body")
        if isinstance(node.orelse, list) and not node.orelse:
            node.orelse = []
        return node

    def visit_Try(self, node):
        self.generic_visit(node)
        self._maybe_strip_attr(node, "body")
        self._maybe_strip_attr(node, "orelse")
        self._maybe_strip_attr(node, "finalbody")
        for h in node.handlers:
            self._maybe_strip_attr(h, "body")
        return node

def strip_hash_comments(code: str) -> str:
    out = []
    sio = io.StringIO(code)
    try:
        for tok in tokenize.generate_tokens(sio.readline):
            if tok.type == tokenize.COMMENT:
                continue
            out.append(tok)
    except tokenize.TokenError:
        return code
    return tokenize.untokenize(out)

def read_text_and_encoding(path):
    with open(path, "rb") as bf:
        raw = bf.read()
    enc, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
    return raw.decode(enc), enc, raw

def remove_comments_and_strings(code: str) -> str:
    pre_lines, _ = extract_preamble(code)
    no_hash = strip_hash_comments(code)
    try:
        tree = ast.parse(no_hash)
        tree = StripStringExpr().visit(tree)
        ast.fix_missing_locations(tree)
        body_unparsed = ast.unparse(tree)
    except Exception:
        body_unparsed = no_hash

    preamble = "\n".join(pre_lines) + ("\n" if pre_lines else "")
    cleaned = preamble + body_unparsed
    return normalize_ws(cleaned)

def process_file(filepath):
    try:
        code, enc, raw = read_text_and_encoding(filepath)
        cleaned = remove_comments_and_strings(code)
    except Exception as e:
        print(f"SKIP (error): {filepath}: {e}")
        return

    if cleaned == code:
        return

    backup_path = filepath + ".bak"
    with open(backup_path, "wb") as b:
        b.write(raw)
    with open(filepath, "w", encoding=enc, newline="") as f:
        f.write(cleaned)
    print(f"Processed: {filepath} (backup saved as {backup_path})")

def main(root="."):
    skip_dirs = {
        ".git", "__pycache__", ".venv", "venv", "env",
        ".mypy_cache", ".pytest_cache",
    }
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            if name.endswith(".py") and name != os.path.basename(__file__):
                process_file(os.path.join(dirpath, name))

if __name__ == "__main__":
    main()
