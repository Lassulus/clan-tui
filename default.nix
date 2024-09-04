{
  buildPythonApplication,
  makeWrapper,
  pytestCheckHook,
  setuptools,
  nix,
  textual,
  runCommand,
}:
let
  propagatedBuildInputs = [
    textual
  ];
in
buildPythonApplication {
  pname = "clan-tui";
  version = "1.0.0";
  src = ./.;
  format = "pyproject";
  buildInputs = [
    makeWrapper
    nix
  ];
  nativeBuildInputs = [ setuptools ];
  inherit propagatedBuildInputs;
  doCheck = true;
  checkPhase = ''
    PYTHONPATH= $out/bin/clan-tui --help
  '';
  passthru.tests.pytest =
    runCommand "pytest"
      {
        propagatedBuildInputs = propagatedBuildInputs;
        nativeBuildInputs = [
          pytestCheckHook
        ];
      }
      ''
        cp -r ${./.}/* .
        chmod -R +w .
        pytest .
        touch $out
      '';
}
