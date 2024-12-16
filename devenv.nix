{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/packages/
  packages = [
    pkgs.git
    pkgs.bash
  ];

  # https://devenv.sh/languages/
  languages.python.enable = true;
  languages.python.uv.enable = true;
  languages.python.uv.package = pkgs.uv;
  languages.python.uv.sync.enable = true;
  languages.python.venv.enable = true;
  languages.python.version = "3.11";

  # https://devenv.sh/scripts/
  scripts.generate-model.exec = ''
    ./source/model/generate_model.sh
  '';

  git-hooks.hooks = {
    # lint shell scripts
    shellcheck.enable = true;

    # format Python code
    black.enable = true;

        typos.enable = true;
        yamllint.enable = true;
        yamlfmt.enable = true;    
        check-toml.enable = true;
  };

}