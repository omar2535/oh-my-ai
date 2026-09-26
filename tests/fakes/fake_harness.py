"""Behaviour of every fake executable used by the tests.

Each fake is a tiny script calling ``main(spec_path)``. The JSON spec lists responses;
the first whose ``args`` is a prefix of argv and whose ``when`` matches the persisted
state is used. Every invocation is appended to a shared JSONL log.
"""

import json
import os
import string
import subprocess
import sys
import time


def main(spec_path: str) -> None:
    with open(spec_path) as fh:
        spec = json.load(fh)
    state_path = spec["state"]
    state = {}
    if os.path.exists(state_path):
        with open(state_path) as fh:
            state = json.load(fh)
    argv = sys.argv[1:]
    started = time.time()
    response = {"stdout": "", "exit": 0}
    for candidate in spec["responses"]:
        args = candidate.get("args", [])
        if argv[: len(args)] != args:
            continue
        if all(state.get(k) == v for k, v in candidate.get("when", {}).items()):
            response = candidate
            break
    if response.get("sleep"):
        time.sleep(response["sleep"])
    before = {k: str(v) for k, v in state.items()}
    for key, value in response.get("set", {}).items():
        state[key] = string.Template(value).safe_substitute(before) if isinstance(value, str) else value
    for key, index in response.get("set_argv", {}).items():
        state[key] = argv[index]
    for key, index in response.get("append_argv", {}).items():
        state[key] = [*state.get(key, []), argv[index]]
    with open(state_path, "w") as fh:
        json.dump(state, fh)
    if response.get("sh"):
        subprocess.run(["sh", "-c", response["sh"]], check=False)
    values = {k: str(v) for k, v in state.items()}
    out = string.Template(response.get("stdout", "")).safe_substitute(values)
    if response.get("stdout_state"):
        out = str(state.get(response["stdout_state"], response.get("default", ""))) + "\n"
    if response.get("json_from_state"):
        out = json.dumps({k: state.get(v) for k, v in response["json_from_state"].items()})
    sys.stdout.write(out)
    sys.stderr.write(string.Template(response.get("stderr", "")).safe_substitute(values))
    with open(spec["log"], "a") as fh:
        fh.write(json.dumps({"bin": spec["name"], "argv": argv, "start": started, "end": time.time()}) + "\n")
    sys.exit(response.get("exit", 0))
