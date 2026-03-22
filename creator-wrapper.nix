{
  creator-src ? builtins.fetchGit {
    url = "https://github.com/es-ude/elastic-ai.creator";
    rev = "9e36f47323841dcd3341139ab39c0ac4f2384527";  # Known good revision
  }:
  {
    hdl = import (creator-src + "/devenv_modules/hdl");
    torch_backend = import (creator-src + "/devenv_modules/torch_backend");
  }
