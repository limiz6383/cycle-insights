import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_citations as vc  # noqa: E402


class CitationStructure(unittest.TestCase):
    def test_every_kb_entry_has_a_source_or_is_marked_unsourced(self):
        self.assertEqual(vc.structure_problems(ROOT / "prompts" / "v3.4.md"), [])


if __name__ == "__main__":
    unittest.main()
