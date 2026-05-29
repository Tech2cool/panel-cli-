# commands/site_create.py

import json
from pathlib import Path
from datetime import datetime
import shutil
from urllib.parse import urlparse

from jinja2 import Template

from panel.constants import NGINX_AVAILABLE, NGINX_ENABLED
from panel.helpers.site import domain_exists, get_site, port_exists, validate_domain, validate_proxy_url, validate_site_name
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

def site_create_cmd(
    name,
    domain,
    site_type,
    port=None,
    proxy_url=None
):

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
    # PROXY VALIDATION
    #

    if site_type in ["proxy", "docker"]:

        #
        # PORT SHORTHAND
        #

        if port and not proxy_url:
            proxy_url = f"http://127.0.0.1:{port}"

        #
        # REQUIRE TARGET
        #

        if not proxy_url:
            error(f"Proxy URL required for {site_type}")
            return False

        #
        # VALIDATE URL
        #

        if not validate_proxy_url(proxy_url):
            error("Invalid proxy URL")
            return False

        #
        # OPTIONAL LOCAL PORT VALIDATION
        #

        parsed = urlparse(proxy_url)

        if parsed.hostname in ["127.0.0.1", "localhost"]:

            target_port = parsed.port

            if not target_port:
                error("Missing proxy port")
                return False

            if target_port < 1 or target_port > 65535:
                error("Invalid proxy port")
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
            "ssl": False,
            "port": port,
            "proxy_url": proxy_url,
            "created_at": datetime.utcnow().isoformat(),
        }

        with open(site_dir / "site.json", "w") as f:
            json.dump(site_data, f, indent=4)

        #
        # STATIC SITE ROOT
        #

        public_dir = site_dir / "public"

        if site_type == "static":

            public_dir.mkdir(exist_ok=True)

            with open(public_dir / "index.html", "w") as f:
                f.write(f"<h1>{domain} created successfully</h1>")

        #
        # LOAD TEMPLATE
        #

        template_path = (
            Path.home()
            / "panel/panel/templates/nginx"
            / f"{site_type}.conf"
        )

        if not template_path.exists():

            error("Template not found")

            cleanup_failed_site(site_dir, domain)

            return False

        with open(template_path) as f:
            template = Template(f.read())

        #
        # RENDER CONFIG
        #

        config = template.render(
            DOMAIN=domain,
            ROOT=public_dir,
            PORT=port,
            PROXY_URL=proxy_url,
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

        #
        # SUCCESS
        #

        info(f"{domain} created successfully!")

        return True

    except Exception as e:

        cleanup_failed_site(site_dir, domain)

        error(f"Site creation failed: {e}")

        return False
    


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
    # TABLE HEADER
    #

    print()

    print(
        f"{'NAME':20}"
        f"{'DOMAIN':30}"
        f"{'TYPE':12}"
        f"{'STATUS':12}"
        f"{'SSL':8}"
        f"{'PORT':8}"
    )

    print("-" * 90)

    #
    # ROWS
    #

    for site in sites:

        port = site.get("port") or "-"

        ssl = "yes" if site.get("ssl") else "no"

        print(
            f"{site.get('name', '-'):20}"
            f"{site.get('domain', '-'):30}"
            f"{site.get('type', '-'):12}"
            f"{site.get('status', '-'):12}"
            f"{ssl:8}"
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

def site_disable_cmd(identifier: str):

    identifier = identifier.strip().lower()

    #
    # GET SITE
    #

    site_data = get_site(identifier)

    if not site_data:
        error("Site not found")
        return False

    domain = site_data.get("domain")
    name = site_data.get("name")

    #
    # SITE DIR
    #

    site_dir = (SITES_DIR / name).resolve()

    if not str(site_dir).startswith(str(SITES_DIR.resolve())):
        error("Invalid site path")
        return False

    #
    # REMOVE ENABLED LINK
    #

    enabled_path = f"{NGINX_ENABLED}/{domain}.conf"

    run_command([
        "sudo",
        "rm",
        "-f",
        enabled_path
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

        if result.stderr:
            error(result.stderr)

        error("Nginx config invalid")

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

        return False

    #
    # UPDATE METADATA
    #

    site_data["status"] = "disabled"

    config_file = site_dir / "site.json"

    with open(config_file, "w") as f:
        json.dump(site_data, f, indent=4)

    #
    # SUCCESS
    #

    info(f"{domain} disabled")

    return True

def site_enable_cmd(identifier: str):

    identifier = identifier.strip().lower()

    #
    # GET SITE
    #

    site_data = get_site(identifier)

    if not site_data:
        error("Site not found")
        return False

    domain = site_data.get("domain")
    name = site_data.get("name")

    if not domain:
        error("Missing domain")
        return False

    #
    # SITE DIR
    #

    site_dir = (SITES_DIR / name).resolve()

    #
    # SAFE PATH
    #

    if not str(site_dir).startswith(str(SITES_DIR.resolve())):
        error("Invalid site path")
        return False

    #
    # PATHS
    #

    available_path = f"{NGINX_AVAILABLE}/{domain}.conf"
    enabled_path = f"{NGINX_ENABLED}/{domain}.conf"

    #
    # ENABLE SITE
    #

    symlink_result = run_command([
        "sudo",
        "ln",
        "-sf",
        available_path,
        enabled_path
    ])

    if symlink_result.returncode != 0:

        error("Failed to enable site")

        return False

    #
    # TEST NGINX
    #

    result = run_command([
        "sudo",
        "nginx",
        "-t"
    ])

    if result.returncode != 0:

        if result.stderr:
            error(result.stderr)

        error("Nginx config invalid")

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

        return False

    #
    # UPDATE METADATA
    #

    site_data["status"] = "active"

    config_file = site_dir / "site.json"

    with open(config_file, "w") as f:
        json.dump(site_data, f, indent=4)

    #
    # SUCCESS
    #

    info(f"{domain} enabled")

    return True

def site_ssl_cmd(identifier):

    identifier = identifier.strip().lower()

    #
    # GET SITE
    #

    site_data = get_site(identifier)

    if not site_data:
        error("Site not found")
        return False

    domain = site_data.get("domain")
    name = site_data.get("name")

    if not domain:
        error("Missing domain")
        return False

    #
    # SITE DIR
    #

    site_dir = (SITES_DIR / name).resolve()

    #
    # SAFE PATH
    #

    if not str(site_dir).startswith(str(SITES_DIR.resolve())):
        error("Invalid site path")
        return False

    #
    # SSL ALREADY ENABLED
    #

    if site_data.get("ssl") is True:
        info("SSL already enabled")
        return True

    #
    # ISSUE SSL
    #

    info(f"Issuing SSL for {domain}")

    result = run_command([
        "sudo",
        "certbot",
        "--nginx",
        "-d",
        domain,
        "--non-interactive",
        "--agree-tos",
        "-m",
        f"admin@{domain}",
        "--redirect"
    ])

    #
    # FAILED
    #

    if result.returncode != 0:

        if result.stderr:
            error(result.stderr)

        error("SSL generation failed")

        return False

    #
    # UPDATE SITE CONFIG
    #

    config_file = site_dir / "site.json"

    site_data["ssl"] = True

    with open(config_file, "w") as f:
        json.dump(site_data, f, indent=4)

    #
    # SUCCESS
    #

    info(f"SSL enabled for {domain}")

    return True

