import pytest
from elasticai.experiment_framework.synthesis import (
    load_synthesis_config_from_env,
    SynthesisConfig,
)


def test_loading_from_empty_env_uses_defaults() -> None:
    conf = load_synthesis_config_from_env(SynthesisConfig, {})
    assert conf == SynthesisConfig()


def test_loading_from_env_with_custom_values() -> None:
    custom_env = {
        "SYNTH_HOST": "192.168.1.100",
        "SYNTH_SSH_USER": "testuser",
        "SYNTH_SSH_PORT": "2222",
        "SYNTH_TARGET": "env5",
        "SYNTH_WORKING_DIR": "/custom/working/dir",
        "SYNTH_KEY": "custom_key",
        "SYNTH_QUIET": "False",
    }
    conf = load_synthesis_config_from_env(SynthesisConfig, custom_env)
    assert conf.host == "192.168.1.100"
    assert conf.ssh_user == "testuser"
    assert conf.ssh_port == 2222
    assert conf.target == "env5"
    assert conf.working_dir == "/custom/working/dir"
    assert conf.key == "custom_key"
    assert not conf.quiet


def test_loading_from_env_with_partial_values() -> None:
    partial_env = {"SYNTH_HOST": "10.0.0.1", "SYNTH_KEY": "partial_key"}
    conf = load_synthesis_config_from_env(SynthesisConfig, partial_env)
    assert conf.host == "10.0.0.1"
    assert conf.key == "partial_key"
    # Other fields should use defaults
    assert conf.ssh_user == ""
    assert conf.ssh_port == 22
    assert conf.target == "env5"
    assert conf.working_dir == "~/"
    assert conf.quiet


def test_loading_from_env_with_invalid_type() -> None:
    invalid_env = {"SYNTH_SSH_PORT": "not_a_number"}
    with pytest.raises((ValueError, TypeError)):
        load_synthesis_config_from_env(SynthesisConfig, invalid_env)
