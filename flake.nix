{
  inputs = {
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";
    devenv.url = "github:cachix/devenv";
    creator.url = "github:es-ude/elastic-ai.creator";
  };

  outputs = {
    self,
    nixpkgs,
    devenv,
    creator,
  }:
    devenv.lib.mkDevenv {
      inherit (devenv) inputs;
      modules = [
        (import creator + "/devenv_modules/hdl")
        (import creator + "/devenv_modules/torch_backend")
      ];
    };
}
