{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  packages = [
    pkgs.git
    pkgs.bash
  ];

  languages.python.enable = true;
  languages.python.uv.enable = true;
  languages.python.uv.package = pkgs.uv;
  languages.python.uv.sync.enable = true;
  languages.python.uv.sync.allExtras = true;
  languages.python.venv.enable = true;
  languages.python.version = "3.12";

  scripts.generate-model.exec = ''
    ./source/model/generate_model.sh
  '';

  git-hooks.hooks = {
    shellcheck.enable = true;
    black.enable = true;
    typos.enable = true;
    yamllint.enable = true;
    yamlfmt.enable = true;
    check-toml.enable = true;
    commitizen.enable = true;
    nixfmt-rfc-style.enable = true;
  };

  scripts.format.exec = ''
    yamlfmt .
    pre-commit run --all-files
  '';

}
