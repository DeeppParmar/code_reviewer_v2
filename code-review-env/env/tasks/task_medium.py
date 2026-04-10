"""Medium task definition.

Provides a realistic Python API handler with exactly 4 real security bugs and
no red herrings, plus ground truth metadata with exact line numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from env.models import GroundTruthBug


@dataclass(frozen=True)
class TaskSpec:
    """Container for a task specification used by the environment."""

    task_id: str
    max_steps: int
    pr_title: str
    pr_description: str
    full_file: str
    code_diff: str
    ground_truth: List[GroundTruthBug]


def get_task() -> TaskSpec:
    """Return the medium task specification (buggy code + ground truth)."""

    full_file = "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from typing import Dict, Optional",
            "",
            "",
            "class FakeDB:",
            '    """Very small DB wrapper used by handlers in this service."""',
            "",
            "    def fetch_one(self, query: str) -> Optional[Dict[str, str]]:",
            "        return {\"id\": \"42\", \"owner_id\": \"7\", \"content\": \"hello\"}",
            "",
            "",
            "def render_profile_html(display_name: str) -> str:",
            '    """Render profile page HTML (simplified)."""',
            "    return f\"<h1>{display_name}</h1>\"",
            "",
            "",
            "def get_profile_handler(current_user_id: str, requested_user_id: str, q: str) -> Dict[str, str]:",
            '    """Return a user profile payload for the web app."""',
            "    db = FakeDB()",
            "    api_key = \"sk_live_51HARD_CODED_SECRET\"",
            "    query = \"SELECT id, owner_id, content FROM profiles WHERE id = '\" + requested_user_id + \"'\"",
            "    row = db.fetch_one(query)",
            "    html = render_profile_html(q)",
            "    return {\"api_key\": api_key, \"profile_id\": row[\"id\"], \"html\": html, \"owner\": row[\"owner_id\"]}",
            "",
        ]
    )

    code_diff = "\n".join(
        [
            "--- a/handlers.py",
            "+++ b/handlers.py",
            "@@",
            "+def get_profile_handler(current_user_id: str, requested_user_id: str, q: str) -> Dict[str, str]:",
            "+    api_key = \"sk_live_51HARD_CODED_SECRET\"",
            "+    query = \"SELECT id, owner_id, content FROM profiles WHERE id = '\" + requested_user_id + \"'\"",
            "+    row = db.fetch_one(query)",
            "+    html = render_profile_html(q)",
            "+    return {\"api_key\": api_key, \"profile_id\": row[\"id\"], \"html\": html, \"owner\": row[\"owner_id\"]}",
        ]
    )

    ground_truth = [
        GroundTruthBug(
            line_number=20,
            severity="major",
            category="security",
            description="Hardcoded secret: API key embedded as a string literal in the handler.",
        ),
        GroundTruthBug(
            line_number=21,
            severity="critical",
            category="security",
            description="SQL injection: query built via string concatenation using user-controlled requested_user_id.",
        ),
        GroundTruthBug(
            line_number=23,
            severity="major",
            category="security",
            description="Missing input validation: user-controlled q is used directly in HTML rendering, enabling XSS with crafted input.",
        ),
        GroundTruthBug(
            line_number=24,
            severity="critical",
            category="security",
            description="IDOR: no authorization check that current_user_id can access requested_user_id profile/resource.",
        ),
    ]

    return TaskSpec(
        task_id="medium",
        max_steps=15,
        pr_title="Add profile API handler",
        pr_description=(
            "This PR adds a handler powering the profile page. It fetches a profile row and "
            "renders a small HTML snippet for the web app."
        ),
        full_file=full_file,
        code_diff=code_diff,
        ground_truth=ground_truth,
    )

