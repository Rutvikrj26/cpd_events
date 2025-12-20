import typer
from commands import local

app = typer.Typer(help="CPD Events Local CLI")

app.add_typer(local.app, name="local", help="Local development commands")

if __name__ == "__main__":
    app()
