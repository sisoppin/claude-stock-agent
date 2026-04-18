from agent import user


def test_watchlist_add_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    assert user.get_watchlist() == []
    user.add_to_watchlist("INFY")
    user.add_to_watchlist("tcs")
    assert user.get_watchlist() == ["INFY", "TCS"]


def test_watchlist_add_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.add_to_watchlist("INFY")
    result = user.add_to_watchlist("INFY")
    assert "already" in result
    assert len(user.get_watchlist()) == 1


def test_watchlist_remove(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.add_to_watchlist("INFY")
    user.remove_from_watchlist("INFY")
    assert user.get_watchlist() == []


def test_watchlist_remove_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    result = user.remove_from_watchlist("INFY")
    assert "not in" in result


def test_format_watchlist_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    assert "empty" in user.format_watchlist()


def test_format_watchlist_with_stocks(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.add_to_watchlist("INFY")
    assert "INFY" in user.format_watchlist()


def test_portfolio_add_holding(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.add_holding("GRSE", 100, 1800)
    pf = user.get_portfolio()
    assert len(pf) == 1
    assert pf[0]["ticker"] == "GRSE"
    assert pf[0]["qty"] == 100
    assert pf[0]["buy_price"] == 1800


def test_portfolio_add_same_ticker_averages(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.add_holding("GRSE", 100, 1800)
    user.add_holding("GRSE", 100, 2000)
    pf = user.get_portfolio()
    assert len(pf) == 1
    assert pf[0]["qty"] == 200
    assert pf[0]["buy_price"] == 1900.0


def test_portfolio_remove(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.add_holding("GRSE", 100, 1800)
    user.remove_holding("GRSE")
    assert user.get_portfolio() == []


def test_portfolio_remove_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    result = user.remove_holding("GRSE")
    assert "not in" in result


def test_format_portfolio_with_live_data(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.add_holding("INFY", 50, 1500)
    stock_cache = {"INFY": {"price": 1800}}
    report = user.format_portfolio(stock_cache)
    assert "INFY" in report
    assert "₹" in report


def test_format_portfolio_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    assert "empty" in user.format_portfolio({})


def test_preferences_set_and_get(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.set_preference("max_pe", 20)
    prefs = user.get_preferences()
    assert prefs["max_pe"] == 20.0


def test_preferences_set_sectors(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.set_preference("sectors", "Technology,Healthcare")
    prefs = user.get_preferences()
    assert prefs["sectors"] == ["Technology", "Healthcare"]


def test_preferences_clear(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.set_preference("max_pe", 20)
    user.clear_preferences()
    prefs = user.get_preferences()
    assert prefs["max_pe"] is None


def test_preferences_unknown_key(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    result = user.set_preference("unknown_key", 10)
    assert "Unknown" in result


def test_format_preferences(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.user._USER_FILE", tmp_path / "user_profile.json")
    user.set_preference("sectors", "Technology")
    result = user.format_preferences()
    assert "Technology" in result
