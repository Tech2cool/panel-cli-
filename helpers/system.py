import subprocess
from pathlib import Path

def run_command(cmd):

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300
    )

    return result


def write_log(app_dir, filename, content):

    logs_dir = Path(app_dir) / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / filename

    with open(log_file, "a") as f:
        f.write(content)
        f.write("\n")


