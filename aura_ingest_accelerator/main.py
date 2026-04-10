import logging
import typer
from rich.console import Console

app = typer.Typer()
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def run(
    # Add your command arguments here, e.g.:
    # input: str = typer.Option(..., "--input", "-i", help="Input file path."),
    # output: str = typer.Option("output.json", "--output", "-o", help="Output file."),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
):
    """aura-ingest-accelerator — main entry point."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    console.print("[bold green]✅ aura-ingest-accelerator started[/bold green]")
    # TODO: implement


if __name__ == "__main__":
    app()
