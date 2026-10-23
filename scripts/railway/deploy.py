"""Railway deployment commands. Invoked through the adjacent shell entrypoints."""

import argparse
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from dotenv import set_key
from dotenv.parser import parse_stream

ROOT = Path(__file__).resolve().parents[2]
API = "agent-os"
DATABASE = "pgvector"


class DeploymentError(Exception):
    pass


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise DeploymentError(f"Create {path} from example.env and configure production credentials first.")
    values = {}
    with path.open() as stream:
        for binding in parse_stream(stream):
            if binding.error or (binding.key is not None and binding.value is None):
                raise DeploymentError(
                    f"Invalid env file at {path}:{binding.original.line}; use KEY=value and quote PEMs."
                )
            if binding.key is not None:
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", binding.key):
                    raise DeploymentError(f"Invalid variable name at {path}:{binding.original.line}.")
                assert binding.value is not None
                values[binding.key] = binding.value
    # Values stay literal: never execute shell or interpolate another variable.
    return values


def save_env(path: Path, values: dict[str, str]) -> None:
    path.chmod(0o600)
    for key, value in values.items():
        set_key(path, key, value, quote_mode="always")
    path.chmod(0o600)


def validate_env(values: dict[str, str], *, require_auth: bool) -> None:
    if values.get("RUNTIME_ENV", "prd") != "prd":
        raise DeploymentError("Railway requires RUNTIME_ENV=prd. Development authorization cannot be deployed.")
    values["RUNTIME_ENV"] = "prd"
    if not values.get("OPENAI_API_KEY") or values["OPENAI_API_KEY"] == "sk-***":
        raise DeploymentError("Set OPENAI_API_KEY in the production env file.")
    # example.env ships the Claude key as a placeholder; upload an empty value instead so a
    # copied template clears the variable rather than shipping a bogus key.
    if values.get("ANTHROPIC_API_KEY") == "sk-***":
        values["ANTHROPIC_API_KEY"] = ""
    # AWS_PROFILE names a profile on this machine and means nothing inside the container.
    values.pop("AWS_PROFILE", None)
    for key in ("SANDBOX_ENABLED", "SANDBOX_IMAGE", "SANDBOX_RUNTIME_ARN"):
        if values.get(key):
            raise DeploymentError(f"{key} no longer configures a sandbox; select the provider in app/sandbox.py.")
    if bool(values.get("SLACK_BOT_TOKEN")) != bool(values.get("SLACK_SIGNING_SECRET")):
        raise DeploymentError("Set both SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET, or neither.")
    if values.get("MCP_CONNECT_SECRET") and len(values["MCP_CONNECT_SECRET"]) < 16:
        raise DeploymentError("MCP_CONNECT_SECRET must contain at least 16 characters.")
    if values.get("AGENTOS_URL"):
        origin = urlsplit(values["AGENTOS_URL"])
        if (
            origin.scheme != "https"
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.path not in {"", "/"}
            or origin.query
            or origin.fragment
        ):
            raise DeploymentError("AGENTOS_URL must be an HTTPS origin without credentials, a path, query or fragment.")
    if require_auth and not (values.get("JWT_VERIFICATION_KEY") or values.get("JWT_JWKS_FILE")):
        raise DeploymentError("Set JWT_VERIFICATION_KEY or JWT_JWKS_FILE before deploying the API.")


def railway(*args: str, value: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["railway", *args], cwd=ROOT, input=value or "", text=True, capture_output=True, timeout=600
    )
    if check and result.returncode:
        # Variable errors can echo stdin. Do not include those responses in logs.
        detail = "Variable upload rejected; values were not logged." if value is not None else result.stderr.strip()
        raise DeploymentError(f"railway {' '.join(args)} failed (exit {result.returncode}). {detail}")
    return result


def preflight() -> None:
    if not shutil.which("railway"):
        raise DeploymentError("Install Railway CLI 5.49.0 or newer, then run railway login.")
    version = re.search(r"(\d+)\.(\d+)\.(\d+)", railway("--version").stdout)
    if version is None or tuple(map(int, version.groups())) < (5, 49, 0):
        raise DeploymentError("Upgrade Railway CLI to 5.49.0 or newer.")
    railway("whoami")


