"""
A simple way to run Explorer locally.

It will use your default datacube settings

(overridable with datacube environment variables, such
as DATACUBE_ENVIRONMENT)

"""
from textwrap import dedent

import click
from click import style
from werkzeug.serving import run_simple


def _print_version(ctx, param, value):
    """Print version information and exit"""
    if not value or ctx.resilient_parsing:
        return

    import cubedash
    import datacube

    click.echo(
        f"Open Data Cube:\n"
        f"    {style('Explorer', bold=True)} version: {cubedash.__version__}\n"
        f"    {style('Core', bold=True)} version: {datacube.__version__}"
    )
    ctx.exit()


@click.command(help=__doc__)
@click.option(
    "--debug", "debug_mode", is_flag=True, default=False, help="Enable debug mode"
)
@click.option(
    "--version",
    is_flag=True,
    callback=_print_version,
    expose_value=False,
    is_eager=True,
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help=dedent(
        """\
        Enable all log messages, instead of just errors.

        Logging goes to stdout unless `--event-log-file` is specified.

        Logging is coloured plain-text if going to a tty, and jsonl format otherwise.

        Use twice to enable debug logging too.
        """
    ),
)
@click.option(
    "-l",
    "--event-log-file",
    help="Output jsonl logs to file",
    type=click.Path(writable=True, dir_okay=True),
)
@click.option("-h", "--hostname", default="localhost")
@click.option("-p", "--port", type=int, default="8080")
@click.option("-w", "--workers", type=int, default=3)
def cli(
    hostname: str,
    port: int,
    debug_mode: bool,
    workers: int,
    event_log_file: str,
    verbose: bool,
):
    from cubedash import app
    from cubedash.logs import init_logging

    init_logging(
        open(event_log_file, "a") if event_log_file else None, verbosity=verbose
    )

    if debug_mode:
        app.debug = True
    run_simple(hostname, port, app, use_reloader=debug_mode, processes=workers)
