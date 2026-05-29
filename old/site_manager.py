import json

from pathlib import Path

from datetime import datetime

from helpers import *

from old.nginx_manager import *

from old.docker_manager import *

PANEL_ROOT = Path("/opt/panel")

SITES_DIR = PANEL_ROOT / "sites"


#
# CREATE SITE
#

def site_create_cmd(
    name,
    type,
    domain,
    proxy_port=None,
    docker_type=None,
    port=None,
    repo=None,
    start=None
):

    site_dir = SITES_DIR / name

    #
    # VALIDATE
    #

    if site_dir.exists():
        error("Site already exists")
        return False

    #
    # CREATE SITE ROOT
    #

    run_command([
        "sudo",
        "mkdir",
        "-p",
        str(site_dir)
    ])

    run_command([
        "sudo",
        "chown",
        "-R",
        "ubuntu:ubuntu",
        str(site_dir)
    ])

    #
    # STATIC SITE
    #

    if type == "static":

        public_dir = site_dir / "public"

        public_dir.mkdir(parents=True, exist_ok=True)

        with open(public_dir / "index.html", "w") as f:
            f.write(f"<h1>{name} works!</h1>")

        nginx_ok = site_create_cmd(
            domain=domain,
            type="static",
            path=str(public_dir)
        )

        if not nginx_ok:
            error("Failed creating nginx site")
            return False

    #
    # PROXY SITE
    #

    elif type == "proxy":

        if not proxy_port:
            error("Proxy port required")
            return False

        nginx_ok = site_create_cmd(
            domain=domain,
            type="proxy",
            port=proxy_port
        )

        if not nginx_ok:
            error("Failed creating nginx site")
            return False

    #
    # DOCKER SITE
    #

    elif type == "docker":

        if not docker_type:
            error("Docker type required")
            return False

        docker_ok = docker_create_cmd(
            name=name,
            domain=domain,
            port=port,
            type=docker_type,
            repo=repo,
            start=start
        )

        if not docker_ok:
            error("Docker deployment failed")
            return False

        nginx_ok = site_create_cmd(
            domain=domain,
            type="proxy",
            port=port
        )

        if not nginx_ok:

            error("Nginx failed")

            docker_delete_cmd(name)

            return False

    else:

        error("Invalid site type")

        return False

    #
    # METADATA
    #

    metadata = {
        "name": name,

        "type": type,

        "docker_type": docker_type,

        "domain": domain,

        "proxy_port": proxy_port,

        "repo": repo,

        "start": start,

        "created_at": datetime.utcnow().isoformat()
    }

    metadata_file = site_dir / "metadata.json"

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=4)

    info(f"{name} created")

    return True


#
# LIST SITES
#

def site_list_cmd():

    if not SITES_DIR.exists():
        return

    for site_dir in SITES_DIR.iterdir():

        metadata_file = site_dir / "metadata.json"

        if metadata_file.exists():

            with open(metadata_file) as f:
                metadata = json.load(f)

            info(
                f"{metadata['name']} - "
                f"{metadata['type']} - "
                f"{metadata['domain']}"
            )


#
# DELETE SITE
#

def site_delete_cmd(name):

    site_dir = SITES_DIR / name

    metadata_file = site_dir / "metadata.json"

    if not metadata_file.exists():
        error("Site not found")
        return False

    with open(metadata_file) as f:
        metadata = json.load(f)

    site_type = metadata["type"]

    domain = metadata["domain"]

    #
    # REMOVE NGINX
    #

    nginx_delete_cmd(domain)

    #
    # REMOVE DOCKER
    #

    if site_type == "docker":

        docker_delete_cmd(name)

    #
    # REMOVE SITE FILES
    #

    run_command([
        "sudo",
        "rm",
        "-rf",
        str(site_dir)
    ])

    info(f"{name} deleted")

    return True