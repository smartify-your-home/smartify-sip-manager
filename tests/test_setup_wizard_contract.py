"""Contract tests for the direct-edit setup wizard (no running Asterisk required)."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WIZARD = ROOT / "smartify_sip_manager" / "setup-wizard.js"


def test_javascript_syntax():
    node = shutil.which("node")
    if not node:
        return  # CI without Node can still run the contract assertions below.
    subprocess.run([node, "--check", str(WIZARD)], check=True)


def test_wizard_uses_existing_model_and_optimistic_locking():
    source = WIZARD.read_text(encoding="utf-8")
    assert "api/anlage" in source
    assert "data.hash!==hash" in source
    assert "JSON.stringify({model:copy,hash})" in source
    assert "structuredClone(original)" in source
    assert "copy.wege" in source and "copy.teilnehmer" in source


def test_wizard_has_direct_configuration_fields():
    source = WIZARD.read_text(encoding="utf-8")
    for field in (
        "ha_benutzer", "qualify_frequency", "browser_mod_entity",
        "video_codecs", "sip_adresse", "quell_ips", "darf_anrufen",
        "angerufen_von", "anruf_ziele", "klingelzeit", "mitglieder_rufen",
        "data-member", "go2rtc_https_url",
    ):
        assert field in source


def test_wizard_requires_explicit_save_and_no_auto_apply():
    source = WIZARD.read_text(encoding="utf-8")
    assert "Validieren & speichern" in source
    assert "api/erzeugen/uebernehmen" not in source
    assert "api/ami/command" not in source


def test_linphone_cloud_template_has_username_only_and_safe_manual_fallback():
    source = WIZARD.read_text(encoding="utf-8")
    assert "wizCloudProvider" in source
    assert "wizLinphoneUsername" in source
    assert "sip.linphone.org" in source
    assert "'linphone-cloud'" in source and "'linphone-in'" in source
    assert "Anderer SIP-Anbieter / manuell" in source
    assert "cloudPreset==='linphone'" in source


def test_cloud_fields_are_specific_and_unrelated_device_fields_are_hidden():
    source = WIZARD.read_text(encoding="utf-8")
    assert "if(cloud)return" in source
    cloud_form = source.split("if(cloud)return", 1)[1].split("const local=", 1)[0]
    assert "Quell-IPs" in cloud_form and "Ausgehender SIP-Anschluss" in cloud_form
    assert "browser_mod_entity" not in cloud_form
    assert "qualify_frequency" not in cloud_form
    assert "ring_player" not in cloud_form
    assert "tuer_entity" not in cloud_form
    assert "const browser=ha?" in source
    assert "const doorEntities=door?" in source


def test_original_graphical_ring_group_editor_is_embedded_not_duplicated():
    source = WIZARD.read_text(encoding="utf-8")
    assert "const ringPanel=$('rufgruppen')" in source
    assert "dialog.appendChild(ringPanel)" in source
    assert "window.smartifyRufgruppen?.()" in source
    assert "dialog.addEventListener('close',restoreRingPanel)" in source
    assert "ringHome.insertBefore(ringPanel,ringNext)" in source


def test_auto_answer_is_inline_for_sip_core_only_and_uses_safe_api():
    source = WIZARD.read_text(encoding="utf-8")
    assert "if(kind!=='participant'||draft?.typ!=='ha_geraet')return ''" in source
    assert "data-action=\"aa-preview\"" in source
    assert "data-action=\"aa-apply\"" in source
    assert "api/sip-core/auto-answer/stage" in source
    assert "api/sip-core/diff" in source
    assert "api/sip-core/apply" in source
    assert "active_hash:aaDraft.hash,confirm:true" in source
