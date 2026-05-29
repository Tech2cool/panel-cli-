from fastapi import (
    FastAPI,
    Header,
    HTTPException
)
import os
from dotenv import load_dotenv
from old.docker_manager import *
from old.nginx_manager import *
from old.ssl_manager import ssl_enable_cmd

load_dotenv()

API_KEY = os.getenv("API_KEY")

app = FastAPI()

def verify_api_key(authorization: str = Header(None)):

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    expected = f"Bearer {API_KEY}"

    if authorization != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
#
# ROOT
#


@app.get("/")
def root(
    authorization: str = Header(None)
):

    verify_api_key(authorization)

    return {
        "message": "Panel API running"
    }

#
# LIST APPS
#

@app.get("/apps")
def list_apps(
    authorization: str = Header(None)
):

    verify_api_key(authorization)
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
    start: str = "node server.js",
    authorization: str = Header(None)

):
    verify_api_key(authorization)

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
def redeploy_app(name: str,  authorization: str = Header(None)):
    verify_api_key(authorization)

    result = app_redeploy_cmd(name)

    return {
        "success": result
    }

#
# DELETE APP
#

@app.delete("/apps/delete")
def delete_app(name: str,authorization: str = Header(None)):
    verify_api_key(authorization)

    result = app_delete_cmd(name)

    return {
        "success": result
    }

#
# APP LOGS
#

@app.get("/apps/logs")
def app_logs(name: str,authorization: str = Header(None)):
    verify_api_key(authorization)

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
def create_db(name: str, port: int,authorization: str = Header(None)):
    verify_api_key(authorization)

    result = db_create_cmd(name, port)

    return {
        "success": result
    }

#
# ENABLE SSL
#

@app.post("/ssl/enable")
def enable_ssl(domain: str,authorization: str = Header(None)):
    verify_api_key(authorization)

    result = ssl_enable_cmd(domain)

    return {
        "success": result
    }

@app.post("/webhook/github")
async def github_webhook(payload: dict):

    repo_url = payload["repository"]["clone_url"]

    apps_dir = Path("/opt/panel/apps")

    for app_dir in apps_dir.iterdir():

        metadata_file = app_dir / "metadata.json"

        if metadata_file.exists():

            with open(metadata_file) as f:
                metadata = json.load(f)

            app_repo = metadata.get("repo")

            if app_repo == repo_url:

                app_name = metadata["name"]

                app_redeploy_cmd(app_name)

                return {
                    "success": True,
                    "redeployed": app_name
                }

    return {
        "success": False,
        "message": "No matching app"
    }