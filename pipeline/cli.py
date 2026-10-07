import typer

app = typer.Typer()


@app.callback()
def main() -> None:
    """Explainer Engine: document -> narrated explainer pipeline."""


if __name__ == "__main__":
    app()
