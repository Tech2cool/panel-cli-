from logger import error, info, success
from pathlib import Path
import shutil
from constants import DOCKER_BIN
from helpers import run_command
from jinja2 import Template
import json

from nginx_manager import site_create_cmd, site_delete_cmd

def docker_list_cmd():

    result = run_command([
        "sudo",
        DOCKER_BIN,
        "ps"
    ])

    info(result.stdout)


def docker_create_cmd(name, domain, port, type):
    
    app_dir = f"/opt/panel/apps/{name}"
    html_dir = f"{app_dir}/html"
    node_app_dir = f"{app_dir}/app"

    run_command([
        "sudo",
        "mkdir",
        "-p",
        app_dir
    ])

    if type == "static":

        run_command([
            "sudo",
            "mkdir",
            "-p",
            html_dir
        ])

        with open("index.html", "w") as f:
            f.write(f"<h1>{name} works!</h1>")

        run_command([
            "sudo",
            "cp",
            "index.html",
            f"{html_dir}/index.html"
        ])

    if type == "node":

        run_command([
            "sudo",
            "mkdir",
            "-p",
            node_app_dir
        ])

        with open("server.js", "w") as f:
            f.write(
        """const http = require('http');

        const PORT = process.env.PORT || 3000;

        const server = http.createServer((req, res) => {
            res.end('API works!');
        });

        server.listen(PORT, () => {
            console.log(`Server running on ${PORT}`);
        });
        """
            )
        run_command([
            "sudo",
            "cp",
            "server.js",
            f"{node_app_dir}/server.js"
        ])

    template_path = (
        Path.home()
        / f"panel/templates/docker/{type}.yml"
    )

    with open(template_path) as f:
        template = Template(f.read())

    compose = template.render(
        NAME=name,
        PORT=port
    )

    metadata = {
        "name": name,
        "domain": domain,
        "port": port,
        "type": "docker"
    }

    with open("metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    run_command([
        "sudo",
        "cp",
        "metadata.json",
        f"{app_dir}/metadata.json"
    ])

    with open("docker-compose.yml", "w") as f:
        f.write(compose)

    run_command([
        "sudo",
        "cp",
        "docker-compose.yml",
        f"{app_dir}/docker-compose.yml"
    ])

    result = run_command([
        "sudo",
        DOCKER_BIN,
        "compose",
        "-f",
        f"{app_dir}/docker-compose.yml",
        "up",
        "-d"
    ])

    if result.stdout:
        info(result.stdout)

    if result.stderr:
        error(result.stderr)

    if result.returncode != 0:
        error("Docker deployment failed")
        return False

    info(f"{name} deployed!")

    return True

def docker_list_cmd():

    result = run_command(
        [
            "sudo",
            DOCKER_BIN,
            "ps",
            "--format",
            "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ]
    )

    info(result.stdout)

def docker_logs_cmd(name: str):

    result = run_command(
        [
            "sudo",
            DOCKER_BIN,
            "logs",
            "--tail",
            "50",
            name
        ]
    )

    info(result.stdout)

    if result.stderr:
        error(result.stderr)

def docker_restart_cmd(name: str):

    result = run_command(
        [
            "sudo",
            DOCKER_BIN,
            "restart",
            name
        ]
    )

    if result.returncode != 0:
        error("Restart failed")
        error(result.stderr)
        return

    info(f"{name} restarted")

def docker_stop_cmd(name: str):

    result = run_command(
        [
            "sudo",
            DOCKER_BIN,
            "stop",
            name
        ]
    )

    if result.returncode != 0:
        error("Stop failed")
        error(result.stderr)
        return

    info(f"{name} stopped")

def docker_delete_cmd(name):

    app_dir = Path(f"/opt/panel/apps/{name}")

    compose_file = app_dir / "docker-compose.yml"

    if not app_dir.exists():
        error("App directory not found")
        return False

    if compose_file.exists():

        result = run_command([
            "sudo",
            DOCKER_BIN,
            "compose",
            "-f",
            str(compose_file),
            "down"
        ])

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            error("Docker cleanup failed")
            return False

    delete_result = run_command([
        "sudo",
        "rm",
        "-rf",
        str(app_dir)
    ])

    if delete_result.returncode != 0:
        error("Failed to remove app directory")
        return False

    success(f"{name} removed")

    return True


def app_list_cmd():

    apps_dir = Path("/opt/panel/apps")

    if not apps_dir.exists():
        return

    for app in apps_dir.iterdir():

        metadata_file = app / "metadata.json"

        if metadata_file.exists():

            with open(metadata_file) as f:
                metadata = json.load(f)

            info(
                f"{metadata['name']} - "
                f"{metadata['type']} - "
                f"{metadata['port']}"
            )


def app_delete_cmd(name):

    app_dir = Path(f"/opt/panel/apps/{name}")

    metadata_file = app_dir / "metadata.json"

    if not metadata_file.exists():
        error("App not found")
        return

    with open(metadata_file) as f:
        metadata = json.load(f)

    domain = metadata.get("domain")

    compose_file = app_dir / "docker-compose.yml"

    if compose_file.exists():

        result = run_command([
            "sudo",
            DOCKER_BIN,
            "compose",
            "-f",
            str(compose_file),
            "down"
        ])

        if result.stdout:
            info(result.stdout)

        if result.stderr:
            error(result.stderr)

        if result.returncode != 0:
            error("Docker cleanup failed")
            return

    if domain:
        site_delete_cmd(domain)

    delete_result = run_command([
        "sudo",
        "rm",
        "-rf",
        str(app_dir)
    ])

    if delete_result.returncode != 0:
        error("Failed to remove app directory")
        return False

    info(f"{name} deleted")

    return True

# 

def app_create_cmd(name, domain, port, type):

    docker_ok = docker_create_cmd(
        name=name,
        domain=domain,
        port=port,
        type=type
    )

    if not docker_ok:
        error("App deployment failed")
        return False

    nginx_ok = site_create_cmd(
        domain=domain,
        type="proxy",
        port=port
    )

    if not nginx_ok:

        error("Nginx failed")
        error("Rolling back deployment...")

        docker_delete_cmd(name)

        return False

    info(f"{name} fully deployed")

    return True

