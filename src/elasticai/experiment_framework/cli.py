import click
import elasticai.experiment_framework.synthesis as synth
import elasticai.experiment_framework.remote_control as rc
import elasticai.experiment_framework.remote_control_v2 as rc_v2


@click.group()
def cli():
    pass


cli.add_command(rc.main, name="rc")
cli.add_command(synth.main, name="synth")
cli.add_command(rc_v2.main, name="rc-v2")


if __name__ == "__main__":
    cli()