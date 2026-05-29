#!/home/ubuntu/panel/venv/bin/python

from site_manager import site_create_cmd, site_disable_cmd, site_enable_cmd, site_list_cmd
import typer


app = typer.Typer()

@app.command()
def hello():
    print("Panel works!")



@app.command()
def hello2():
    print("Panel works!2")


@app.command()
def site_create(
    name: str,
    domain: str,
    site_type: str = typer.Option("static"),
    port: int = typer.Option(None),
):
    site_create_cmd(
        name=name,
        domain=domain,
        site_type=site_type,
        port=port,
    )


@app.command()
def site_list():
    site_list_cmd()


@app.command()
def site_disable(domain: str):
    site_disable_cmd(domain)


@app.command()
def site_enable(domain: str):
    site_enable_cmd(domain)


if __name__ == "__main__":
    app()

