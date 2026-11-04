import os
from pathlib import Path

# Symbols for visual tree representation
space = "    "
branch = "│   "
tee = "├── "
last = "└── "


def tree(dir_path, prefix: str = ""):
    """A recursive generator that, given a directory Path object,
    will yield a visual tree structure line by line
    with each line prefixed by the same characters.
    """
    contents = list(dir_path.iterdir())
    # contents each get pointers that are ├── with a final └── :
    pointers = [tee] * (len(contents) - 1) + [last]
    for pointer, path in zip(pointers, contents):
        yield prefix + pointer + path.name
        if path.is_dir():  # Extend the prefix and recurse:
            extension = branch if pointer == tee else space
            # i.e. space because last, └── , above so no more |
            yield from tree(path, prefix=prefix + extension)


"""
Flow chart for the project
"""
from pathlib import Path
import ast
import re
from graphviz import Digraph
from collections import deque, defaultdict


def extract_io_python(file_path: Path):
    """
    Extract pandas I/O calls from Python files using AST parsing.
    Skips files with syntax errors or encoding issues.
    Captures both literal paths and variable-based paths using ast.unparse.
    """
    if file_path.name.lower() == "config.py":
        return set(), set()
    try:
        text = file_path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return set(), set()

    inputs, outputs = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func_name = node.func.attr.lower()
            is_read = func_name.startswith("read_")
            is_write = func_name.startswith("to_")
            if (is_read or is_write) and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    path_str = arg.value
                else:
                    try:
                        path_str = ast.unparse(arg)
                    except Exception:
                        continue
                if is_read:
                    inputs.add(path_str)
                if is_write:
                    outputs.add(path_str)
    return inputs, outputs


def extract_io_stata(file_path: Path):
    """
    Extract Stata I/O commands from .do files via regex.
    Skips files with encoding issues.
    """
    if file_path.name.lower() == "config.do":
        return set(), set()
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set(), set()
    inputs, outputs = set(), set()
    pattern_use = re.compile(
        r"^\s*(use|import\s+delimited)\s+['\"]([^'\"]+)['\"]", re.IGNORECASE
    )
    pattern_save = re.compile(
        r"^\s*(save|export\s+delimited)\s+['\"]([^'\"]+)['\"]", re.IGNORECASE
    )
    for line in text.splitlines():
        m_in = pattern_use.search(line)
        if m_in:
            inputs.add(m_in.group(2))
        m_out = pattern_save.search(line)
        if m_out:
            outputs.add(m_out.group(2))
    return inputs, outputs


def extract_io_r(file_path: Path):
    """
    Extract R I/O calls from .r and .rscript files via regex.
    Skips files with encoding issues.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set(), set()
    inputs, outputs = set(), set()
    for read_fn in [r"read\.csv", r"read\.table", r"readr::read_csv"]:
        for m in re.finditer(read_fn + r"\(\s*['\"]([^'\"]+)['\"]", text):
            inputs.add(m.group(1))
    for write_fn in [r"write\.csv", r"write\.table", r"readr::write_csv"]:
        for m in re.finditer(write_fn + r"\(.*?['\"]([^'\"]+)['\"]", text, re.DOTALL):
            outputs.add(m.group(1))
    return inputs, outputs


def sanitize_id(path: str) -> str:
    """
    Create a Graphviz-safe node ID by replacing unsafe characters.
    """
    return re.sub(r"[^0-9A-Za-z_]", "_", path)


def build_data_flow_graph(folders):
    """
    Scans folders, builds a directed graph of I/O, computes levels, and renders layout.
    """
    # Collect nodes and edges
    nodes = {}  # id -> {'label':..., 'type':'code'|'data'}
    edges = []  # (src_id, dst_id, bidir)
    incoming = defaultdict(set)
    outgoing = defaultdict(set)

    for folder in folders:
        base = Path(folder)
        for f in base.rglob("*"):
            suffix = f.suffix.lower()
            if suffix == ".py":
                ins, outs = extract_io_python(f)
            elif suffix == ".do":
                ins, outs = extract_io_stata(f)
            elif suffix in {".r", ".rscript"}:
                ins, outs = extract_io_r(f)
            else:
                continue
            code_label = str(f.relative_to(base))
            code_id = sanitize_id(code_label)
            nodes[code_id] = {"label": code_label, "type": "code"}
            # add data nodes and edges
            for p in ins & outs:
                data_id = sanitize_id(p)
                nodes[data_id] = {"label": p, "type": "data"}
                # bidirectional
                edges.append((data_id, code_id, True))
                outgoing[data_id].add(code_id)
                incoming[code_id].add(data_id)
                edges.append((code_id, data_id, True))
                outgoing[code_id].add(data_id)
                incoming[data_id].add(code_id)
            only_ins = ins - outs
            only_outs = outs - ins
            for p in only_ins:
                data_id = sanitize_id(p)
                nodes[data_id] = {"label": p, "type": "data"}
                edges.append((data_id, code_id, False))
                outgoing[data_id].add(code_id)
                incoming[code_id].add(data_id)
            for p in only_outs:
                data_id = sanitize_id(p)
                nodes[data_id] = {"label": p, "type": "data"}
                edges.append((code_id, data_id, False))
                outgoing[code_id].add(data_id)
                incoming[data_id].add(code_id)

    # Identify root inputs (data nodes with no incoming)
    queue = deque()
    levels = {}
    for nid, info in nodes.items():
        if info["type"] == "data" and not incoming[nid]:
            levels[nid] = 0
            queue.append(nid)
    # BFS to assign levels
    while queue:
        u = queue.popleft()
        for v in outgoing[u]:
            if v not in levels:
                levels[v] = levels[u] + 1
                queue.append(v)

    # Create graphviz
    dot = Digraph(comment="Data Flow Diagram")
    dot.attr(rankdir="LR")
    for nid, info in nodes.items():
        style = {"shape": "ellipse"} if info["type"] == "data" else {"shape": "box"}
        color = "#CC99FF" if info["type"] == "data" else "#4C9AFF"
        dot.node(
            nid,
            info["label"],
            style="filled",
            fillcolor=color,
            fontcolor="white",
            **style,
        )
    # Add edges with weight=level of destination
    for src, dst, bidir in edges:
        wt = levels.get(dst, 1)
        if bidir:
            dot.edge(src, dst, dir="both", weight=str(wt))
        else:
            dot.edge(src, dst, dir="forward", weight=str(wt))

    return dot


def generate_data_flow_diagram(
    paths, output="data_flow_diagram", fmt="png", cleanup=True
):
    graph = build_data_flow_graph(paths)
    return graph.render(output, format=fmt, cleanup=cleanup)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    for line in tree(root / "code"):
        print(line)
    file_path = generate_data_flow_diagram(
        [root / "code"], output=str(root / "combined_flow")
    )
    print(f"Generated diagram at {file_path}")
