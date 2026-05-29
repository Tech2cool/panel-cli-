# commands/site_create.py

import json
from pathlib import Path
from datetime import datetime
import shutil

from jinja2 import Template

from panel.constants import NGINX_AVAILABLE, NGINX_ENABLED
from panel.helpers.site import domain_exists, port_exists, validate_domain, validate_site_name
from panel.helpers.system import run_command
from panel.logger import *

PANEL_ROOT = Path("/opt/panel")
SITES_DIR = PANEL_ROOT / "sites"

VALID_TYPES = ["static", "proxy", "docker"]

RESERVED_NAMES = [
    "www",
    "root",
    "admin",
    "api",
]


def cleanup_failed_site(site_dir, domain):
    """
    Cleanup partially created site
    """

    try:
        shutil.rmtree(site_dir, ignore_errors=True)

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

    except Exception as e:
        error(f"Cleanup failed: {e}")


def site_create_cmd(name, domain, site_type, port=None):

    #
    # NORMALIZE
    #

    name = name.strip().lower()
    domain = domain.strip().lower()

    #
    # VALIDATION
    #

    if not name:
        error("Site name required")
        return False

    if not domain:
        error("Domain required")
        return False

    if name in RESERVED_NAMES:
        error("Reserved site name")
        return False

    if not validate_site_name(name):
        error("Invalid site name")
        return False

    if not validate_domain(domain):
        error("Invalid domain")
        return False

    if domain_exists(domain):
        error("Domain already exists")
        return False

    if site_type not in VALID_TYPES:
        error(f"Invalid type. Allowed: {', '.join(VALID_TYPES)}")
        return False

    #
    # PORT VALIDATION
    #

    if site_type in ["proxy", "docker"]:

        if port is None:
            error(f"Port required for {site_type}")
            return False

        if not isinstance(port, int):
            error("Port must be integer")
            return False

        if port < 1 or port > 65535:
            error("Invalid port")
            return False

        if port_exists(port):
            error("Port already in use")
            return False

    #
    # SAFE PATH
    #

    site_dir = (SITES_DIR / name).resolve()

    if not str(site_dir).startswith(str(SITES_DIR.resolve())):
        error("Invalid site path")
        return False

    if site_dir.exists():
        error("Site already exists")
        return False

    #
    # CREATE SITE DIRECTORY
    #

    try:

        site_dir.mkdir(parents=True, exist_ok=False)

    except Exception as e:

        error(f"Failed to create site directory: {e}")

        return False

    try:

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
        # PUBLIC DIRECTORY
        #

        public_dir = site_dir / "public"

        if site_type == "static":

            public_dir.mkdir(exist_ok=True)

            with open(public_dir / "index.html", "w") as f:
                f.write(f"<h1>{domain} created successfully</h1>")

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

            cleanup_failed_site(site_dir, domain)

            return False

        with open(template_path) as f:
            template = Template(f.read())

        #
        # RENDER NGINX CONFIG
        #

        config = template.render(
            DOMAIN=domain,
            PORT=port,
            ROOT=public_dir,
        )

        #
        # TEMP CONFIG
        #

        temp_config = site_dir / "nginx.conf"

        with open(temp_config, "w") as f:
            f.write(config)

        #
        # INSTALL CONFIG
        #

        config_path = f"{NGINX_AVAILABLE}/{domain}.conf"

        copy_result = run_command([
            "sudo",
            "cp",
            str(temp_config),
            config_path
        ])

        if copy_result.returncode != 0:

            error("Failed to install nginx config")

            cleanup_failed_site(site_dir, domain)

            return False

        #
        # ENABLE SITE
        #

        symlink_result = run_command([
            "sudo",
            "ln",
            "-sf",
            config_path,
            f"{NGINX_ENABLED}/{domain}.conf"
        ])

        if symlink_result.returncode != 0:

            error("Failed to enable site")

            cleanup_failed_site(site_dir, domain)

            return False

        #
        # TEST NGINX
        #

        nginx_test = run_command([
            "sudo",
            "nginx",
            "-t"
        ])

        if nginx_test.returncode != 0:

            error("Invalid nginx config")

            if nginx_test.stderr:
                error(nginx_test.stderr)

            cleanup_failed_site(site_dir, domain)

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

            error("Failed to reload nginx")

            cleanup_failed_site(site_dir, domain)

            return False

        info(f"{domain} created successfully!")

        return True

    except Exception as e:

        cleanup_failed_site(site_dir, domain)

        error(f"Site creation failed: {e}")

        return False

# commands/site_list.py

import json

from pathlib import Path

from panel.logger import *

PANEL_ROOT = Path("/opt/panel")
SITES_DIR = PANEL_ROOT / "sites"


def site_list_cmd():

    if not SITES_DIR.exists():

        info("No sites directory")

        return False

    sites = []

    for site_dir in SITES_DIR.iterdir():

        if not site_dir.is_dir():
            continue

        config_file = site_dir / "site.json"

        if not config_file.exists():
            continue

        try:

            with open(config_file) as f:
                data = json.load(f)

            sites.append(data)

        except Exception as e:

            error(f"Failed reading {site_dir.name}: {e}")

    #
    # EMPTY
    #

    if not sites:

        info("No sites found")

        return True

    #
    # OUTPUT
    #

    print()

    print(
        f"{'NAME':20}"
        f"{'DOMAIN':30}"
        f"{'TYPE':12}"
        f"{'STATUS':12}"
        f"{'PORT':8}"
    )

    print("-" * 82)

    for site in sites:

        port = site.get("port") or "-"

        print(
            f"{site.get('name', '-'):20}"
            f"{site.get('domain', '-'):30}"
            f"{site.get('type', '-'):12}"
            f"{site.get('status', '-'):12}"
            f"{str(port):8}"
        )

    print()

    return True

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





