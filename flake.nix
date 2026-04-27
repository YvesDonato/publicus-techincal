{
  description = "Publicus technical workspace";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      nixpkgs,
      ...
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      perSystem =
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          nodejs = pkgs.nodejs_22;
          backendPython = pkgs.python3.withPackages (
            pythonPackages: with pythonPackages; [
              fastapi
              httpx
              pydantic
              pydantic-settings
              pytest
              pytest-asyncio
              python-multipart
              uvicorn
            ]
          );
          frontendSrc = ./frontend;
          npmDepsHash = "sha256-2tMpuPpgETmQHeE9y1EACSAmnam/LcuQ5RO59vj6MpQ=";
          npmDeps = pkgs.fetchNpmDeps {
            name = "publicus-frontend-0.0.1-npm-deps";
            src = frontendSrc;
            hash = npmDepsHash;
          };

          frontend = pkgs.buildNpmPackage {
            pname = "publicus-frontend";
            version = "0.0.1";
            src = frontendSrc;

            inherit npmDeps nodejs;

            nativeBuildInputs = [ pkgs.makeWrapper ];
            npmBuildScript = "build";

            installPhase = ''
              runHook preInstall

              mkdir -p "$out/lib/publicus-frontend" "$out/bin"
              cp -R build "$out/lib/publicus-frontend/"

              makeWrapper ${nodejs}/bin/node "$out/bin/publicus-frontend" \
                --set NODE_ENV production \
                --add-flags "$out/lib/publicus-frontend/build/index.js"

              runHook postInstall
            '';

            meta = {
              description = "SvelteKit frontend for Publicus";
              mainProgram = "publicus-frontend";
            };
          };

          frontendCheck = pkgs.buildNpmPackage {
            pname = "publicus-frontend-check";
            version = "0.0.1";
            src = frontendSrc;

            inherit npmDeps nodejs;

            npmBuildScript = "check";

            installPhase = ''
              runHook preInstall
              mkdir -p "$out"
              touch "$out/check-passed"
              runHook postInstall
            '';
          };
        in
        {
          inherit
            backendPython
            frontend
            frontendCheck
            nodejs
            pkgs
            ;
        };
    in
    {
      packages = forAllSystems (
        system:
        let
          inherit (perSystem system) backendPython frontend pkgs;
        in
        {
          inherit frontend;
          backend-python = backendPython;
          uv = pkgs.uv;
          default = frontend;
        }
      );

      apps = forAllSystems (system: {
        frontend = {
          type = "app";
          program = "${self.packages.${system}.frontend}/bin/publicus-frontend";
          meta = {
            description = "Run the Publicus SvelteKit frontend server";
          };
        };
        default = self.apps.${system}.frontend;
      });

      checks = forAllSystems (
        system:
        let
          inherit (perSystem system) frontend frontendCheck;
        in
        {
          inherit frontend;
          frontend-check = frontendCheck;
        }
      );

      formatter = forAllSystems (
        system:
        let
          inherit (perSystem system) pkgs;
        in
        pkgs.writeShellApplication {
          name = "format-publicus";
          runtimeInputs = [ pkgs.nixfmt ];
          text = ''
            if [ "$#" -eq 0 ]; then
              set -- flake.nix
            fi

            exec nixfmt "$@"
          '';
        }
      );

      devShells = forAllSystems (
        system:
        let
          inherit (perSystem system) backendPython nodejs pkgs;
        in
        {
          default = pkgs.mkShell {
            packages = [
              backendPython
              nodejs
              pkgs.direnv
              pkgs.git
              pkgs.nil
              pkgs.nixfmt
              pkgs.uv
            ]
            ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
              pkgs.chromium
            ];

            shellHook = ''
              export PATH="$PWD/frontend/node_modules/.bin:$PATH"
              export UV_PROJECT_ENVIRONMENT="$PWD/backend/.venv"

              echo "Node: $(node --version)"
              echo "Python: $(python --version)"
              echo "uv: $(uv --version)"
              echo "Backend: Python, uv, FastAPI, Uvicorn, Pydantic, HTTPX, and pytest are available"
              echo "Backend API: uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload"
              echo "Business Benefits Finder category route: requires Chromium, included in this Linux dev shell"
              echo "Frontend: npm --prefix frontend install && npm --prefix frontend run dev -- --host 0.0.0.0"
            '';
          };
        }
      );
    };
}
