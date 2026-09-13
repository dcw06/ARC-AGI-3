"""POSIX process-group supervisor covering installation, failures and cleanup."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def supervise(command, output, seconds):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    process = None
    status = "starting"
    def record():
        target = output / "notebook-cost.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps({"elapsed_seconds": time.monotonic()-started,
            "budget_seconds": seconds, "status":status, "scope":"supervised_setup_execution_and_cleanup"}))
        os.replace(temporary, target)
    record()  # retained even if launch or first dependency installation fails
    try:
        process = subprocess.Popen(command, start_new_session=True)
        status = "running"
        while process.poll() is None:
            record()
            if time.monotonic()-started >= seconds:
                status = "timed_out"
                raise TimeoutError("whole-notebook compute ceiling reached")
            time.sleep(0.1)
        status = "complete" if process.returncode == 0 else "failed"
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)
    except BaseException:
        if status != "timed_out":
            status = "failed"
        raise
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        record()
