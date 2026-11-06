#!/usr/bin/env python3
"""satcosim: one entry point for the orbitsim × satsim co-simulation.

  python cosim.py setup                 # init submodules, uv sync both, npm install viz
  python cosim.py trace [case,...]      # orbitsim: export contact traces -> satsim/input/traces
  python cosim.py run <config|name>...  # satsim: run experiment(s), write playback for the viewer
  python cosim.py all                   # trace + every configs/cosim_*.yaml
  python cosim.py view                  # start the viewer (http://localhost:5288/play.html)
  python cosim.py test                  # orbitsim pytest + viz vitest + satsim pytest
  python cosim.py status                # submodule commits and dirty state
  python cosim.py update                # pull both submodules to their branch heads

Standard library only; needs git, uv and npm on PATH. Works from any directory.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORBIT = ROOT / "orbitsim"
SAT = ROOT / "satsim"
VIZ = ORBIT / "viz"
PLAYBACK = VIZ / "public" / "playback"
TRACES = SAT / "input" / "traces"
WIN = os.name == "nt"


def sh(cmd: list[str], cwd: Path, check: bool = True) -> int:
    print(f"\n$ ({cwd.relative_to(ROOT) if cwd != ROOT else '.'}) {' '.join(cmd)}", flush=True)
    exe = shutil.which(cmd[0]) or cmd[0]
    rc = subprocess.call([exe, *cmd[1:]], cwd=cwd)
    if check and rc != 0:
        sys.exit(f"failed ({rc}): {' '.join(cmd)}")
    return rc


def need_submodules() -> None:
    if not (ORBIT / "pyproject.toml").exists() or not (SAT / "pyproject.toml").exists():
        sys.exit("submodules missing: run `python cosim.py setup` (or `git submodule update --init`)")


def cmd_setup(_args) -> None:
    sh(["git", "submodule", "update", "--init", "--recursive"], ROOT)
    sh(["uv", "sync"], ORBIT)
    sh(["uv", "sync"], SAT)
    sh(["npm", "install"], VIZ)
    print("\nready. try: python cosim.py view")


def cmd_trace(args) -> None:
    need_submodules()
    out = ORBIT / "cosim_out"
    sh(["uv", "run", "python", "export_cosim.py", str(out), *([args[0]] if args else [])], ORBIT)
    TRACES.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(out.glob("*.json")):
        shutil.copy2(f, TRACES / f.name)
        n += 1
    print(f"copied {n} files -> {TRACES.relative_to(ROOT)}")


def resolve_config(name: str) -> Path:
    for cand in (Path(name), SAT / name, SAT / "configs" / name, SAT / "configs" / f"{name}.yaml",
                 SAT / "configs" / f"cosim_{name}.yaml"):
        if cand.is_file():
            return cand.resolve()
    known = ", ".join(p.stem for p in sorted((SAT / "configs").glob("cosim_*.yaml")))
    sys.exit(f"no config {name!r}; known: {known}")


def cmd_run(args) -> None:
    need_submodules()
    if not args:
        sys.exit("usage: python cosim.py run <config|name> [...]   e.g. run typhoon_agentic_v1")
    for name in args:
        cfg = resolve_config(name)
        sh(["uv", "run", "satsim-cosim", str(cfg), "--viz", str(PLAYBACK)], SAT)
    print(f"\nplayback -> {PLAYBACK.relative_to(ROOT)}; refresh http://localhost:5288/play.html")


def cmd_all(_args) -> None:
    cmd_trace([])
    cmd_run([str(p) for p in sorted((SAT / "configs").glob("cosim_*.yaml"))])


def cmd_view(_args) -> None:
    need_submodules()
    if not (VIZ / "node_modules").exists():
        sh(["npm", "install"], VIZ)
    print("open http://localhost:5288/play.html  (Ctrl+C to stop)")
    sh(["npm", "run", "dev"], VIZ, check=False)


def cmd_test(_args) -> None:
    need_submodules()
    rc = 0
    rc |= sh(["uv", "run", "pytest", "-q"], ORBIT, check=False)
    rc |= sh(["npx", "vitest", "run"], VIZ, check=False)
    # test_configs_symlink_runs needs real symlinks in satsim/configs (absent on Windows checkouts)
    extra = ["--deselect", "tests/test_plugins.py::test_configs_symlink_runs"] if WIN else []
    rc |= sh(["uv", "run", "pytest", "-q", *extra], SAT, check=False)
    sys.exit(rc)


def cmd_status(_args) -> None:
    sh(["git", "submodule", "status"], ROOT)
    for p in (ORBIT, SAT):
        sh(["git", "status", "-sb"], p, check=False)


def cmd_update(_args) -> None:
    sh(["git", "submodule", "update", "--init", "--remote"], ROOT)
    sh(["git", "submodule", "status"], ROOT)
    print("\nif the commits moved: git add orbitsim satsim && git commit -m 'bump submodules'")


COMMANDS = {"setup": cmd_setup, "trace": cmd_trace, "run": cmd_run, "all": cmd_all, "view": cmd_view,
            "test": cmd_test, "status": cmd_status, "update": cmd_update}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 2)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
