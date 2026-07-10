import pytest

from app.mind.shell_parsing import (
    ShellParseError,
    flag_bool,
    flag_string,
    parse_command,
    time_filter,
)


def test_parse_command_preserves_quoted_arguments_and_normalizes_aliases() -> None:
    parsed = parse_command(
        'memory write --type user_preference --content "una preferenza precisa" '
        '--reason="utile" --future_use "domani"'
    )

    assert parsed.namespace == "memory"
    assert parsed.action == "write"
    assert flag_string(parsed, "content") == "una preferenza precisa"
    assert flag_string(parsed, "future-use") == "domani"
    assert flag_string(parsed, "reason") == "utile"


def test_parse_command_keeps_boolean_time_flags_for_shell_handlers() -> None:
    parsed = parse_command('session list --query "ieri" --yesterday --limit 5')

    assert flag_bool(parsed, False, "yesterday") is True
    assert time_filter(parsed, default_basis="conversation") == {
        "preset": "yesterday",
        "from": None,
        "to": None,
        "basis": "conversation",
    }


@pytest.mark.parametrize(
    ("command", "code"),
    [
        ("", "shell.empty_command"),
        ('memory search "unterminated', "shell.parse_error"),
    ],
)
def test_parse_command_returns_structured_recovery_errors(
    command: str,
    code: str,
) -> None:
    with pytest.raises(ShellParseError) as captured:
        parse_command(command)

    assert captured.value.code == code
    assert captured.value.actions
