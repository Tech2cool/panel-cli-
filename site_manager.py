# commands/site_create.py

import json
from pathlib import Path
from datetime import datetime
import shutil

from jinja2 import Template

from constants import NGINX_AVAILABLE, NGINX_ENABLED
from helpers import run_command
from logger import *

PANEL_ROOT = Path("/opt/panel")
SITES_DIR = PANEL_ROOT / "sites"

VALID_TYPES = ["static", "proxy", "docker"]


def site_create_cmd(name, domain, site_type, port=None):
    site_dir = SITES_DIR / name

    #
    # VALIDATION
    #

    if site_dir.exists():
        error("Site already exists")
        return False

    if site_type not in VALID_TYPES:
        error(f"Invalid type. Allowed: {', '.join(VALID_TYPES)}")
        return False

    if site_type in ["proxy", "docker"] and not port:
        error(f"Port required for {site_type}")
        return False

    #
    # CREATE SITE DIR
    #

    site_dir.mkdir(parents=True)

    #
    # SAVE METADATA
    #

    site_data = {
        "name": name,
        "domain": domain,
        "type": site_type,
        "status": "active",
        "port": port,
        "created_at": datetime.utcnow().isoformat(),
    }

    with open(site_dir / "site.json", "w") as f:
        json.dump(site_data, f, indent=4)

    #
    # LOAD NGINX TEMPLATE
    #

    template_path = (
        Path.home()
        / "panel/templates/nginx"
        / f"{site_type}.conf"
    )

    if not template_path.exists():
        error("Template not found")
        return False

    with open(template_path) as f:
        template = Template(f.read())

    config = template.render(
        DOMAIN=domain,
        PORT=port,
        ROOT=site_dir / "public",
    )

    #
    # STATIC SITE ROOT
    #

    if site_type == "static":
        (site_dir / "public").mkdir(exist_ok=True)

        with open(site_dir / "public/index.html", "w") as f:
            f.write("<h1>It works</h1>")

    #
    # WRITE NGINX CONFIG
    #

    temp_config = site_dir / "nginx.conf"

    with open(temp_config, "w") as f:
        f.write(config)

    config_path = f"{NGINX_AVAILABLE}/{domain}.conf"

    run_command([
        "sudo",
        "cp",
        str(temp_config),
        config_path
    ])

    run_command([
        "sudo",
        "ln",
        "-sf",
        config_path,
        f"{NGINX_ENABLED}/{domain}.conf"
    ])

    #
    # TEST NGINX
    #

    result = run_command([
        "sudo",
        "nginx",
        "-t"
    ])

    if result.returncode != 0:
        error(result.stderr)
        return False

    #
    # RELOAD NGINX
    #

    reload_result = run_command([
        "sudo",
        "systemctl",
        "reload",
        "nginx"
    ])

    if reload_result.returncode != 0:
        error("Nginx reload failed")
        return False

    info(f"{domain} created successfully!")

    return True


def site_list_cmd():
    if not SITES_DIR.exists():
        print("No sites found")
        return

    for site in SITES_DIR.iterdir():
        config = site / "site.json"

        if not config.exists():
            continue

        with open(config) as f:
            data = json.load(f)

        print(
            f"{data['name']} | "
            f"{data['domain']} | "
            f"{data['status']}"
        )


def site_delete_cmd(name):
    site_dir = SITES_DIR / name

    if not site_dir.exists():
        error("Site not found")
        return False

    domain = None

    import json

    with open(site_dir / "site.json") as f:
        data = json.load(f)
        domain = data["domain"]

    #
    # REMOVE NGINX FILES
    #

    run_command([
        "sudo",
        "rm",
        "-f",
        f"{NGINX_ENABLED}/{domain}.conf"
    ])

    run_command([
        "sudo",
        "rm",
        "-f",
        f"{NGINX_AVAILABLE}/{domain}.conf"
    ])

    #
    # RELOAD NGINX
    #

    run_command([
        "sudo",
        "systemctl",
        "reload",
        "nginx"
    ])

    #
    # DELETE SITE
    #

    shutil.rmtree(site_dir)

    info(f"{name} deleted")

    return True


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

    error(result.stdout)
    error(result.stderr)

    if result.returncode != 0:
        error("Nginx config invalid")
        return

    run_command([
        "sudo",
        "systemctl",
        "reload",
        "nginx"
    ])

    info(f"{domain} disabled")


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

    error(result.stdout)
    error(result.stderr)

    if result.returncode != 0:
        error("Nginx config invalid")
        return

    run_command([
        "sudo",
        "systemctl",
        "reload",
        "nginx"
    ])

    info(f"{domain} enabled")





