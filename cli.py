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
    app_list_cmd,
    docker_create_cmd,
    docker_list_cmd,
    docker_logs_cmd,
    docker_restart_cmd,
    docker_stop_cmd
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
    type: str = typer.Option("node")
):
    app_create_cmd(name, domain, port,type)


@app.command()
def ssl_enable(domain: str):
    ssl_enable_cmd(domain)

if __name__ == "__main__":
    app()

