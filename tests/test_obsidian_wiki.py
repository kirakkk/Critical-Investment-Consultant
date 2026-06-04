import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cic.obsidian_wiki import USER_SECTION_END, USER_SECTION_START, export_radar_wiki_if_configured, write_radar_wiki
from cic.radar_report import analyze_radar_input


class ObsidianWikiTest(unittest.TestCase):
    def setUp(self):
        self.sample = json.loads(Path("data/sample_radar_signals.json").read_text(encoding="utf-8"))
        self.report = analyze_radar_input(self.sample, use_llm=False)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_writes_llm_wiki_pages_for_radar_report(self):
        result = write_radar_wiki(self.report, self.root)

        self.assertEqual(result["status"], "exported")
        files = result["files"]
        for key in ("raw", "report", "company", "theme", "index", "log", "schema"):
            self.assertTrue(Path(files[key]).exists(), key)

        claim_paths = sorted((self.root / "claim").glob("*.md"))
        source_paths = sorted((self.root / "source").glob("*.md"))
        task_paths = sorted((self.root / "task").glob("*.md"))
        self.assertGreater(len(claim_paths), 0)
        self.assertGreater(len(source_paths), 0)
        self.assertGreater(len(task_paths), 0)

        company_text = Path(files["company"]).read_text(encoding="utf-8")
        self.assertIn("[[theme/", company_text)
        self.assertIn(USER_SECTION_START, company_text)

        raw_text = Path(files["raw"]).read_text(encoding="utf-8")
        self.assertIn("```json", raw_text)
        self.assertIn("001309.SZ", raw_text)

    def test_preserves_user_notes_inside_generated_pages(self):
        first = write_radar_wiki(self.report, self.root)
        company_path = Path(first["files"]["company"])
        text = company_path.read_text(encoding="utf-8")
        note_body = "## 我的笔记\n\n- 人工补充：跟踪 SSD 扩产兑现。"
        start = text.index(USER_SECTION_START) + len(USER_SECTION_START)
        end = text.index(USER_SECTION_END, start)
        company_path.write_text(text[:start] + "\n" + note_body + "\n" + text[end:], encoding="utf-8")

        second = write_radar_wiki(self.report, self.root)

        updated = Path(second["files"]["company"]).read_text(encoding="utf-8")
        self.assertIn("人工补充：跟踪 SSD 扩产兑现。", updated)
        self.assertIn("## 核心 Claims", updated)

    def test_env_configured_export(self):
        with patch.dict("os.environ", {"CIC_OBSIDIAN_WIKI_PATH": str(self.root)}, clear=False):
            result = export_radar_wiki_if_configured(self.report)

        self.assertEqual(result["status"], "exported")
        self.assertTrue(Path(result["files"]["index"]).exists())


if __name__ == "__main__":
    unittest.main()
