{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:
let
  pkgs-unstable = import inputs.nixpkgs-unstable { system = pkgs.stdenv.system; };
in
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
    $DEVENV_ROOT/dlt_source_affinity/model/generate_model.sh
  '';

  git-hooks.hooks = {
    shellcheck.enable = true;
    shellcheck.excludes = [
      ".envrc"
    ];
    ruff.enable = true;
    ruff-format.enable = true;
    typos.enable = true;
    yamllint.enable = true;
    yamlfmt.enable = true;
    yamlfmt.settings.lint-only = false;
    check-toml.enable = true;
    commitizen.enable = true;
    commitizen.package = pkgs-unstable.commitizen;
    nixfmt-rfc-style.enable = true;
    markdownlint.enable = true;
    mdformat.enable = true;
    mdformat.package = pkgs.mdformat.withPlugins (
      ps: with ps; [
        mdformat-frontmatter
      ]
    );
    trufflehog.enable = true;
  };

  scripts.format.exec = ''
    markdownlint --fix .
    pre-commit run --all-files
  '';

  scripts.test-all.exec = ''
    pytest -s -vv "$@"
  '';

  scripts.deps-upgrade.exec = ''
    uv \
      sync \
      --all-extras \
      --upgrade
  '';

  enterTest = ''
    test-all
  '';

  scripts.build.exec = ''
    uv build
  '';

  scripts.sample-pipeline-run.exec = ''
    python $DEVENV_ROOT/affinity_pipeline.py
  '';

  scripts.sample-pipeline-show.exec = ''
    cd "$DEVENV_ROOT"
    dlt pipeline affinity_pipeline show
  '';
}
