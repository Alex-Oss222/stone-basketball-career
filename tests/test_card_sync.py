import json
from pathlib import Path
import tempfile
import unittest

from runtime import signing

TEAM = signing.TEAM


class CardSyncTests(unittest.TestCase):
    def test_control_line_follows_the_register_and_nothing_else_changes(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / TEAM / "Team/Roster").mkdir(parents=True)
        (root / TEAM / "Team/Player_Cards").mkdir(parents=True)
        (root / TEAM / "Team/Roster/roster.json").write_text(json.dumps({"as_of": "2003-07-21", "players": [
            {"id": "test_player", "name": "Test Player", "control": "Re-signed July 17, 2003."}]}))
        card = root / TEAM / "Team/Player_Cards/test_player.md"
        card.write_text("# Test Player | Miami Heat Player Profile\n\n**Contract/control:** Contract reaches June 30. [Finance record](x).\n\n## Assessment\n\nUnassessed\n")
        writer = signing.Writer(root)
        signing.sync_cards(writer, "2003-07-31")
        writer.commit()
        text = card.read_text()
        self.assertIn("**Contract/control:** Re-signed July 17, 2003. (register, 2003-07-21)", text)
        self.assertNotIn("June 30", text)
        self.assertIn("## Assessment\n\nUnassessed", text)
        writer = signing.Writer(root)
        signing.sync_cards(writer, "2003-07-31")
        self.assertEqual(writer.texts, {})                  # idempotent: an unchanged register writes nothing


if __name__ == "__main__":
    unittest.main()
