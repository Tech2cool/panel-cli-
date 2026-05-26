import subprocess

from logger import error, info, success
from pathlib import Path
import shutil
from constants import DOCKER_BIN
from helpers import run_command,write_log
from jinja2 import Template
import json
import time
import secrets

from nginx_manager import site_create_cmd, site_delete_cmd

def docker_list_cmd():

    result = run_command([
        "sudo",
        DOCKER_BIN,
        "ps"
    ])

    info(result.stdout)


def docker_create_cmd(name, domain, port, type, repo, start):

    app_dir = f"/opt/panel/apps/{name}"

    html_dir = f"{app_dir}/html"

    node_app_dir = f"{app_dir}/app"

    #
    # CREATE APP ROOT
    #

    run_command([
        "sudo",
        "mkdir",
        "-p",
        app_dir
    ])

    run_command([
        "sudo",
        "chown",
        "-R",
        "ubuntu:ubuntu",
        app_dir
    ])

    #
    # STATIC RUNTIME
    #

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

    #
    # NODE RUNTIME
    #

    if type == "node":

        run_command([
            "sudo",
            "mkdir",
            "-p",
            node_app_dir
        ])

        #
        # GIT DEPLOY
        #

        if repo:

            result = run_command([
                "sudo",
                "git",
                "clone",
                repo,
                node_app_dir
            ])

            if result.stdout:
                info(result.stdout)
                write_log(
                    app_dir,
                    "deploy.log",
                    result.stdout
                )

            if result.stderr and result.returncode != 0:
                error(result.stderr)
                write_log(
                    app_dir,
                    "deploy.log",
                    result.stderr
                )

            if result.returncode != 0:
                error("Git clone failed")
                return False

            #
            # INSTALL NODE DEPENDENCIES
            #

            npm_result = run_command([
                "sudo",
                DOCKER_BIN,
                "run",
                "--rm",
                "-v",
                f"{node_app_dir}:/app",
                "-w",
                "/app",
                "node:20-alpine",
                "npm",
                "install"
            ])

            if npm_result.stdout:
                info(npm_result.stdout)
                write_log(
                    app_dir,
                    "build.log",
                    npm_result.stdout
                )

            if npm_result.stderr and npm_result.returncode != 0:
                error(npm_result.stderr)
                write_log(
                    app_dir,
                    "build.log",
                    npm_result.stderr
                )

            if npm_result.returncode != 0:
                error("npm install failed")
                return False

        #
        # STARTER APP
        #

        else:

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

    #
    # LOAD COMPOSE TEMPLATE
    #

    template_path = (
        Path.home()
        / f"panel/templates/docker/{type}.yml"
    )

    if not template_path.exists():
        error("Runtime template not found")
        return False

    with open(template_path) as f:
        template = Template(f.read())

    compose = template.render(
        NAME=name,
        PORT=port,
        START=start
    )

    #
    # METADATA
    #

    metadata = {
        "name": name,
        "domain": domain,
        "port": port,
        "runtime": type,
        "repo": repo,
        "start": start
    }

    with open("metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    run_command([
        "sudo",
        "cp",
        "metadata.json",
        f"{app_dir}/metadata.json"
    ])

    #
    # DOCKER COMPOSE
    #

    with open("docker-compose.yml", "w") as f:
        f.write(compose)

    run_command([
        "sudo",
        "cp",
        "docker-compose.yml",
        f"{app_dir}/docker-compose.yml"
    ])

    #
    # DEPLOY
    #

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
        write_log(
            app_dir,
            "deploy.log",
            result.stdout
        )

    if result.stderr and result.returncode != 0:
        error(result.stderr)
        write_log(
            app_dir,
            "deploy.log",
            result.stderr
        )

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

            runtime = (
                metadata.get("runtime")
                or metadata.get("type")
                or "unknown"
            )

            info(
                f"{metadata['name']} - "
                f"{runtime} - "
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

def app_create_cmd(name, domain, port, type,repo,start):

    docker_ok = docker_create_cmd(
        name=name,
        domain=domain,
        port=port,
        type=type,
        repo=repo,
        start=start,
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
    #
    # WAIT FOR APP STARTUP
    #

    info("Waiting for app health...")

    health_ok = False

    for _ in range(10):

        health_result = run_command([
            "curl",
            "-I",
            f"http://127.0.0.1:{port}"
        ])

        if health_result.returncode == 0:
            health_ok = True
            break

        time.sleep(1)
        #
        # VERIFY HEALTH
        #

        if not health_ok:
            error("Health check failed")
            error("Rolling back deployment...")

            app_delete_cmd(name)

            return False

        #
        # SUCCESS
        #

    info(f"{name} fully deployed and healthy")
    return True

def app_redeploy_cmd(name):

    app_dir = Path(f"/opt/panel/apps/{name}")

    metadata_file = app_dir / "metadata.json"

    compose_file = app_dir / "docker-compose.yml"

    node_app_dir = app_dir / "app"

    #
    # VALIDATE APP
    #

    if not metadata_file.exists():
        error("App not found")
        return False

    #
    # LOAD METADATA
    #

    with open(metadata_file) as f:
        metadata = json.load(f)

    repo = metadata.get("repo")

    runtime = metadata.get("runtime")

    #
    # STOP CURRENT CONTAINERS
    #

    down_result = run_command([
        "sudo",
        DOCKER_BIN,
        "compose",
        "-f",
        str(compose_file),
        "down"
    ])

    if down_result.stdout:
        info(down_result.stdout)

    if down_result.stderr and down_result.returncode != 0:
        error(down_result.stderr)

    if down_result.returncode != 0:
        error("Failed stopping containers")
        return False

    #
    # GIT PULL
    #

    if repo:

        git_result = run_command([
            "sudo",
            "git",
            "-C",
            str(node_app_dir),
            "pull"
        ])

        if git_result.stdout:
            info(git_result.stdout)

        if git_result.stderr and git_result.returncode != 0:
            error(git_result.stderr)

        if git_result.returncode != 0:
            error("Git pull failed")
            return False

    #
    # NODE DEPENDENCIES
    #

    if runtime == "node":

        npm_result = run_command([
            "sudo",
            DOCKER_BIN,
            "run",
            "--rm",
            "-v",
            f"{node_app_dir}:/app",
            "-w",
            "/app",
            "node:20-alpine",
            "npm",
            "install"
        ])

        if npm_result.stdout:
            info(npm_result.stdout)

        if npm_result.stderr and npm_result.returncode != 0:
            error(npm_result.stderr)

        if npm_result.returncode != 0:
            error("npm install failed")
            return False

    #
    # START CONTAINERS
    #

    up_result = run_command([
        "sudo",
        DOCKER_BIN,
        "compose",
        "-f",
        str(compose_file),
        "up",
        "-d"
    ])

    if up_result.stdout:
        info(up_result.stdout)

    if up_result.stderr and up_result.returncode != 0:
        error(up_result.stderr)

    if up_result.returncode != 0:
        error("Redeploy failed")
        return False

    info(f"{name} redeployed")

    return True


def app_logs_cmd(name):

    app_dir = Path(f"/opt/panel/apps/{name}")

    logs_dir = app_dir / "logs"

    if not logs_dir.exists():
        error("Logs not found")
        return False

    deploy_log = logs_dir / "deploy.log"

    build_log = logs_dir / "build.log"

    #
    # DEPLOY LOGS
    #

    if deploy_log.exists():

        info("=== DEPLOY LOGS ===")

        with open(deploy_log) as f:
            print(f.read())

    #
    # BUILD LOGS
    #

    if build_log.exists():

        info("=== BUILD LOGS ===")

        with open(build_log) as f:
            print(f.read())

    return True


def runtime_logs_cmd(name):

    subprocess.run([
        "sudo",
        DOCKER_BIN,
        "logs",
        "-f",
        name
    ])


def app_status_cmd(name):

    result = run_command([
        "sudo",
        DOCKER_BIN,
        "ps",
        "-a",
        "--filter",
        f"name={name}"
    ])

    if result.stdout:
        print(result.stdout)

    if result.returncode != 0:
        error("Failed fetching status")
        return False

    return True


def volume_create_cmd(name):
    volume_dir = f"/opt/panel/volumes/{name}"

    run_command([
        "sudo",
        "mkdir",
        "-p",
        volume_dir
    ])

    run_command([
        "sudo",
        "chown",
        "-R",
        "ubuntu:ubuntu",
        volume_dir
    ])

    info(f"Volume {name} created")



def db_create_cmd(name, port):

    db_dir = f"/opt/panel/databases/{name}"

    volume_dir = f"/opt/panel/volumes/{name}"

    #
    # CREATE DIRECTORIES
    #

    run_command([
        "sudo",
        "mkdir",
        "-p",
        db_dir
    ])

    run_command([
        "sudo",
        "mkdir",
        "-p",
        volume_dir
    ])

    run_command([
        "sudo",
        "chown",
        "-R",
        "ubuntu:ubuntu",
        db_dir
    ])

    run_command([
        "sudo",
        "chown",
        "-R",
        "ubuntu:ubuntu",
        volume_dir
    ])

    #
    # DATABASE CREDENTIALS
    #

    db_name = name

    db_user = "panel"

    db_pass = secrets.token_hex(16)

    #
    # LOAD TEMPLATE
    #

    template_path = (
        Path.home()
        / "panel/templates/docker/postgres.yml"
    )

    with open(template_path) as f:
        template = Template(f.read())

    compose = template.render(
        NAME=name,
        PORT=port,
        DB_NAME=db_name,
        DB_USER=db_user,
        DB_PASS=db_pass
    )

    #
    # SAVE COMPOSE
    #

    with open("docker-compose.yml", "w") as f:
        f.write(compose)

    run_command([
        "sudo",
        "cp",
        "docker-compose.yml",
        f"{db_dir}/docker-compose.yml"
    ])

    #
    # METADATA
    #

    metadata = {
        "name": name,
        "type": "postgres",
        "port": port,
        "database": db_name,
        "user": db_user,
        "password": db_pass
    }

    with open("metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    run_command([
        "sudo",
        "cp",
        "metadata.json",
        f"{db_dir}/metadata.json"
    ])

    #
    # START DATABASE
    #

    result = run_command([
        "sudo",
        DOCKER_BIN,
        "compose",
        "-f",
        f"{db_dir}/docker-compose.yml",
        "up",
        "-d"
    ])

    if result.stdout:
        info(result.stdout)

    if result.stderr and result.returncode != 0:
        error(result.stderr)

    if result.returncode != 0:
        error("Database deployment failed")
        return False

    info(f"Database {name} created")

    info(f"User: {db_user}")

    info(f"Password: {db_pass}")

    return True