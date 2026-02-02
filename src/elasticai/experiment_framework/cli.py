import click
import elasticai.experiment_framework.synthesis as synth

import elasticai.experiment_framework.remote_control as rc


def cli():
    @click.group
    def main():
        pass

    main.add_command(rc.main, name="rc")
    main.add_command(synth.main, "synth")

    main()


if __name__ == "__main__":
    cli()
