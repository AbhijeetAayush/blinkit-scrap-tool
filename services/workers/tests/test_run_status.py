def test_dispatched_is_not_terminal():
    from src.app.run_status import is_run_terminal

    assert is_run_terminal("dispatched") is False
    assert is_run_terminal("running") is False
    assert is_run_terminal("derived") is True
    assert is_run_terminal("error") is True
    assert is_run_terminal("budget") is True
