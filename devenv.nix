{
  pkgs,
  lib,
  config,
  inputs,
  ...
}: {
  packages = [
    pkgs.alejandra
    pkgs.ruff
    pkgs.cocogitto
    pkgs.git-cliff
    pkgs.cmake
    pkgs.gcc-arm-embedded-13
    pkgs.ninja
    pkgs.picotool
    pkgs.ty
    pkgs.pyrefly
  ];

  languages.c.enable = true;
  languages.cplusplus.enable = true;
  languages.python = {
    enable = true;
    package = pkgs.python312;
    uv.enable = true;
    uv.sync.enable = true;
    uv.sync.allExtras = true;
  };

  tasks = let
    uv_run = "${pkgs.uv}/bin/uv run";
  in {
    "check:fast-tests" = {
      exec = ''
        ${uv_run} coverage run
        ${uv_run} coverage xml
      '';
      before = ["check:tests"];
    };

    "check:types" = {
      exec = ''
        ${uv_run} pyrefly check 'src/**/*.py*' 'tests/**/*.py*'
        ${uv_run} ty check
      '';
      before = ["check:code-lint"];
    };

    "check:python-lint" = {
      exec = "${uv_run} ruff check";
      before = ["check:code-lint"];
    };

    "check:commit-lint" = {
      exec = ''
        if $CI; then
          ${pkgs.cocogitto}/bin/cog check ..$GITHUB_SOURCE_REF
        else
          ${pkgs.cocogitto}/bin/cog check --from-latest-tag --ignore-merge-commits
        fi
      '';
    };

    "check:formatting" = {
      exec = "${uv_run} ruff format --check";
      before = ["check:code-lint"];
    };

    "check:architecture" = {
      exec = "${uv_run} tach check";
      before = ["check:code-lint"];
    };

    "package:build" = {
      exec = "${pkgs.uv}/bin/uv build";
    };

    "check:code-lint" = {
    };

    "check:tests" = {
    }; # this is triggered in CI with --mode before flag
  };
}