def linked_project(*, allow_unlinked: bool = False) -> dict[str, Any] | None:
    result = railway("status", "--json", check=False)
    if result.returncode:
        if allow_unlinked and "no linked project" in result.stderr.lower():
            return None
        raise DeploymentError("Cannot inspect the linked Railway project. Check railway status and railway login.")
    project = json.loads(result.stdout)
    if not isinstance(project, dict) or any(
        not isinstance(project.get(key), str) or not project[key] for key in ("id", "name")
    ):
        raise DeploymentError("Railway returned an invalid project identity; stopping.")
    return project


def upload(service: str, values: dict[str, str]) -> None:
    for key, value in values.items():
        print(f"Setting {service}: {key}", flush=True)
        try:
            # Railway rejects empty stdin; KEY= clears a value without exposing a secret.
            if value == "":
                railway("variable", "set", f"{key}=", "--skip-deploys", "--service", service, value="")
            else:
                railway("variable", "set", key, "--stdin", "--skip-deploys", "--service", service, value=value)
        except (DeploymentError, subprocess.TimeoutExpired) as error:
            raise DeploymentError(
                f"{error} Earlier variables may have changed; no deployment was requested by this upload."
            ) from error


def provision(path: Path, workspace: str | None, with_checkpoint_volume: bool = False) -> int:
    values = read_env(path)
    validate_env(values, require_auth=False)
    if not workspace:
        raise DeploymentError("Pass --workspace <name-or-id> or set RAILWAY_WORKSPACE before provisioning.")
    preflight()
    if linked_project(allow_unlinked=True) is not None:
        raise DeploymentError("This checkout is already linked. Use env-sync.sh and redeploy.sh for that project.")
    if (urlsplit(values.get("AGENTOS_URL", "")).hostname or "").endswith(".up.railway.app"):
        raise DeploymentError(
            "AGENTOS_URL names an existing Railway deployment. Link it, or clear the stale URL first."
        )
    for key, expected in {"DB_HOST": "pgvector.railway.internal", "DB_PORT": "5432", "PORT": "8000"}.items():
        if values.get(key, expected) != expected:
            raise DeploymentError(f"First provisioning creates managed services; remove {key} or set it to {expected}.")
    managed = {
        "DB_HOST": "pgvector.railway.internal",
        "DB_PORT": "5432",
        "DB_USER": values.get("DB_USER") or "ai",
        "DB_PASS": values.get("DB_PASS") or secrets.token_urlsafe(32),
        "DB_DATABASE": values.get("DB_DATABASE") or "ai",
        "DB_DRIVER": "postgresql+psycopg",
        "WAIT_FOR_DB": "True",
        "PORT": "8000",
        "RUNTIME_ENV": "prd",
        "MCP_CONNECT_SECRET": values.get("MCP_CONNECT_SECRET") or secrets.token_urlsafe(32),
    }
    values.update(managed)
    save_env(path, managed)
    print("Creating billed Railway resources. Teardown: ./scripts/railway/down.sh", flush=True)
    try:
        railway("init", "--name", "agentos-railway", "--workspace", workspace)
        railway("add", "--service", DATABASE, "--image", "agnohq/pgvector:18")
        upload(
            DATABASE,
            {
                "POSTGRES_USER": values["DB_USER"],
                "POSTGRES_PASSWORD": values["DB_PASS"],
                "POSTGRES_DB": values["DB_DATABASE"],
            },
        )
        railway("volume", "--service", DATABASE, "add", "--mount-path", "/var/lib/postgresql")
        # The initial image deployment may still be building and cannot be redeployed.
        # Deploy from the configured image with the variables and volume now in place.
        railway("redeploy", "--service", DATABASE, "--from-source", "--yes")
        railway("add", "--service", API)
        if with_checkpoint_volume:
            railway("volume", "--service", API, "add", "--mount-path", "/data")
        domain = json.loads(railway("domain", "--service", API, "--port", "8000", "--json").stdout)
        if not isinstance(domain, dict):
            raise DeploymentError("Railway returned invalid domain JSON.")
        url = domain.get("domain") or next(iter(domain.get("domains", [])), None)
        if not isinstance(url, str) or not url.startswith("https://"):
            raise DeploymentError("Railway did not return a public HTTPS domain.")
        values["AGENTOS_URL"] = values.get("AGENTOS_URL") or url
        save_env(path, {"AGENTOS_URL": values["AGENTOS_URL"]})
        upload(API, values)
        print(f"URL: {values['AGENTOS_URL']}\nProduction settings and MCP connect secret are saved in {path}.")
        if not (values.get("JWT_VERIFICATION_KEY") or values.get("JWT_JWKS_FILE")):
            print(
                "Provisioned; the API has not been deployed.\n"
                "Connect this URL at https://os.agno.com with token-based authorization, then save the public\n"
                "JWT_VERIFICATION_KEY as a quoted PEM in the production env file (or configure JWT_JWKS_FILE).\n"
                f"Finish with: ./scripts/railway/env-sync.sh {shlex.quote(str(path))} --no-deploy\n"
                "Then: ./scripts/railway/redeploy.sh"
            )
            return 2
        railway("up", "--service", API, "-d")
    except DeploymentError, subprocess.TimeoutExpired, KeyboardInterrupt, ValueError:
        print(
            "Provisioning may have created billed resources. Inspect railway status before retrying.\n"
            "Do not create another project. Finish configuration on the linked project, or use "
            "./scripts/railway/down.sh.",
            file=sys.stderr,
        )
        raise
    print("Build submitted. Verify railway logs --service agent-os, /health, and authenticated access before sharing.")
    return 0


