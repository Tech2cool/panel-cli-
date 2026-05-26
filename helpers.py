import subprocess

def run_command(cmd):

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30
    )

    return result