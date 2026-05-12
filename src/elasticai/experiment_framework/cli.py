import click
import elasticai.experiment_framework.synthesis as synth


@click.group()
def cli():
    pass


cli.add_command(synth.main, name="synth")


if __name__ == "__main__":
    cli()