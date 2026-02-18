from __future__ import annotations

import logging
from pathlib import Path

import click

from config.parser import load_json_or_jsonc
from core.interpreter import ConfigInterpreter

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("mapack")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--target",
    "targets",
    multiple=True,
    help="Target(s) to execute. If omitted, all targets are executed.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Build plan without writing output files.")
def main(config_file: Path, targets: tuple[str, ...], dry_run: bool) -> None:
    """Pack maps from a JSON/JSONC config file."""
    config_path = config_file.resolve()
    config = load_json_or_jsonc(config_path)

    interpreter = ConfigInterpreter(config=config, config_path=config_path)
    outputs_by_target = interpreter.run(list(targets) if targets else None, dry_run=dry_run)

    click.echo("Build finished.")
    for target_name, outputs in outputs_by_target.items():
        click.echo(f"- target={target_name}")
        if outputs:
            for output in outputs:
                click.echo(f"  - {output}")
        else:
            click.echo("  - (no exported artifacts)")


if __name__ == "__main__":
    main()
