from helpers import run_command
from logger import info, error, success

def ssl_enable_cmd(domain):

    result = run_command([
        "sudo",
        "certbot",
        "--nginx",
        "-d",
        domain,
        "--non-interactive",
        "--agree-tos",
        "-m",
        "admin@example.com",
        "--redirect"
    ])

    if result.stdout:
        info(result.stdout)

    if result.stderr:
        error(result.stderr)

    if result.returncode != 0:
        error("SSL setup failed")
        return False

    success(f"SSL enabled for {domain}")

    return True