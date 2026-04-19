#!/usr/bin/env bash
# File: .devcontainer/post-create.sh
#
# Description:
# Installs OPA, Regal, and Conftest, then sets up pre-commit hooks.
# Versions match those used in .pre-commit-config.yaml and CI workflow.

set -euo pipefail

CONFTEST_VERSION="0.61.0"

echo "==> Installing OPA (latest)..."
curl -sL -o /tmp/opa "https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static"
chmod +x /tmp/opa
sudo mv /tmp/opa /usr/local/bin/opa
echo "    opa $(opa version | head -1)"

echo "==> Installing Regal (latest)..."
REGAL_VERSION=$(curl -sL "https://api.github.com/repos/StyraInc/regal/releases/latest" \
  | grep '"tag_name"' | cut -d '"' -f 4)
curl -sL -o /tmp/regal \
  "https://github.com/StyraInc/regal/releases/download/${REGAL_VERSION}/regal_Linux_x86_64"
chmod +x /tmp/regal
sudo mv /tmp/regal /usr/local/bin/regal
echo "    $(regal version)"

echo "==> Installing Conftest v${CONFTEST_VERSION}..."
curl -sL -o /tmp/conftest.tar.gz \
  "https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}/conftest_${CONFTEST_VERSION}_Linux_x86_64.tar.gz"
tar -xzf /tmp/conftest.tar.gz -C /tmp conftest
sudo mv /tmp/conftest /usr/local/bin/conftest
rm /tmp/conftest.tar.gz
echo "    $(conftest --version)"

echo "==> Installing pre-commit..."
pip install --quiet pre-commit
pre-commit install
echo "    $(pre-commit --version)"

echo "==> Done."
