"""Regression checks for consolidated v1.19 UI, without HA runtime dependencies."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "smartify_sip_manager/index.html").read_text(encoding="utf-8")
JS = (ROOT / "smartify_sip_manager/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "smartify_sip_manager/app.css").read_text(encoding="utf-8")


class NavigationRegressionTests(unittest.TestCase):
    def test_five_work_areas_have_matching_subnav(self):
        areas = re.findall(r'<button[^>]+data-area="([^"]+)"', HTML)
        subareas = re.findall(r'data-subarea="([^"]+)"', HTML)
        self.assertEqual(areas, ["overview", "participants", "groups", "video", "tools"])
        self.assertEqual(subareas, areas)

    def test_every_nav_tab_opens_a_real_panel(self):
        tab_ids = re.findall(r'<button[^>]+data-tab="([^"]+)"', HTML)
        panel_ids = set(re.findall(r'<section[^>]+id="([^"]+)"', HTML))
        panel_area = json.loads(re.search(r"const PANEL_AREA=(\{[^\n]+\});", JS).group(1))
        area_start = json.loads(re.search(r"const AREA_START=(\{[^\n]+\});", JS).group(1))
        self.assertEqual(len(tab_ids), len(set(tab_ids)))
        self.assertTrue(set(tab_ids).issubset(panel_ids))
        self.assertEqual(set(tab_ids), set(panel_area))
        self.assertEqual(set(area_start), set(re.findall(r'<button[^>]+data-area="([^"]+)"', HTML)))
        for area, start in area_start.items():
            self.assertIn(start, tab_ids)
            self.assertEqual(panel_area[start], area)

    def test_save_apply_reload_controls_and_dialog_survive(self):
        for control in ("globalSave", "globalApply", "globalReload",
                        "globalConfirmDialog", "globalConfirmTitle",
                        "globalConfirmText", "anSave", "rgSave", "erzApply",
                        "draftApply", "groupDirectSave", "epDirectSave"):
            with self.subTest(control=control):
                self.assertIn('id="' + control + '"', HTML)
        self.assertIn("globalAction('save')", JS)
        self.assertIn("globalAction('apply')", JS)
        self.assertIn("globalAction('reload')", JS)

    def test_old_reload_buttons_hidden_without_deleting_handlers(self):
        self.assertIn("#reloadPjsip,#reloadDialplan{display:none!important}", CSS)
        for control in ("reloadPjsip", "reloadDialplan"):
            self.assertIn('id="' + control + '"', HTML)
            self.assertIn("$('" + control + "').onclick", JS)


if __name__ == "__main__":
    unittest.main()
