import re
from datetime import timedelta
from itertools import takewhile
from typing import ClassVar

import arrow
from pydantic import BaseModel

from bot.exts.filtering._filter_context import Event, FilterContext
from bot.exts.filtering._filters.filter import UniqueFilter

LINK_RE = re.compile(r"(https?://\S+)")


class ExtraLinksSettings(BaseModel):
    """Extra settings for when to trigger the antispam rule."""

    interval_description: ClassVar[str] = (
        "Look for rule violations in messages from the last `interval` number of seconds."
    )
    threshold_description: ClassVar[str] = "Maximum number of links before the filter is triggered."

    interval: int = 10
    threshold: int = 10


class LinksFilter(UniqueFilter):
    """Detects too many links sent by a single user."""

    name = "links"
    events = (Event.MESSAGE,)
    extra_fields_type = ExtraLinksSettings

    async def triggered_on(self, ctx: FilterContext) -> bool:
        """Search for the filter's content within a given context."""
        earliest_relevant_at = arrow.utcnow() - timedelta(seconds=self.extra_fields.interval)
        relevant_messages = list(takewhile(lambda msg: msg.created_at > earliest_relevant_at, ctx.content))
        detected_messages = {msg for msg in relevant_messages if msg.author == ctx.author}

        total_links = 0
        messages_with_links = 0
        for msg in detected_messages:
            if total_matches := len(LINK_RE.findall(msg.content)):
                messages_with_links += 1
                total_links += total_matches

        if total_links > self.extra_fields.threshold and messages_with_links > 1:
            ctx.related_messages |= detected_messages
            ctx.filter_info[self] = f"sent {total_links} links"
            return True
        return False
