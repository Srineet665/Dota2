from discord_bot import build_invite_url


def test_build_invite_url_contains_required_parts():
    url = build_invite_url(1494040784033284216)
    assert "client_id=1494040784033284216" in url
    assert "scope=bot+applications.commands" in url
    assert "permissions=18432" in url