def sync_env(path: Path, no_deploy: bool) -> None:
    values = read_env(path)
    validate_env(values, require_auth=True)
    preflight()
    linked_project()
    upload(API, values)
    if no_deploy:
        print("Variables uploaded; no deployment triggered.")
    else:
        railway("redeploy", "--service", API, "--yes")
        print("Redeployment requested. Verify the live service before sharing.")


def redeploy() -> None:
    preflight()
    linked_project()
    railway("up", "--service", API, "-d")
    print("Build submitted. Inspect railway logs --service agent-os and verify the live service.")


def teardown(yes: bool) -> None:
    preflight()
    project = linked_project()
    assert project is not None
    print(f"Delete project {project['name']} ({project['id']}), all its services, volumes and database data.")
    if not yes and input("Type the project name to confirm: ") != project["name"]:
        raise DeploymentError("Aborted.")
    railway("delete", "--project", project["id"], "--yes", check=False)
    projects = json.loads(railway("list", "--json").stdout)
    if not isinstance(projects, list) or any(not isinstance(p, dict) or not p.get("id") for p in projects):
        raise DeploymentError("Cannot verify project deletion; the checkout stays linked.")
    if any(p["id"] == project["id"] for p in projects):
        raise DeploymentError("Project is still listed; the checkout stays linked. Inspect Railway before retrying.")
    railway("unlink", "--yes")
    print(
        "Project confirmed absent and checkout unlinked. Local env files were preserved.\n"
        "Review AGENTOS_URL and JWT verification settings before provisioning another project."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("up", "env-sync"):
        command = commands.add_parser(name)
        command.add_argument("env_file", nargs="?", type=Path, default=ROOT / ".env.production")
        if name == "up":
            command.add_argument("--workspace", default=os.getenv("RAILWAY_WORKSPACE"))
            command.add_argument(
                "--with-checkpoint-volume", action="store_true", help="Mount /data on the API for AgentCore checkpoints"
            )
        else:
            command.add_argument("--no-deploy", action="store_true")
    commands.add_parser("redeploy")
    commands.add_parser("down").add_argument("--yes", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "up":
            return provision(args.env_file.resolve(), args.workspace, args.with_checkpoint_volume)
        if args.command == "env-sync":
            sync_env(args.env_file.resolve(), args.no_deploy)
        elif args.command == "redeploy":
            redeploy()
        elif args.command == "down":
            teardown(args.yes)
    except (DeploymentError, OSError, ValueError, subprocess.TimeoutExpired, EOFError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Inspect railway status before retrying.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
