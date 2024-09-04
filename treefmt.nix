{ inputs, ... }:
{
  imports = [ inputs.treefmt-nix.flakeModule ];

  perSystem =
    { pkgs, ... }:
    {
      treefmt = {
        # Used to find the project root
        projectRootFile = ".git/config";

        programs.deno.enable = pkgs.hostPlatform.system != "riscv64-linux";
        programs.mypy.enable = true;
        programs.nixfmt.enable = pkgs.hostPlatform.system != "riscv64-linux";
        programs.nixfmt.package = pkgs.nixfmt-rfc-style;
        programs.deadnix.enable = true;
        programs.ruff.check = true;
        programs.ruff.format = true;
        programs.rustfmt.enable = true;
        programs.shfmt.enable = true;
        settings.formatter.shfmt.includes = [ "*.envrc" ];
      };
    };
}
