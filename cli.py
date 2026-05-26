#!/home/ubuntu/panel/venv/bin/python

from ssl_manager import ssl_enable_cmd
import typer
from nginx_manager import (
    site_create_cmd,
    site_list_cmd,
    site_disable_cmd,
    site_enable_cmd,
    site_delete_cmd
)

from docker_manager import (
    app_create_cmd,
    app_delete_cmd,
    app_link_db_cmd,
    app_list_cmd,
    app_logs_cmd,
    app_redeploy_cmd,
    app_status_cmd,
    db_create_cmd,
    docker_create_cmd,
    docker_list_cmd,
    docker_logs_cmd,
    docker_restart_cmd,
    docker_stop_cmd,
    runtime_logs_cmd,
    volume_create_cmd
)

app = typer.Typer()

@app.command()
def hello():
    print("Panel works!")


@app.command()
def site_create(
    domain: str,
    type: str = typer.Option(...),
    port: int = typer.Option(None)
):
    site_create_cmd(domain,type, port)
  

@app.command()
def site_list():
    site_list_cmd()

@app.command()
def app_list():
    app_list_cmd()

@app.command()
def site_disable(domain: str):
    site_disable_cmd(domain)

@app.command()
def site_enable(domain: str):
    site_enable_cmd(domain)


@app.command()
def site_delete(domain: str):
    site_delete_cmd(domain)


@app.command()
def docker_create(name: str,
    domain: str,
    port: int,
    type: str = typer.Option(...)
    ):
    docker_create_cmd(name,domain, port,type)

def docker_list():
    docker_list_cmd()

@app.command()
def docker_logs(name: str):
    docker_logs_cmd(name)

@app.command()
def docker_restart(name: str):
    docker_restart_cmd(name)


@app.command()
def docker_stop(name: str):
    docker_stop_cmd(name)

@app.command()
def app_delete(name: str):
    app_delete_cmd(name)

@app.command()
def app_create(
    name: str,
    domain: str,
    port: int,
    type: str = typer.Option("node"),
    repo: str = typer.Option(None),
    start: str = typer.Option("node server.js")
):
    app_create_cmd(name, domain, port,type, repo,start)

@app.command()
def app_redeploy(name: str):
    app_redeploy_cmd(name)

@app.command()
def ssl_enable(domain: str):
    ssl_enable_cmd(domain)


@app.command()
def app_logs(name: str):
    app_logs_cmd(name)
    

@app.command()
def runtime_logs(name: str):
    runtime_logs_cmd(name)


@app.command()
def app_status(name: str):
    app_status_cmd(name)

@app.command()
def volume_create(name: str):
    volume_create_cmd(name)


@app.command()
def db_create(name: str, port: int):
    db_create_cmd(name, port)



@app.command()
def app_link_db(app_name: str, db_name: str):
    app_link_db_cmd(app_name, db_name)


if __name__ == "__main__":
    app()



