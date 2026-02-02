import click
import elasticai.experiment_framework.synthesis as synth


def cli():
    @click.group
    def main():
        pass

    main.add_command(synth.main, "synth")
    main.add_command(synth.main, "s")
    main()


if __name__ == "__main__":
    cli()
