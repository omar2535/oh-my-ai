#!/bin/sh
# omai bootstrap: install uv (user-local) if missing, install omai, then converge.
#   curl -fsSL https://raw.githubusercontent.com/omar2535/oh-my-ai/main/bootstrap.sh | sh
# Never uses sudo.
set -eu

OMAI_SOURCE="${OMAI_SOURCE:-git+https://github.com/omar2535/oh-my-ai}"

if ! command -v uv >/dev/null 2>&1; then
    echo "==> installing uv (user-local)"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    PATH="$HOME/.local/bin:$PATH"
    export PATH
fi

echo "==> installing omai from $OMAI_SOURCE"
uv tool install --force "$OMAI_SOURCE"

echo "==> omai up"
exec "$HOME/.local/bin/omai" up "$@"
