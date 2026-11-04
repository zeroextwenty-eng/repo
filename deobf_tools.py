"""
deobf_tools.py – wrappers for every deobfuscator on disk.

Each function takes `input_path` (str, existing file) and returns
(output_text: str, label: str) or raises RuntimeError on failure.
"""
import os
import subprocess
import sys
import tempfile
import shutil

# ── paths ───────────────────────────────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(_HERE, "tools")
DESKTOP = r"C:\Users\ZeroExTwenty\Desktop"

def _first_exist(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return paths[0] if paths else ""

HERCULES_PY   = _first_exist(
    os.path.join(TOOLS_DIR, "hercules", "deobfhercules.py"),
    os.path.join(DESKTOP, "hercules-deobfuscator-main", "hercules", "deobfhercules_fixed", "deobfhercules.py")
)
DEOBF_PY      = _first_exist(
    os.path.join(TOOLS_DIR, "deobfuscator", "deobf", "deob.py"),
    os.path.join(DESKTOP, "Deobfuscator", "deobf", "deob.py")
)
CLYDE_CLI     = _first_exist(
    os.path.join(TOOLS_DIR, "clyde", "cli.js"),
    os.path.join(DESKTOP, "ClydeDeobfuscator-main", "ClydeDeobfuscator-main", "cli.js")
)
PROMETHEUS_CLI= _first_exist(
    os.path.join(TOOLS_DIR, "prometheus", "bin", "pdeobf.js"),
    os.path.join(DESKTOP, "Prometheus-Deobfuscator-main", "Prometheus-Deobfuscator-main", "bin", "pdeobf.js")
)
PROMDEOBF_MAIN= _first_exist(
    os.path.join(TOOLS_DIR, "promdeobf", "promdeobf", "main.js"),
    os.path.join(DESKTOP, "promdeobf", "promdeobf", "main.js")
)
LUAOBF_CLI    = _first_exist(
    os.path.join(TOOLS_DIR, "luaobfuscator", "index.js"),
    os.path.join(DESKTOP, "LuaObfuscator-Deobfuscator-main", "LuaObfuscator-Deobfuscator-main", "index.js")
)
IRONVEIL_CLI  = _first_exist(
    os.path.join(TOOLS_DIR, "ironveil", "deobfuscator", "index.js"),
    os.path.join(DESKTOP, "Ironveil-Deobfuscator-V1-main", "Ironveil-Deobfuscator-V1-main", "deobfuscator", "index.js")
)
IB2_EXE       = _first_exist(
    os.path.join(TOOLS_DIR, "ib2", "ib2bot-main", "ib2deobf", "LuaAnalysis.Ironbrew2.exe"),
    os.path.join(DESKTOP, "ib2-deobf", "ib2bot-main", "ib2deobf", "LuaAnalysis.Ironbrew2.exe")
)
SEVENTYSEVEN_EXE = _first_exist(
    os.path.join(TOOLS_DIR, "77fuscator", "77fuscatorDeobfuscator-main", "bin", "Debug", "net8.0", "deobfuscator.exe"),
    os.path.join(DESKTOP, "77fuscatorDeobfuscator-main", "77fuscatorDeobfuscator-main", "bin", "Debug", "net8.0", "deobfuscator.exe")
)
VEIL_OBF_CLI = _first_exist(
    os.path.join(TOOLS_DIR, "veil", "src", "lib", "obfuscator", "cli.mjs"),
    os.path.join(DESKTOP, "veil-lua-obfuscator-leaked-by-null", "src", "lib", "obfuscator", "cli.mjs")
)
LURAPH_V15_1_JS = _first_exist(
    os.path.join(TOOLS_DIR, "luraph_v15_1", "v15_tool_attempt_source", "deob.js"),
    os.path.join(DESKTOP, "Luraph_v15_1_Deobfuscator_Newest", "v15_tool_attempt_source", "deob.js")
)
LUAGUARD_CLI    = _first_exist(
    os.path.join(TOOLS_DIR, "luaguard", "luaguard-unpack.mjs"),
    os.path.join(DESKTOP, "luaguard-unpack-main", "luaguard-unpack-main", "luaguard-unpack.mjs")
)
CENTURION_PY    = _first_exist(
    os.path.join(TOOLS_DIR, "centurion", "centurion.py"),
    os.path.join(DESKTOP, "centurion-deobfuscator", "centurion-deobfuscator", "centurion.py")
)
LUAU_BIN_DIR    = os.path.join(_HERE, "luau_bin")
# Moonveil and Moonsec are separate bots / require special flow – not wrapped here.


TIMEOUT = 120  # seconds per tool


def _run(cmd, cwd=None, timeout=TIMEOUT, input_data=None):
    """Run a command, return stdout str. Raises RuntimeError on failure."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, timeout=timeout,
            input=input_data,
        )
        out = (r.stdout or b"").decode("utf-8", "replace").strip()
        err = (r.stderr or b"").decode("utf-8", "replace").strip()
        if r.returncode != 0:
            raise RuntimeError(err or out or f"exit code {r.returncode}")
        return out
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"timed out after {timeout}s")
    except FileNotFoundError as e:
        raise RuntimeError(str(e))


def _node():
    local_node = os.path.join(_HERE, "bin", "node")
    if os.path.exists(local_node) and sys.platform.startswith("linux"):
        try: os.chmod(local_node, 0o755)
        except OSError: pass
        return local_node
    n = shutil.which("node")
    if n:
        return n
    return "node"


def _py():
    return sys.executable


# ── individual tools ─────────────────────────────────────────────────────────

def run_hercules(input_path: str) -> tuple[str, str]:
    """Hercules deobfuscator (Python, v1.6–v2.0)."""
    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as f:
        out_path = f.name
    try:
        _run([_py(), HERCULES_PY, input_path, out_path], timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), "Hercules"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


def run_luraph_ironbrew1(input_path: str) -> tuple[str, str]:
    """Deobfuscator (Luraph v15 / IronBrew1) – Python."""
    cwd = os.path.dirname(DEOBF_PY)
    _run([_py(), DEOBF_PY, input_path], cwd=cwd, timeout=TIMEOUT)
    # output goes to <input_folder>/output/<input_name>
    out_dir = os.path.join(os.path.dirname(input_path), "output")
    out_file = os.path.join(out_dir, os.path.basename(input_path))
    if not os.path.exists(out_file):
        raise RuntimeError("output file not found after deob.py run")
    with open(out_file, encoding="utf-8", errors="replace") as f:
        return f.read(), "Luraph/IronBrew1"


def run_clyde(input_path: str) -> tuple[str, str]:
    """Clyde deobfuscator (Node.js, V2–V6)."""
    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as f:
        out_path = f.name
    try:
        _run([_node(), CLYDE_CLI, input_path, "-o", out_path],
             cwd=os.path.dirname(CLYDE_CLI), timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), "Clyde"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


def run_prometheus(input_path: str) -> tuple[str, str]:
    """Prometheus deobfuscator (Node.js)."""
    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as f:
        out_path = f.name
    try:
        _run([_node(), PROMETHEUS_CLI, input_path, "-o", out_path],
             cwd=os.path.dirname(PROMETHEUS_CLI), timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), "Prometheus"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


def run_promdeobf(input_path: str) -> tuple[str, str]:
    """promdeobf (Node.js, alternate Prometheus deobfuscator with extra steps)."""
    # promdeobf reads from input.lua and writes to out.lua in its own folder.
    # We copy the file in, run it, read out.lua.
    cwd = os.path.dirname(PROMDEOBF_MAIN)
    dest = os.path.join(cwd, "input.lua")
    out_file = os.path.join(cwd, "out.lua")
    shutil.copy2(input_path, dest)
    try:
        _run([_node(), PROMDEOBF_MAIN], cwd=cwd, timeout=TIMEOUT)
        if not os.path.exists(out_file):
            raise RuntimeError("out.lua not produced by promdeobf")
        with open(out_file, encoding="utf-8", errors="replace") as f:
            return f.read(), "promdeobf (Prometheus alt)"
    finally:
        for p in (dest, out_file):
            try: os.unlink(p)
            except OSError: pass


def run_luaobfuscator(input_path: str) -> tuple[str, str]:
    """LuaObfuscator deobfuscator (Node.js – Chaotic Good/Evil)."""
    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as f:
        out_path = f.name
    try:
        _run([_node(), LUAOBF_CLI, input_path, "--out", out_path],
             cwd=os.path.dirname(LUAOBF_CLI), timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), "LuaObfuscator"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


def run_ironveil(input_path: str) -> tuple[str, str]:
    """Ironveil V1 deobfuscator (Node.js)."""
    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as f:
        out_path = f.name
    try:
        _run([_node(), IRONVEIL_CLI, input_path, out_path],
             cwd=os.path.dirname(IRONVEIL_CLI), timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), "Ironveil V1"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


def run_ironbrew2(input_path: str) -> tuple[str, str]:
    """IronBrew2 deobfuscator (pre-built .exe)."""
    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as f:
        out_path = f.name
    try:
        _run([IB2_EXE, input_path, out_path], timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), "IronBrew2"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


def run_77fuscator(input_path: str) -> tuple[str, str]:
    """77fuscator deobfuscator (pre-built .exe)."""
    with tempfile.NamedTemporaryFile(suffix=".luac", delete=False) as f:
        out_path = f.name
    try:
        _run([SEVENTYSEVEN_EXE, input_path, "-o", out_path], timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), "77fuscator"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


def run_luraph_v15_1(input_path: str) -> tuple[str, str]:
    """Luraph v15.1 Deobfuscator (Node.js + Luau)."""
    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as f:
        out_path = f.name
    try:
        env = dict(os.environ)
        env["PYTHON_BIN"] = sys.executable
        _run([_node(), LURAPH_V15_1_JS, input_path, "-o", out_path],
             cwd=os.path.dirname(LURAPH_V15_1_JS), timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), "Luraph v15.1"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


def run_baconguard(input_path: str) -> tuple[str, str]:
    """Bacon Guard / FORGE deobfuscator (Python + Luau VM sandbox)."""
    from bgdeobf.runner import run
    from bgdeobf.engine import Options, EngineError
    with open(input_path, "rb") as f:
        data = f.read()
    try:
        res = run(data, opts=Options(clean=True), hard_timeout=TIMEOUT)
        return res.text, "Bacon Guard / FORGE"
    except EngineError as e:
        raise RuntimeError(f"Bacon Guard engine error ({e.code}): {e.message}")
    except Exception as e:
        raise RuntimeError(str(e))


def run_luaguard(input_path: str) -> tuple[str, str]:
    """LuaGuard Unpacker (Node.js)."""
    out_dir = tempfile.mkdtemp(prefix="mbot_luaguard_")
    try:
        _run([_node(), LUAGUARD_CLI, os.path.abspath(input_path), "-o", out_dir],
             cwd=os.path.dirname(LUAGUARD_CLI), timeout=TIMEOUT)
        candidates = ["structured.txt", "pseudocode.txt", "disasm.txt"]
        for cand in candidates:
            p = os.path.join(out_dir, cand)
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if content.strip():
                    return content, "LuaGuard Unpack"
        raise RuntimeError("No output generated by LuaGuard unpacker")
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def run_centurion(input_path: str) -> tuple[str, str]:
    """Centurion polymorphic deobfuscator (Python + Luau)."""
    env = dict(os.environ)
    env["CENT_LUAU_LUAU"] = os.path.join(LUAU_BIN_DIR, "luau.exe")
    env["CENT_LUAU_LUAU_AST"] = os.path.join(LUAU_BIN_DIR, "luau-ast.exe")
    env["CENT_LUAU_LUAU_COMPILE"] = os.path.join(LUAU_BIN_DIR, "luau-compile.exe")
    out_dir = tempfile.mkdtemp(prefix="mbot_centurion_")
    try:
        r = subprocess.run(
            [_py(), CENTURION_PY, "deobfuscate", os.path.abspath(input_path), "--out-dir", out_dir],
            cwd=os.path.dirname(CENTURION_PY),
            capture_output=True,
            timeout=TIMEOUT,
            env=env
        )
        out = (r.stdout or b"").decode("utf-8", "replace").strip()
        for root, _, files in os.walk(out_dir):
            for fn in files:
                if fn.endswith((".lua", ".luau", ".txt")):
                    with open(os.path.join(root, fn), encoding="utf-8", errors="replace") as f:
                        txt = f.read()
                    if txt.strip():
                        return txt, "Centurion"
        if r.returncode != 0:
            err = (r.stderr or b"").decode("utf-8", "replace").strip()
            raise RuntimeError(err or out or f"exit code {r.returncode}")
        if out:
            return out, "Centurion"
        raise RuntimeError("Centurion produced no output")
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def run_veil_obfuscate(input_path: str, preset: str = "heavy") -> tuple[str, str]:
    """Veil Lua Obfuscator (Node.js)."""
    with tempfile.NamedTemporaryFile(suffix=".lua", delete=False) as f:
        out_path = f.name
    try:
        _run([_node(), "--experimental-strip-types", VEIL_OBF_CLI, input_path, out_path, preset],
             cwd=os.path.dirname(VEIL_OBF_CLI), timeout=TIMEOUT)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            return f.read(), f"Veil ({preset})"
    finally:
        try: os.unlink(out_path)
        except OSError: pass


# ── auto-detect pipeline ─────────────────────────────────────────────────────

# Ordered list: (name, detection_hint, runner_fn)
# detection_hint is a substring to look for in the first 4 KB of the script.
# Empty string = always try (fallback).
TOOLS = [
    # Tools with specific signatures first
    ("Bacon Guard",      "bacon guard",   run_baconguard),
    ("Bacon Guard",      "forge",         run_baconguard),
    ("IronBrew2",        "ironbrew2",     run_ironbrew2),
    ("IronBrew2",        "ironbrew",      run_ironbrew2),
    ("Ironveil V1",      "ironveil",      run_ironveil),
    ("77fuscator",       "77fus",         run_77fuscator),
    ("Clyde",            "clyde",         run_clyde),
    ("LuaObfuscator",    "luaobfuscator", run_luaobfuscator),
    ("Hercules",         "hercules",      run_hercules),
    ("Prometheus",       "wearedevs",     run_prometheus),
    ("Prometheus",       "prometheus",    run_prometheus),
    ("promdeobf",        "prometheus",    run_promdeobf),
    ("Luraph v15.1",     "lph",           run_luraph_v15_1),
    ("Luraph v15.1",     "luraph",        run_luraph_v15_1),
    # Broad-spectrum / fallback tools
    ("Luraph v15.1",     "",              run_luraph_v15_1),
    ("Luraph/IronBrew1", "",              run_luraph_ironbrew1),
]

def _is_useful_output(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if "0 statements recorded" in stripped:
        return False
    non_comment = [l for l in stripped.splitlines() if l.strip() and not l.strip().startswith("--")]
    if len(non_comment) == 0:
        return False
    return True


def detect_and_run(input_path: str) -> tuple[str, str]:
    with open(input_path, "rb") as f:
        header = f.read(4096).decode("utf-8", "replace").lower()

    errors = []
    for name, hint, fn in TOOLS:
        if hint and hint.lower() not in header:
            continue
        try:
            text, label = fn(input_path)
            if _is_useful_output(text):
                return text, label
            errors.append(f"{name}: produced empty/useless output")
        except RuntimeError as e:
            errors.append(f"{name}: {e}")

    for name, hint, fn in TOOLS:
        if hint:
            continue
        try:
            text, label = fn(input_path)
            if _is_useful_output(text):
                return text, label
            errors.append(f"{name}: produced empty/useless output")
        except RuntimeError as e:
            errors.append(f"{name}: {e}")

    raise RuntimeError("No tool could deobfuscate this script:\n" +
                       "\n".join(f"  • {e}" for e in errors))


ENGINE_RUNNERS = {
    "auto": ("Auto Detect", detect_and_run),
    "baconguard": ("Bacon Guard / FORGE", run_baconguard),
    "luraph_v15_1": ("Luraph v15.1", run_luraph_v15_1),
    "hercules": ("Hercules (1.6 - 2.0)", run_hercules),
    "clyde": ("Clyde (V2 - V6)", run_clyde),
    "prometheus": ("Prometheus", run_prometheus),
    "luaobfuscator": ("LuaObfuscator", run_luaobfuscator),
    "ironbrew2": ("IronBrew2", run_ironbrew2),
    "ironveil": ("Ironveil V1", run_ironveil),
    "77fuscator": ("77fuscator", run_77fuscator),
    "luaguard": ("LuaGuard Unpack", run_luaguard),
    "centurion": ("Centurion", run_centurion),
    "luraph_ironbrew1": ("Luraph / IronBrew1", run_luraph_ironbrew1),
}


def run_engine(engine_key: str, input_path: str) -> tuple[str, str]:
    """Execute by specific engine key, or fallback to auto detect."""
    key = (engine_key or "auto").lower()
    if key in ENGINE_RUNNERS and key != "auto":
        _, fn = ENGINE_RUNNERS[key]
        return fn(input_path)
    return detect_and_run(input_path)
