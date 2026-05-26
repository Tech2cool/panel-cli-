from constants import NGINX_AVAILABLE, NGINX_ENABLED
from helpers import run_command
import typer
from pathlib import Path
from jinja2 import Template




def site_create_cmd(domain, type, port):

    template_file = f"{type}.conf"

    template_path = (
        Path.home()
        / "panel/templates/nginx"
        / template_file
    )

    if not template_path.exists():
        print("Invalid site type")
        return False

    with open(template_path) as f:
        template = Template(f.read())

    config = template.render(
        DOMAIN=domain,
        PORT=port
    )

    with open("temp.conf", "w") as f:
        f.write(config)

    config_path = f"{NGINX_AVAILABLE}/{domain}.conf"

    run_command([
        "sudo",
        "cp",
        "temp.conf",
        config_path
    ])

    run_command([
        "sudo",
        "ln",
        "-sf",
        config_path,
        f"{NGINX_ENABLED}/{domain}.conf"
    ])

    result = run_command([
        "sudo",
        "nginx",
        "-t"
    ])

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print("Nginx config invalid")
        return False

    reload_result = run_command([
        "sudo",
        "systemctl",
        "reload",
        "nginx"
    ])

    if reload_result.returncode != 0:
        print("Nginx reload failed")
        return False

    print(f"{domain} created!")

    return True

def site_list_cmd():
    path = Path(NGINX_AVAILABLE)

    for file in path.glob("*.conf"):
        print(file.stem)

def site_disable_cmd(domain: str):

    enabled_path = f"{NGINX_ENABLED}/{domain}.conf"

    run_command([
        "sudo",
        "rm",
        "-f",
        enabled_path
    ])

    result = run_command(
        ["sudo", "nginx", "-t"]
    )

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        print("Nginx config invalid")
        return

    run_command([
        "sudo",
        "systemctl",
        "reload",
        "nginx"
    ])

    print(f"{domain} disabled")


def site_enable_cmd(domain: str):

    available_path = f"{NGINX_AVAILABLE}/{domain}.conf"
    enabled_path = f"{NGINX_ENABLED}/{domain}.conf"

    run_command([
        "sudo",
        "ln",
        "-sf",
        available_path,
        enabled_path
    ])

    result = run_command(
        ["sudo", "nginx", "-t"]
    )

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        print("Nginx config invalid")
        return

    run_command([
        "sudo",
        "systemctl",
        "reload",
        "nginx"
    ])

    print(f"{domain} enabled")


def site_delete_cmd(domain: str):

    enabled_path = f"{NGINX_ENABLED}/{domain}.conf"
    available_path = f"{NGINX_AVAILABLE}/{domain}.conf"

    run_command([
        "sudo",
        "rm",
        "-f",
        enabled_path
    ])

    run_command([
        "sudo",
        "mv",
        available_path,
        f"/opt/panel/archive/{domain}.conf"
    ])

    result = run_command(
        ["sudo", "nginx", "-t"]
    )

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        print("Nginx config invalid")
        return

    run_command([
        "sudo",
        "systemctl",
        "reload",
        "nginx"
    ])

    print(f"{domain} archived")
