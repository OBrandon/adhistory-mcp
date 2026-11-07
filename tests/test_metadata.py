"""Release metadata must agree, or the registry publish fails."""

import json
import tomllib
from pathlib import Path

from adhistory_mcp import __version__

ROOT = Path(__file__).resolve().parent.parent


def test_versions_and_names_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    server = json.loads((ROOT / "server.json").read_text())
    pkg = server["packages"][0]
    assert project["version"] == __version__ == server["version"] == pkg["version"]
    assert pkg["identifier"] == project["name"] == "adhistory-mcp"
    assert pkg["registryType"] == "pypi"
    assert len(server["description"]) <= 100
    env = {e["name"]: e for e in pkg["environmentVariables"]}
    assert env["APIFY_TOKEN"]["isRequired"] and env["APIFY_TOKEN"]["isSecret"]


def test_readme_has_registry_ownership_line():
    server = json.loads((ROOT / "server.json").read_text())
    readme = (ROOT / "README.md").read_text()
    assert f"<!-- mcp-name: {server['name']} -->" in readme
