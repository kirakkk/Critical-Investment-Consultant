import unittest

from cic.agent_skills import (
    agent_skill_manifest,
    get_agent_profile,
    skills_for_agent,
    validate_agent_skill_profiles,
)


class AgentSkillProfileTest(unittest.TestCase):
    def skill_ids(self, agent_id):
        return {skill.skill_id for skill in skills_for_agent(agent_id, include_optional=True)}

    def test_all_agent_skill_profiles_are_valid(self):
        self.assertEqual(validate_agent_skill_profiles(), [])

    def test_bear_case_agent_has_scrape_and_analysis_skills(self):
        skills = self.skill_ids("bear_case_agent")
        self.assertIn("public_web_scrape", skills)
        self.assertIn("financial_statement_analysis", skills)
        self.assertIn("market_snapshot_analysis", skills)
        self.assertIn("peer_comparison_analysis", skills)
        self.assertIn("contradiction_mining", skills)
        self.assertIn("source_catalog_gate", skills)

    def test_contradiction_agent_can_fetch_official_and_public_counter_evidence(self):
        skills = self.skill_ids("contradiction_agent")
        self.assertIn("official_disclosure_fetch", skills)
        self.assertIn("public_web_scrape", skills)
        self.assertIn("pdf_announcement_extract", skills)
        self.assertIn("financial_statement_analysis", skills)

    def test_source_gated_agents_include_source_catalog_gate(self):
        for agent_id in ("intake_agent", "validation_agent", "diff_risk_agent", "data_fetch_agent"):
            profile = get_agent_profile(agent_id)
            self.assertIn("source_catalog_gate", profile.required_skill_ids)

    def test_kol_scout_does_not_auto_scrape_social_sources(self):
        profile = get_agent_profile("kol_scout")
        self.assertNotIn("public_web_scrape", profile.required_skill_ids)
        self.assertIn("manual_source_ingest", profile.required_skill_ids)
        self.assertIn("kol_profile_lookup", profile.required_skill_ids)

    def test_editor_agent_cannot_fetch_new_sources(self):
        manifest = agent_skill_manifest("editor_agent")
        skill_ids = {item["skill_id"] for item in manifest["skills"]}
        self.assertNotIn("public_web_scrape", skill_ids)
        self.assertNotIn("official_disclosure_fetch", skill_ids)
        self.assertEqual(manifest["default_budget"]["max_sources"], 0)


if __name__ == "__main__":
    unittest.main()

