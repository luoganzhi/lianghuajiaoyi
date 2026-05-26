from src.trading import environment


def test_validate_trading_environment_rejects_unconfirmed_real_trading(capsys):
    assert environment.validate_trading_environment(
        is_simulated=False,
        allow_real_trading=False,
        credentials=("key", "secret", "password"),
    ) is False

    output = capsys.readouterr().out
    assert "ALLOW_REAL_TRADING=true" in output


def test_validate_trading_environment_rejects_missing_sim_credentials(capsys):
    assert environment.validate_trading_environment(
        is_simulated=True,
        credentials=("key", "", None),
    ) is False

    output = capsys.readouterr().out
    assert "SIM_API_SECRET" in output
    assert "SIM_API_PASSWORD" in output


def test_validate_trading_environment_allows_confirmed_real_credentials(capsys):
    assert environment.validate_trading_environment(
        is_simulated=False,
        allow_real_trading=True,
        credentials=("key", "secret", "password"),
    ) is True

    output = capsys.readouterr().out
    assert "实盘交易已启用" in output


def test_get_trading_credentials_selects_environment(monkeypatch):
    monkeypatch.setattr(environment, "SIM_API_KEY", "sim-key")
    monkeypatch.setattr(environment, "SIM_API_SECRET", "sim-secret")
    monkeypatch.setattr(environment, "SIM_API_PASSWORD", "sim-password")
    monkeypatch.setattr(environment, "REAL_API_KEY", "real-key")
    monkeypatch.setattr(environment, "REAL_API_SECRET", "real-secret")
    monkeypatch.setattr(environment, "REAL_API_PASSWORD", "real-password")

    assert environment.get_trading_credentials(True) == ("sim-key", "sim-secret", "sim-password")
    assert environment.get_trading_credentials(False) == ("real-key", "real-secret", "real-password")
