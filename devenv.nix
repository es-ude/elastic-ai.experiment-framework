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

  ];

  

  languages.python = {
    enable = true;
    uv.enable = true;
  };

   "check:fast-tests" = {
      exec = ''
        ${uv_run} coverage run
        ${uv_run} coverage xml
      '';
      before = ["check:tests"];
    };

    "check:types" = {
      exec = "${uv_run} mypy -p elasticai.creator";
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
      exec = "${unstablePkgs.uv}/bin/uv build";
    };

     "check:code-lint" = {
    };

    "check:tests" = {
    }; # this is triggered in CI with --mode before flag

}
