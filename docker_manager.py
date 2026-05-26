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

    print(result.stdout)

def docker_create_cmd(name: str, port: int):

    app_dir = f"/opt/panel/apps/{name}"

    run_command([
        "sudo",
        "mkdir",
        "-p",
        app_dir
    ])

    template_path = (
        Path.home()
        / "panel/templates/docker/node-compose.yml"
    )

    with open(template_path) as f:
        template = Template(f.read())

    compose = template.render(
        NAME=name,
        PORT=port
    )

    metadata = {
        "name": name,
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

    result = run_command(
        [
            "sudo",
            "docker",
            "compose",
            "-f",
            f"{app_dir}/docker-compose.yml",
            "up",
            "-d"
        ]
    )

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        print("Docker deployment failed")
        return

    print(f"{name} deployed!")

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

    print(result.stdout)

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

    print(result.stdout)

    if result.stderr:
        print(result.stderr)

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
        print("Restart failed")
        print(result.stderr)
        return

    print(f"{name} restarted")

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
        print("Stop failed")
        print(result.stderr)
        return

    print(f"{name} stopped")

def app_list_cmd():

    apps_dir = Path("/opt/panel/apps")

    for app in apps_dir.iterdir():

        metadata_file = app / "metadata.json"

        if metadata_file.exists():

            with open(metadata_file) as f:
                metadata = json.load(f)

            print(
                f"{metadata['name']} - "
                f"{metadata['type']} - "
                f"{metadata['port']}"
            )


def app_delete_cmd(name):

    app_dir = Path(f"/opt/panel/apps/{name}")

    metadata_file = app_dir / "metadata.json"

    if not metadata_file.exists():
        print("App not found")
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
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            print("Docker cleanup failed")
            return

    if domain:
        site_delete_cmd(domain)

    shutil.rmtree(app_dir)

    print(f"{name} deleted")



def app_create_cmd(name, domain, port):

    docker_create_cmd(name, port)

    site_create_cmd(
        domain=domain,
        type="proxy",
        port=port
    )

    print(f"{name} fully deployed")