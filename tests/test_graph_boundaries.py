import ast
from pathlib import Path
from _paths import SOURCE_ROOT

def _imports(path):
    tree=ast.parse(path.read_text(encoding="utf-8"))
    out=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.ImportFrom) and n.module:
            out.append((n.level,n.module))
    return out

def test_core_has_no_upward_domain_imports():
    root=SOURCE_ROOT/"core"
    forbidden=("composition","mix","analysis","revision","agent","app","pipeline")
    for p in root.glob("*.py"):
        for level,module in _imports(p):
            if level>=2 and module.split(".")[0] in forbidden:
                raise AssertionError(f"{p.name} imports upward: {module}")

def test_composer_revision_do_not_invoke_cli_subprocess():
    root=SOURCE_ROOT
    for rel in ("agent/composer_planner.py","agent/composition_brief.py"):
        text=(root/rel).read_text(encoding="utf-8")
        assert "subprocess" not in text
        assert "code_composer.cli" not in text


def _module_name(src_root, path):
    rel=path.relative_to(src_root).with_suffix("")
    if rel.name=="__init__":
        parts=rel.parts[:-1]
    else:
        parts=rel.parts
    return "code_composer" + (("."+".".join(parts)) if parts else "")


def _resolved_imports(src_root):
    modules={_module_name(src_root,p):p for p in src_root.rglob("*.py") if "__pycache__" not in p.parts}
    graph={m:set() for m in modules}
    for mod,path in modules.items():
        tree=ast.parse(path.read_text(encoding="utf-8"))
        is_pkg=path.name=="__init__.py"
        pkg=mod.split(".") if is_pkg else mod.split(".")[:-1]
        for n in ast.walk(tree):
            target=None
            if isinstance(n,ast.Import):
                for alias in n.names:
                    if alias.name.startswith("code_composer"):
                        t=alias.name
                        while t not in modules and "." in t:
                            t=t.rsplit(".",1)[0]
                        if t in modules and t!=mod:
                            graph[mod].add(t)
                continue
            if isinstance(n,ast.ImportFrom):
                if n.level:
                    base=pkg[:len(pkg)-(n.level-1)]
                    target=".".join(base+(([n.module] if n.module else [])))
                else:
                    target=n.module
                if target and target.startswith("code_composer"):
                    t=target
                    while t not in modules and "." in t:
                        t=t.rsplit(".",1)[0]
                    if t in modules and t!=mod:
                        graph[mod].add(t)
    return graph


def test_package_import_graph_has_no_cycles():
    src=SOURCE_ROOT
    graph=_resolved_imports(src)
    visiting=set(); done=set()
    def dfs(node,stack):
        if node in visiting:
            cycle=stack[stack.index(node):]+[node]
            raise AssertionError("import cycle: "+" -> ".join(cycle))
        if node in done:
            return
        visiting.add(node); stack.append(node)
        for nxt in graph[node]:
            dfs(nxt,stack)
        stack.pop(); visiting.remove(node); done.add(node)
    for node in graph:
        dfs(node,[])


def test_compatibility_shims_do_not_use_wildcard_exports():
    src=SOURCE_ROOT
    for path in src.glob("*.py"):
        if path.name in {"__init__.py","render.py"}:
            continue
        tree=ast.parse(path.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom):
                assert all(alias.name != "*" for alias in n.names), f"wildcard compatibility export: {path.name}"
def test_legacy_vocabulary_agent_surface_is_absent():
    root=SOURCE_ROOT
    forbidden=[
        root/"agent"/"agent_surface.py",
        root/"agent"/"agent_runner.py",
        root/"agent"/"agent_evaluation.py",
        root/"app"/"agent_cli.py",
        root/"agent_surface.py",
        root/"agent_runner.py",
        root/"agent_evaluation.py",
        root/"agent_cli.py",
        root/"core"/"resolve.py",
    ]
    assert all(not p.exists() for p in forbidden)
def test_runtime_source_contains_no_removed_vocabulary_parser():
    src=SOURCE_ROOT
    banned=("SECTION_ALIASES","parse_intent(","IntentSpec","STYLE_ALIASES","STYLE_PRESETS","STYLE_MATERIALS")
    offenders=[]
    for path in src.rglob("*.py"):
        text=path.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                offenders.append((str(path.relative_to(src)),token))
    assert offenders==[]


def test_single_resolver_implementation():
    src=SOURCE_ROOT
    implementations=[]
    for path in src.rglob("resolve.py"):
        text=path.read_text(encoding="utf-8")
        if "def resolve_ir(" in text:
            implementations.append(path.relative_to(src).as_posix())
    assert implementations==["composition/resolve.py"]

def test_legacy_automatic_revision_surface_is_absent():
    src=SOURCE_ROOT
    forbidden=[
        src/"revision",
        src/"revision_runner.py",
    ]
    assert all(not p.exists() for p in forbidden)

    banned=(
        "propose_from_issue",
        "apply_proposal",
        "try_proposal",
        "PatchOp",
        "class Proposal",
    )
    offenders=[]
    for path in src.rglob("*.py"):
        text=path.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                offenders.append((str(path.relative_to(src)),token))
    assert offenders==[]

