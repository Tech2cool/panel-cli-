from panel.helpers import run_command
from panel.logger import info, error, success

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
        "tech2cool123@gmail.com",
        "--redirect"
    ])

    if result.stdout:
        info(result.stdout)

    if result.stderr and result.returncode != 0:
        error(result.stderr)

    if result.returncode != 0:
        error("SSL setup failed")
        return False

    info(f"SSL enabled for {domain}")

    return True
