from fastapi import FastAPI

from docker_manager import *
from nginx_manager import *
from ssl_manager import ssl_enable_cmd

app = FastAPI()

#
# ROOT
#

@app.get("/")
def root():

    return {
        "message": "Panel API running"
    }

#
# LIST APPS
#

@app.get("/apps")
def list_apps():

    apps = []

    apps_dir = Path("/opt/panel/apps")

    if apps_dir.exists():

        for app_dir in apps_dir.iterdir():

            metadata_file = app_dir / "metadata.json"

            if metadata_file.exists():

                with open(metadata_file) as f:
                    metadata = json.load(f)

                apps.append(metadata)

    return apps

#
# CREATE APP
#

@app.post("/apps/create")
def create_app(
    name: str,
    domain: str,
    port: int,
    type: str = "node",
    repo: str = None,
    start: str = "node server.js"
):

    result = app_create_cmd(
        name,
        domain,
        port,
        type,
        repo,
        start
    )

    return {
        "success": result
    }

#
# REDEPLOY APP
#

@app.post("/apps/redeploy")
def redeploy_app(name: str):

    result = app_redeploy_cmd(name)

    return {
        "success": result
    }

#
# DELETE APP
#

@app.delete("/apps/delete")
def delete_app(name: str):

    result = app_delete_cmd(name)

    return {
        "success": result
    }

#
# APP LOGS
#

@app.get("/apps/logs")
def app_logs(name: str):

    app_dir = Path(f"/opt/panel/apps/{name}")

    logs_dir = app_dir / "logs"

    deploy_log = ""

    build_log = ""

    deploy_file = logs_dir / "deploy.log"

    build_file = logs_dir / "build.log"

    if deploy_file.exists():

        with open(deploy_file) as f:
            deploy_log = f.read()

    if build_file.exists():

        with open(build_file) as f:
            build_log = f.read()

    return {
        "deploy_log": deploy_log,
        "build_log": build_log
    }

#
# CREATE DATABASE
#

@app.post("/db/create")
def create_db(name: str, port: int):

    result = db_create_cmd(name, port)

    return {
        "success": result
    }

#
# ENABLE SSL
#

@app.post("/ssl/enable")
def enable_ssl(domain: str):

    result = ssl_enable_cmd(domain)

    return {
        "success": result
    }