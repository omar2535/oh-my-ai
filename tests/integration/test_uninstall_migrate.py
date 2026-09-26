from conftest import install_fake

NPM_CODEX = ".nvm/versions/node/v22.18.0/lib/node_modules/@openai/codex/bin/codex.js"


def fake_npm(fake_home):
    fake_home.write_fake(
        "npm",
        [
            {
                "args": ["uninstall", "-g", "@openai/codex"],
                "sh": f"rm -f ~/{NPM_CODEX}; [ -e ~/.local/bin/codex ] || rm -f ~/.local/bin/codex",
            }
        ],
    )


def test_uninstall_keeps_config_and_credentials(fake_home, cli):
    install_fake(fake_home, "codex")
    fake_npm(fake_home)
    result = cli("uninstall", "codex")
    assert result.exit_code == 0, result.output
    assert ["uninstall", "-g", "@openai/codex"] in fake_home.calls("npm")
    assert not fake_home.path(NPM_CODEX).exists()
    assert fake_home.path(".codex/auth.json").exists()


def test_purge_removes_config(fake_home, cli):
    install_fake(fake_home, "hermes")
    result = cli("uninstall", "hermes", "--purge", "--yes")
    assert result.exit_code == 0, result.output
    assert not fake_home.path(".hermes").exists()
    assert not fake_home.path(".local/bin/hermes").exists()


def test_migrate_codex_from_nvm_npm_to_standalone(fake_home, cli):
    install_fake(fake_home, "codex")
    fake_npm(fake_home)
    staged = fake_home.write_fake("codex", [{"args": ["--version"], "stdout": "codex-cli 0.157.1\n"}], staged=True)
    script = (
        f"mkdir -p ~/.codex/packages/standalone && cp {staged} ~/.codex/packages/standalone/codex "
        "&& ln -sf ~/.codex/packages/standalone/codex ~/.local/bin/codex\n"
    )
    fake_home.write_fake("curl", [{"args": ["-fsSL", "https://chatgpt.com/codex/install.sh"], "stdout": script}])

    result = cli("migrate", "codex", "--to", "standalone")

    assert result.exit_code == 0, result.output
    assert "npm → standalone" in result.output
    assert not fake_home.path(NPM_CODEX).exists()
