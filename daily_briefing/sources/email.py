"""Email source — fetches unread count and subjects via IMAP.

Uses stdlib `imaplib` — zero dependencies. Requires IMAP credentials
in .env (EMAIL_USER, EMAIL_PASSWORD, EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT).

Disabled by default in brief.yaml. Enable after configuring credentials.
"""

from __future__ import annotations

import email
import imaplib
import os
from typing import Any

from daily_briefing.sources.base import SourceProtocol, SourceResult

MAX_SUBJECTS = 5


class EmailSource(SourceProtocol):
    """Fetches unread email count and recent subjects via IMAP."""

    name = "email"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch unread email summary via IMAP."""
        imap_server = os.environ.get("EMAIL_IMAP_SERVER", "imap.gmail.com")
        imap_port = int(os.environ.get("EMAIL_IMAP_PORT", "993"))
        user = os.environ.get("EMAIL_USER", "")
        password = os.environ.get("EMAIL_PASSWORD", "")

        if not user or not password:
            return SourceResult(
                name=self.name,
                priority=70,
                error="Email not configured. Set EMAIL_USER and EMAIL_PASSWORD in .env",
            )

        try:
            unread_count, subjects = self._check_imap(imap_server, imap_port, user, password)
            return SourceResult(
                name=self.name,
                priority=70,
                data={
                    "unread_count": unread_count,
                    "recent_subjects": subjects,
                },
            )
        except imaplib.IMAP4.error as e:
            return SourceResult(
                name=self.name,
                priority=70,
                error=f"IMAP error: {e}",
            )
        except OSError as e:
            return SourceResult(
                name=self.name,
                priority=70,
                error=f"Connection error: {e}",
            )

    def _check_imap(
        self,
        server: str,
        port: int,
        user: str,
        password: str,
    ) -> tuple[int, list[str]]:
        """Connect to IMAP, count unread, fetch recent subject lines."""
        # Connect with SSL (standard IMAP port 993)
        mail = imaplib.IMAP4_SSL(server, port, timeout=15)
        try:
            mail.login(user, password)
            mail.select("INBOX")

            # Count unread messages
            status, messages = mail.search(None, "UNSEEN")
            unread_count = 0
            if status == "OK" and messages[0]:
                unread_count = len(messages[0].split())

            # Fetch subjects of recent unread messages
            subjects: list[str] = []
            if unread_count > 0:
                # Get the most recent unread messages (by UID, limited to MAX_SUBJECTS)
                status, data = mail.search(None, "UNSEEN")
                if status == "OK" and data[0]:
                    message_ids = data[0].split()
                    # Take the last N (most recent) IDs
                    recent_ids = message_ids[-MAX_SUBJECTS:]

                    for msg_id in recent_ids:
                        try:
                            status, msg_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
                            if status == "OK":
                                for part in msg_data:
                                    if isinstance(part, tuple):
                                        msg = email.message_from_bytes(part[1])
                                        subj = msg.get("Subject", "")
                                        if subj:
                                            # Decode RFC 2047 encoded subjects
                                            decoded = email.header.decode_header(subj)
                                            subj_str = ""
                                            for fragment, charset in decoded:
                                                if isinstance(fragment, bytes):
                                                    subj_str += fragment.decode(charset or "utf-8", errors="replace")
                                                else:
                                                    subj_str += fragment
                                            subjects.append(subj_str[:100])
                        except Exception:
                            continue

            return unread_count, subjects
        finally:
            mail.logout()
