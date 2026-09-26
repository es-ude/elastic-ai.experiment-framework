import click

import elasticai.experiment_framework.synthesis as synth
from elasticai.experiment_framework.env5 import fpga


@click.group()
def cli():
    pass


cli.add_command(fpga, name="fpga")
cli.add_command(synth.main, name="synth")


if __name__ == "__main__":
    cli()
