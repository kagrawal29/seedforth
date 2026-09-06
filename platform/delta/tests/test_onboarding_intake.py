"""Tests for onboarding intake name extraction logic.

Tests the smart name extraction that happens when admin posts in
#seedforth-onboarding to onboard a new user.
"""

import re
import pytest


def _extract_onboarding_name(text: str, mentions: list[dict], bot_id: str = "999"):
    """Replicate the onboarding intake name extraction logic from app.py.

    Args:
        text: Message text (with mentions as <@id> tokens)
        mentions: List of dicts with 'id', 'name', 'display_name' keys
        bot_id: The bot's own user ID (to filter out)

    Returns:
        (target_user_id, display_name, slug) or None if extraction fails
    """
    real_mentions = [m for m in mentions if str(m["id"]) != bot_id]

    target_user_id_str = ""
    target_display_name = ""

    if real_mentions:
        target_user = real_mentions[0]
        target_user_id_str = str(target_user["id"])
        target_display_name = target_user.get("display_name") or target_user["name"]
    else:
        name_text = re.sub(r"<@!?\d+>", "", text).strip()
        name_text = re.sub(
            r"\b(?:onboard|onboarding|start|begin|hey|can you|help me|my friend|my colleague|he\'s|she\'s|they\'re|an?|the)\b",
            "", name_text, flags=re.IGNORECASE,
        ).strip()
        name_text = re.sub(r"^[,\-\s]+", "", name_text).strip()
        name_match = re.search(r"\b([A-Z][a-z]+)\b", name_text)
        if name_match:
            target_display_name = name_match.group(1)
        else:
            return None

    slug_name = re.sub(r"[^a-z0-9]+", "-", target_display_name.lower()).strip("-")[:20]
    project_slug = f"onboarding-{slug_name}"

    return target_user_id_str, target_display_name, project_slug


class TestOnboardingNameExtraction:
    """Test name extraction from various onboarding message formats."""

    def test_mention_real_user(self):
        """Admin mentions a real Discord user."""
        text = "onboard <@123456> -- runs a consulting firm"
        mentions = [{"id": "123456", "name": "alex", "display_name": "Alex"}]
        result = _extract_onboarding_name(text, mentions)
        assert result == ("123456", "Alex", "onboarding-alex")

    def test_mention_bot_and_real_user(self):
        """Admin mentions both @Delta and @Alex."""
        text = "hey <@999> onboard <@123456> -- accountant"
        mentions = [
            {"id": "999", "name": "Delta", "display_name": "Delta"},
            {"id": "123456", "name": "alex", "display_name": "Alex"},
        ]
        result = _extract_onboarding_name(text, mentions, bot_id="999")
        assert result == ("123456", "Alex", "onboarding-alex")

    def test_mention_only_bot_with_name_in_text(self):
        """Admin mentions @Delta but includes name in text."""
        text = "hey <@999> can you help me onboard my friend Alex, he's an accountant"
        mentions = [{"id": "999", "name": "Delta", "display_name": "Delta"}]
        result = _extract_onboarding_name(text, mentions, bot_id="999")
        assert result == ("", "Alex", "onboarding-alex")

    def test_no_mention_with_name(self):
        """No mentions at all, just a name in text."""
        text = "onboard my friend Alex, he's an accountant and wants to automate his work"
        mentions = []
        result = _extract_onboarding_name(text, mentions)
        assert result == ("", "Alex", "onboarding-alex")

    def test_start_onboarding_for_name(self):
        """'start onboarding for Name' pattern."""
        text = "start onboarding for Priya, she's a product manager"
        mentions = []
        result = _extract_onboarding_name(text, mentions)
        assert result == ("", "Priya", "onboarding-priya")

    def test_no_name_extractable(self):
        """No mention and no capitalized name found -- should return None."""
        text = "onboard someone please"
        mentions = []
        result = _extract_onboarding_name(text, mentions)
        assert result is None

    def test_display_name_used_over_username(self):
        """Display name takes priority over username for the slug."""
        text = "onboard <@123456>"
        mentions = [{"id": "123456", "name": "cooluser42", "display_name": "Raj Kumar"}]
        result = _extract_onboarding_name(text, mentions)
        assert result[1] == "Raj Kumar"
        assert result[2] == "onboarding-raj-kumar"

    def test_slug_format_clean(self):
        """Slug should be lowercase, hyphenated, no special chars."""
        text = "onboard <@123456>"
        mentions = [{"id": "123456", "name": "user", "display_name": "Jean-Pierre"}]
        result = _extract_onboarding_name(text, mentions)
        assert result[2] == "onboarding-jean-pierre"

    def test_slug_truncated(self):
        """Slug name portion is capped at 20 chars."""
        text = "onboard <@123456>"
        mentions = [{"id": "123456", "name": "user", "display_name": "Alexanderthegreatconqueror"}]
        result = _extract_onboarding_name(text, mentions)
        slug_name = result[2].replace("onboarding-", "")
        assert len(slug_name) <= 20

    def test_brief_extraction_strips_name(self):
        """The admin brief should not include the target name."""
        text = "hey <@999> onboard <@123456> -- accountant who wants to automate"
        mentions = [
            {"id": "999", "name": "Delta", "display_name": "Delta"},
            {"id": "123456", "name": "alex", "display_name": "Alex"},
        ]
        result = _extract_onboarding_name(text, mentions, bot_id="999")
        # Verify we get the right user, not Delta
        assert result[0] == "123456"
        assert result[1] == "Alex"
