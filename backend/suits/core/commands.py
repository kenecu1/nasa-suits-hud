"""Command messages from the client -> changes to the Store. No sockets here.

A command is checked against the ``Command`` model in contract.py. Anything else (not JSON,
not a command, an unknown name, extra fields, too long) is logged once and dropped: the
client never gets an error back, and the wearer sees the effect only through the next State,
which always shows what the backend holds (docs/briefs/M2.md, section 6).
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from suits.contract import Command
from suits.core.store import Store

log = logging.getLogger(__name__)

# A real command is under 100 bytes. Anything far longer is not one of ours.
MAX_COMMAND_CHARS = 1024


def parse(text: str) -> Command | None:
    """The command in ``text``, or None (logged) if it is not a valid command."""
    if len(text) > MAX_COMMAND_CHARS:
        log.warning("dropped a command message of %d characters (limit %d)",
                    len(text), MAX_COMMAND_CHARS)
        return None
    try:
        return Command.model_validate_json(text)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in e['loc']) or 'message'}: {e['msg']}"
            for e in exc.errors()
        )
        log.warning("dropped an invalid command message (%s): %.200r", problems, text)
        return None


def dispatch(command: Command, store: Store) -> bool:
    """Carry out a valid command. Returns True if the State changed (send it soon)."""
    if command.name == "ack_alert":
        acked = store.ack(command.args.id)
        if acked is None:
            # Normal when the alert cleared, or a newer press already acked it (decision B).
            log.info("ack_alert %s: nothing to acknowledge",
                     repr(command.args.id) if command.args.id else "(top)")
            return False
        log.info("ack_alert: acknowledged %s", acked)
        return True
    if command.name == "toggle_details":
        log.info("toggle_details: details page %s", "open" if store.toggle_details() else "closed")
        return True
    # Unreachable while CommandName and this function agree; loud if someone adds a name only
    # to the contract.
    raise ValueError(f"no handler for command {command.name!r}")


def handle(text: str, store: Store) -> bool:
    """Parse and carry out one text frame. Returns True if the State changed."""
    command = parse(text)
    return command is not None and dispatch(command, store)
