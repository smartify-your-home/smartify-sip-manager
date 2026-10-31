"""Tests für externe Ziele und Wege im Dialplan (v1.8)."""
import importlib.util, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1] / 'smartify_sip_manager'
sys.path.insert(0, str(ROOT))
import anlage as A  # noqa: E402
import generator as G  # noqa: E402

F = lambda **k: {'kamerabild': False, 'video_im_anruf': False, 'ios': False, 'tuer_oeffnen': False, **k}
EXT = ('[default]\nexten => 906,1,NoOp(Test Linphone Push)\n same => n,Dial(PJSIP/linphone-cloud/sip:beispielkonto@sip.linphone.org,30)\n'
       '\n[tuer]\nexten => 999,1,Hangup()\n')
EPS = {'110': {'context': 'tuer'}, '104': {'context': 'default'}, '105': {'context': 'default'}, 'linphone-cloud': {'context': ''}}


def model(**extra):
    m = A.leer()
    m['teilnehmer'] = [
        {'nummer': '110', 'typ': 'tuerstation', 'name': 'Haustür', 'faehigkeiten': F()},
        {'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': F()},
        {'nummer': '105', 'typ': 'ha_geraet', 'name': 'Browser', 'faehigkeiten': F()},
        {'nummer': '', 'typ': 'extern_ziel', 'name': 'Handy', 'endpoint': 'linphone-cloud',
         'sip_adresse': 'sip:beispielkonto@sip.linphone.org', 'faehigkeiten': F(video_im_anruf=True)},
        {'nummer': '907', 'typ': 'extern_ziel', 'name': 'Handy Büro', 'endpoint': 'linphone-cloud', 'sip_adresse': 'buero@sip.linphone.org', 'faehigkeiten': F()},
    ]
    m['wege'] = [{'name': 'Klingel Haustür', 'nummer': '600', 'von': ['110'],
                  'ziele': ['104', '105', 'sip:beispielkonto@sip.linphone.org'], 'klingelzeit': 30}]
    m.update(extra)
    return A.validate(m)


class ModelTests(unittest.TestCase):
    def test_extern_ziel(self):
        m = model()
        t = next(x for x in m['teilnehmer'] if x['name'] == 'Handy')
        self.assertEqual(t['sip_adresse'], 'beispielkonto@sip.linphone.org')
        self.assertEqual(A.ref_of(t), 'sip:beispielkonto@sip.linphone.org')

    def test_ref_follows_new_number(self):
        m = model()
        next(t for t in m['teilnehmer'] if t['name'] == 'Handy')['nummer'] = '908'
        m = A.validate(m)
        self.assertIn('908', m['wege'][0]['ziele'])
        self.assertNotIn('sip:beispielkonto@sip.linphone.org', m['wege'][0]['ziele'])

    def test_errors(self):
        bad = model()
        next(t for t in bad['teilnehmer'] if t['name'] == 'Handy')['sip_adresse'] = 'kein-at'
        with self.assertRaisesRegex(ValueError, 'SIP-Adresse'):
            A.validate(bad)
        bad = model()
        bad['wege'][0]['nummer'] = '104'
        with self.assertRaisesRegex(ValueError, 'schon vergeben'):
            A.validate(bad)


class DialplanTests(unittest.TestCase):
    def setUp(self):
        self.out = G.gen_dialplan(model(), EXT, EPS)
        self.text = self.out['content']

    def test_weg_in_caller_context(self):
        outside, inside = G.split_managed(self.text)
        self.assertEqual(outside.strip(), EXT.strip(), 'eigene Einträge bleiben unverändert')
        self.assertIn('[tuer](+)', inside)
        self.assertIn('exten => 600,1,NoOp(Smartify: Rufgruppe Klingel Haustür)', inside)
        self.assertIn('${PJSIP_DIAL_CONTACTS(104)}', inside)
        self.assertIn('${PJSIP_DIAL_CONTACTS(105)}', inside)
        self.assertIn('&PJSIP/linphone-cloud/sip:beispielkonto@sip.linphone.org', inside)
        self.assertIn('Dial(${SM_DIAL:1},30)', inside)
        self.assertIn(' same => n(z2),', inside)

    def test_direct_dial_in_device_context(self):
        _, inside = G.split_managed(self.text)
        self.assertIn('[default](+)', inside)
        self.assertIn('exten => 907,1,NoOp(Smartify: Handy Büro)', inside)

    def test_conflict_not_overwritten(self):
        m = model()
        next(t for t in m['teilnehmer'] if t['name'] == 'Handy Büro')['nummer'] = '906'
        out = G.gen_dialplan(A.validate(m), EXT, EPS)
        self.assertNotIn('exten => 906', G.split_managed(out['content'])[1])
        self.assertTrue(any(r['level'] == 'warn' and r['text'].startswith('906') for r in out['aktionen']))

    def test_matching_manual_entry_is_info(self):
        m = model()
        h = next(t for t in m['teilnehmer'] if t['name'] == 'Handy')
        h['nummer'] = '906'
        out = G.gen_dialplan(A.validate(m), EXT, EPS)
        rows = [r for r in out['aktionen'] if r['bezug'] == '906']
        self.assertEqual([r['level'] for r in rows], ['info'])

    def test_call_from_linphone_lands_in_inbound_context(self):
        m = model()
        h = next(t for t in m['teilnehmer'] if t['name'] == 'Handy')
        h['eingang'] = 'linphone-in'
        m['wege'] = [{'name': 'Ruf vom Handy', 'nummer': '601', 'von': ['sip:beispielkonto@sip.linphone.org'], 'ziele': ['104'], 'klingelzeit': 20}]
        ext = EXT + '\n[linphone-in]\nexten => 104,1,Dial(PJSIP/104,30)\n'
        eps = dict(EPS, **{'linphone-in': {'context': 'linphone-in'}})
        inside = G.split_managed(G.gen_dialplan(A.validate(m), ext, eps)['content'])[1]
        self.assertIn('[linphone-in](+)', inside)
        self.assertIn('exten => 601,1,', inside)

    def test_legacy_trunk_rows_are_migrated(self):
        m = model()
        m['teilnehmer'].append({'nummer': '', 'typ': 'extern', 'name': 'linphone-cloud', 'endpoint': 'linphone-cloud',
                                'faehigkeiten': F(video_im_anruf=True)})
        next(t for t in m['teilnehmer'] if t['name'] == 'Handy Büro')['faehigkeiten']['video_im_anruf'] = False
        m['wege'][0]['von'] = ['110', 'linphone-cloud']
        v = A.validate(m)
        self.assertFalse(any(t['typ'] == 'extern' for t in v['teilnehmer']))
        self.assertEqual(v['wege'][0]['von'], ['110'])
        self.assertTrue(next(t for t in v['teilnehmer'] if t['name'] == 'Handy Büro')['faehigkeiten']['video_im_anruf'])

    def test_guess_eingang(self):
        eps = {'linphone-cloud': {'context': ''}, 'linphone-in': {'context': 'linphone-in'}, 'provider': {'context': 'from-provider'}, '104': {'context': 'default'}}
        self.assertEqual(A.guess_eingang(eps, 'linphone-cloud'), 'linphone-in')

    def test_darf_anrufen(self):
        m = model()
        h = next(t for t in m['teilnehmer'] if t['name'] == 'Handy')
        h.update(eingang='linphone-in', darf_anrufen=['104', '600', '105'])
        ext = EXT + '\n[linphone-in]\nexten => 105,1,Dial(PJSIP/105,30)\n'
        eps = dict(EPS, **{'linphone-in': {'context': 'linphone-in'}})
        out = G.gen_dialplan(A.validate(m), ext, eps)
        inside = G.split_managed(out['content'])[1]
        block = inside.split('[linphone-in](+)')[1]
        self.assertIn('exten => 104,1,', block)
        self.assertIn('exten => 600,1,', block)
        self.assertIn('&PJSIP/linphone-cloud/sip:beispielkonto@sip.linphone.org', block.split('exten => 600,1,')[1])
        self.assertNotIn('exten => 105,1,', block)
        self.assertEqual(G.gen_dialplan(A.validate(m), out['content'], eps)['content'], out['content'])

    def test_darf_anrufen_needs_eingang_and_valid_numbers(self):
        m = model()
        h = next(t for t in m['teilnehmer'] if t['name'] == 'Handy')
        h['darf_anrufen'] = ['104']
        with self.assertRaisesRegex(ValueError, 'Eingang'):
            A.validate(m)
        h.update(eingang='linphone-in', darf_anrufen=['999'])
        with self.assertRaisesRegex(ValueError, 'keine interne Nummer'):
            A.validate(m)

    def test_import_prefills_darf_anrufen(self):
        eps = {'104': {'context': 'default', 'codecs': []}, 'linphone-cloud': {'context': ''}, 'linphone-in': {'context': 'linphone-in'}}
        sip = {'users': [{'extension': '104', 'ha_username': 'ipad', 'display_name': 'iPad'}]}
        m = A.import_from(sip, eps, {}, extern_ziele=G.dialplan_extern_targets(EXT),
                          dialplan={'104': ['linphone-in', 'default'], '906': ['default']})
        h = next(t for t in m['teilnehmer'] if t['typ'] == 'extern_ziel')
        self.assertEqual((h['eingang'], h['darf_anrufen']), ('linphone-in', ['104']))

    def test_idempotent(self):
        self.assertEqual(G.gen_dialplan(model(), self.text, EPS)['content'], self.text)

    def test_no_route_number_no_dialplan(self):
        m = model()
        m['wege'][0]['nummer'] = ''
        out = G.gen_dialplan(A.validate(m), EXT, EPS)
        self.assertNotIn('600', out['content'])

    def test_import_targets(self):
        found = G.dialplan_extern_targets(EXT)
        self.assertEqual(found, [{'nummer': '906', 'endpoint': 'linphone-cloud', 'sip_adresse': 'beispielkonto@sip.linphone.org',
                                  'name': 'Test Linphone Push'}])

    def test_video_codec_patch_for_extern_ziel(self):
        custom = '[linphone-cloud]\ntype=endpoint\ndisallow=all\nallow=alaw,ulaw\n'
        out = G.gen_pjsip(model(), custom, [('custom/pjsip_custom.conf', custom)], {})
        self.assertIn('allow=alaw,ulaw,opus,vp8,h264', out['content'])


class LintTests(unittest.TestCase):
    def test_generated_dialplan_passes_lint(self):
        tmp = Path(tempfile.mkdtemp())
        os.environ['SMARTIFY_DATA_DIR'] = str(tmp / 'd')
        os.environ['ADDON_CONFIGS_ROOT'] = str(tmp / 'c')
        (tmp / 'c' / '3e533915_asterisk' / 'asterisk' / 'custom').mkdir(parents=True)
        spec = importlib.util.spec_from_file_location('app180', ROOT / 'app.py')
        app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app)
        text = G.gen_dialplan(model(), EXT, EPS)['content']
        result = app.lint_conf('extensions.conf', text)
        self.assertEqual(result['errors'], 0, result['issues'])


if __name__ == '__main__':
    unittest.main()


class RufgruppenImportTests(unittest.TestCase):
    EXT = ('[default]\nexten => _1XX,1,Dial(PJSIP/${EXTEN},30)\n'
           'exten => 600,1,NoOp(Gruppe EG)\n same => n,Dial(${PJSIP_DIAL_CONTACTS(104)}&${PJSIP_DIAL_CONTACTS(105)}&PJSIP/linphone-cloud/sip:neu@sip.linphone.org,25)\n same => n,Hangup()\n'
           'exten => 700,1,GotoIf($[1]?x)\n')

    def test_import_and_takeover(self):
        sip = {'users': [{'extension': '104', 'ha_username': 'a'}, {'extension': '105', 'ha_username': 'b'}]}
        eps = {'104': {'context': 'default'}, '105': {'context': 'default'}, 'linphone-cloud': {'context': ''}, 'linphone-in': {'context': 'linphone-in'}}
        m = A.import_from(sip, eps, {}, gruppen=G.dialplan_groups(self.EXT))
        w = m['wege'][0]
        self.assertEqual((w['nummer'], w['name'], w['klingelzeit'], w['kontexte'], w['ersetzen']), ('600', 'Gruppe EG', 25, ['default'], True))
        self.assertEqual(w['ziele'], ['104', '105', 'sip:neu@sip.linphone.org'])
        self.assertTrue(any(t['typ'] == 'extern_ziel' and t['sip_adresse'] == 'neu@sip.linphone.org' and t['eingang'] == 'linphone-in' for t in m['teilnehmer']))
        out = G.gen_dialplan(m, self.EXT, eps)
        outside, inside = G.split_managed(out['content'])
        self.assertNotIn('Gruppe EG)', outside)
        self.assertIn('exten => 700,1,GotoIf', outside, 'komplexe Einträge bleiben')
        self.assertIn('exten => 600,1,NoOp(Smartify: Rufgruppe Gruppe EG)', inside)
        self.assertIn('Dial(${SM_DIAL:1},25)', inside)
        self.assertEqual(G.gen_dialplan(m, out['content'], eps)['content'], out['content'])


class ErsetzenTests(unittest.TestCase):
    """1.13.3: eigener (auch komplexer) Eintrag wird nur mit „ersetzen“ übernommen."""
    EXT = ('[default]\nexten => _1XX,1,Dial(PJSIP/${EXTEN},30)\n'
           'exten => 600,1,NoOp(MaPa alt)\n same => n,Set(X=1)\n same => n,Dial(PJSIP/100&PJSIP/103,20)\n same => n,Hangup()\n'
           'exten => 601,1,NoOp(bleibt)\n same => n,Hangup()\n')

    def model(self, ersetzen):
        import anlage
        return anlage.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {},
                                'teilnehmer': [{'nummer': '100', 'typ': 'ha_geraet', 'name': 'iPhone', 'faehigkeiten': {}},
                                               {'nummer': '103', 'typ': 'ha_geraet', 'name': 'S10', 'faehigkeiten': {}}],
                                'wege': [{'name': 'MaPa anrufen', 'nummer': '600', 'von': ['100'], 'ziele': ['103'],
                                          'klingelzeit': 20, 'ersetzen': ersetzen}]})

    def test_conflict_offers_action(self):
        import generator
        r = generator.gen_dialplan(self.model(False), self.EXT, {})
        self.assertIn('NoOp(MaPa alt)', r['content'])
        self.assertTrue(any(a.get('aktion') == 'rufgruppe_ersetzen' for a in r['aktionen']), r['aktionen'])

    def test_replace(self):
        import generator
        r = generator.gen_dialplan(self.model(True), self.EXT, {})
        self.assertNotIn('MaPa alt', r['content'])
        self.assertNotIn('Set(X=1)', r['content'])
        self.assertIn('NoOp(bleibt)', r['content'])
        self.assertIn('exten => 600,1,NoOp(Smartify: Rufgruppe MaPa anrufen)', r['content'])
        self.assertIn('_1XX', r['content'])
        again = generator.gen_dialplan(self.model(True), r['content'], {})
        self.assertEqual(again['content'], r['content'])


class AnruferPruefungTests(unittest.TestCase):
    """1.13.4: nur die Anrufer der Gruppe dürfen die Nummer wählen."""

    def model(self, von):
        import anlage
        return anlage.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {},
            'teilnehmer': [{'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': {}},
                           {'nummer': '105', 'typ': 'ha_geraet', 'name': 'PC', 'faehigkeiten': {}},
                           {'nummer': '906', 'typ': 'extern_ziel', 'name': 'LP Raphael', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'beispielkonto@sip.linphone.org', 'faehigkeiten': {}, 'darf_anrufen': ['600']},
                           {'nummer': '907', 'typ': 'extern_ziel', 'name': 'LP Beate', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'test-benutzer-b@sip.linphone.org', 'faehigkeiten': {}}],
            'wege': [{'name': 'MaPa', 'nummer': '600', 'von': von, 'ziele': ['906', '907'], 'klingelzeit': 20}]})

    EPS = {'linphone-in': {'context': 'linphone-in'}, 'linphone-cloud': {'context': 'default'}}

    def test_only_listed_callers(self):
        import generator
        c = generator.gen_dialplan(self.model(['104']), '[default]\n', self.EPS)['content']
        block = c[c.index('exten => 600,1'):]
        self.assertIn('Set(SM_EP=${CHANNEL(endpoint)})', block)
        self.assertIn('GotoIf($["${SM_EP}" = "104"]?erlaubt)', block)
        self.assertNotIn('"105"', block)
        self.assertIn('Hangup(21)', block)
        self.assertIn('same => n(erlaubt),Set(SM_DIAL=)', block)
        # Freigabe für 906 im Eingang: nur dieses Linphone-Konto
        lin = c[c.index('[linphone-in]'):]
        self.assertIn('GotoIf($["${SM_EP}" = "linphone-in" & "${CALLERID(num)}" = "beispielkonto"]?erlaubt)', lin)

    def test_empty_means_everyone(self):
        import generator
        c = generator.gen_dialplan(self.model([]), '[default]\n', self.EPS)['content']
        block = c[c.index('exten => 600,1'):c.index('Hangup()', c.index('exten => 600,1'))]
        self.assertNotIn('SM_EP', block)


class EingangTests(unittest.TestCase):
    """1.14.0: Eingänge mit Quell-IPs im Modell, Freigaben aus dem alten Werkzeug übernehmen."""
    PJ = ('[linphone-cloud]\ntype=endpoint\ncontext=default\nallow=ulaw\n\n'
          '[linphone-in]\ntype=endpoint\ncontext=linphone-in\ntransport=transport-udp\nallow=ulaw\n\n'
          '[linphone-in-identify]\ntype=identify\nendpoint=linphone-in\nmatch=100.64.10.20/32\n')
    EXT = ('[default]\nexten => _1XX,1,Dial(PJSIP/${EXTEN},30)\n\n[linphone-in]\n; Freigaben\n'
           'exten => 104,1,NoOp(Externer Eingang 104)\n same => n,Dial(${PJSIP_DIAL_CONTACTS(104)},30)\n same => n,Hangup()\n')

    def model(self, uebernommen, darf=('104',), ips=('100.64.10.20/32',)):
        return A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {}, 'wege': [],
            'eingaenge': [{'name': 'linphone-in', 'quell_ips': list(ips), 'uebernommen': uebernommen}],
            'teilnehmer': [{'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': {}},
                           {'nummer': '906', 'typ': 'extern_ziel', 'name': 'LP Raphael', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'beispielkonto@sip.linphone.org', 'faehigkeiten': {}, 'darf_anrufen': list(darf)}]})

    def test_import(self):
        eps = A.endpoints_from_conf([('custom/pjsip_custom.conf', self.PJ)])
        m = A.import_from({}, eps, {}, dialplan=G.dialplan_numbers(self.EXT))
        self.assertEqual(m['eingaenge'], [{'name': 'linphone-in', 'quell_ips': ['100.64.10.20/32'], 'uebernommen': False, 'freigaben': ['104']}])

    def test_takeover_dialplan(self):
        eps = A.endpoints_from_conf([('custom/pjsip_custom.conf', self.PJ)])
        before = G.gen_dialplan(self.model(False, darf=()), self.EXT, eps)    # nicht angehakt: eigener Eintrag bleibt
        self.assertIn('NoOp(Externer Eingang 104)', before['content'])
        self.assertTrue(any('bleibt' in a['text'] for a in before['aktionen']))
        after = G.gen_dialplan(self.model(True), self.EXT, eps)
        c = after['content']
        self.assertNotIn('Externer Eingang 104', c)
        lin = c[c.index('[linphone-in](+)'):]
        self.assertIn('exten => 104,1,', lin)
        self.assertIn('GotoIf($["${SM_EP}" = "linphone-in"]?erlaubt)', lin)   # allein am Eingang: kein Konto-Vergleich
        self.assertEqual(G.gen_dialplan(self.model(True), c, eps)['content'], c)

    def test_pjsip_ips(self):
        files = [('custom/pjsip_custom.conf', self.PJ)]
        r = G.gen_pjsip(self.model(True, ips=('100.64.10.20/32', '100.64.1.2/32')), self.PJ, files, {'sip': {}})
        self.assertIn('match=100.64.10.20/32,100.64.1.2/32', r['content'])
        self.assertEqual(r['content'].count('type=identify'), 1)
        new = A.validate(dict(self.model(True), eingaenge=[{'name': 'tailscale-in', 'quell_ips': ['100.64.9.9']}]))
        r2 = G.gen_pjsip(new, self.PJ, files, {'sip': {}})
        self.assertIn('[tailscale-in]\ntype=endpoint\ncontext=tailscale-in', r2['content'])
        self.assertIn('match=100.64.9.9/32', r2['content'])

    def test_reject_ranges(self):
        with self.assertRaisesRegex(ValueError, 'Netzbereiche'):
            self.model(True, ips=('100.64.0.0/10',))


class WegfallTests(unittest.TestCase):
    def test_warns_when_number_leaves_context(self):
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {},
            'teilnehmer': [{'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': {}},
                           {'nummer': '105', 'typ': 'ha_geraet', 'name': 'PC', 'faehigkeiten': {}}],
            'wege': [{'name': 'MaPa', 'nummer': '600', 'von': ['104'], 'ziele': ['105'], 'klingelzeit': 20}]})
        old = ('[default]\n\n' + G.BEGIN + '\n[linphone-in]\nexten => 600,1,NoOp(alt)\n same => n,Hangup()\n; <<< SMARTIFY-VERWALTET\n')
        r = G.gen_dialplan(m, old, {})
        self.assertTrue(any('„linphone-in“ NICHT mehr erreichbar' in a['text'] for a in r['aktionen']), r['aktionen'])


class MitgliederTests(unittest.TestCase):
    """1.15.0: Mitglieder dürfen die Gruppe anrufen, der Anrufer wird übersprungen."""
    EPS = {'linphone-in': {'context': 'linphone-in'}, 'linphone-cloud': {'context': 'default'}}

    def model(self, flag=True, von=('110',)):
        return A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {},
            'teilnehmer': [{'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': {}},
                           {'nummer': '110', 'typ': 'tuerstation', 'name': 'Tür', 'faehigkeiten': {}},
                           {'nummer': '906', 'typ': 'extern_ziel', 'name': 'Raphael', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'beispielkonto@sip.linphone.org', 'faehigkeiten': {}},
                           {'nummer': '907', 'typ': 'extern_ziel', 'name': 'Beate', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'test-benutzer-b@sip.linphone.org', 'faehigkeiten': {}}],
            'wege': [{'name': 'MaPa', 'nummer': '600', 'von': list(von), 'ziele': ['104', '906', '907'], 'klingelzeit': 20,
                      'mitglieder_rufen': flag}]})

    def test_members_allowed_and_skipped(self):
        c = G.gen_dialplan(self.model(), '[default]\n', self.EPS)['content']
        self.assertIn('[linphone-in]', c)                       # Cloud-Mitglieder erreichen 600 über ihren Eingang
        block = c[c.index('[default]', 1):]
        for cond in ('"${SM_EP}" = "110"', '"${SM_EP}" = "104"',
                     '"${SM_EP}" = "linphone-in" & "${CALLERID(num)}" = "test-benutzer-b"'):
            self.assertIn(f'GotoIf($[{cond}]?erlaubt)', block)
        # 104 wird übersprungen, wenn 104 anruft; Beate, wenn Beate anruft
        self.assertRegex(block, r'GotoIf\(\$\["\$\{SM_EP\}" = "104"\]\?z1\)\n same => n,Set\(SM_C=\$\{PJSIP_DIAL_CONTACTS\(104\)\}\)')
        self.assertIn('GotoIf($["${SM_EP}" = "linphone-in" & "${CALLERID(num)}" = "test-benutzer-b"]?z3)\n same => n,Set(SM_DIAL=${SM_DIAL}&PJSIP/linphone-cloud/sip:test-benutzer-b@sip.linphone.org)', block)
        self.assertIn('same => n(z3),GotoIf($["${SM_DIAL}" = ""]?leer)', block)

    def test_off_keeps_old_behaviour(self):
        c = G.gen_dialplan(self.model(False), '[default]\n', self.EPS)['content']
        self.assertNotIn('[linphone-in]', c)
        self.assertNotIn('GotoIf($["${SM_EP}" = "104"]', c)


class KontextUndIpTests(unittest.TestCase):
    """1.16.0: jeder Kontext prüft nur seine Anrufer; Cloud-Handys am Eingang über ihre IP erkannt."""
    EPS = {'linphone-in': {'context': 'linphone-in'}, 'linphone-cloud': {'context': 'default'}}

    def test_per_context_and_ip(self):
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {},
            'teilnehmer': [{'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': {}},
                           {'nummer': '906', 'typ': 'extern_ziel', 'name': 'Raphael', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'beispielkonto@sip.linphone.org', 'faehigkeiten': {}, 'quell_ips': '100.64.10.20'},
                           {'nummer': '907', 'typ': 'extern_ziel', 'name': 'Beate', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'test-benutzer-b@sip.linphone.org', 'faehigkeiten': {}, 'quell_ips': ['100.64.1.2']}],
            'wege': [{'name': 'MaPa', 'nummer': '600', 'von': ['104'], 'ziele': ['906', '907'], 'klingelzeit': 20, 'mitglieder_rufen': True}]})
        c = G.gen_dialplan(m, '[default]\n', self.EPS)['content']
        d = c[c.index('[default](+)'):c.index('\n[linphone-in]')]
        lin = c[c.index('\n[linphone-in]'):]
        self.assertIn('GotoIf($["${SM_EP}" = "104"]?erlaubt)', d)
        self.assertNotIn('linphone-in', d.split('Set(SM_DIAL=)')[0])
        self.assertNotIn('SM_IP', d)
        self.assertNotIn('"104"', lin)
        self.assertIn('Set(SM_IP=${CHANNEL(pjsip,remote_addr)})', lin)
        self.assertIn('GotoIf($["${SM_EP}" = "linphone-in" & "${SM_IP}" = "100.64.10.20"]?erlaubt)', lin)
        self.assertIn('GotoIf($["${SM_EP}" = "linphone-in" & "${SM_IP}" = "100.64.1.2"]?z2)', lin)
        # identify bekommt beide IPs
        r = G.gen_pjsip(m, '[linphone-in]\ntype=endpoint\ncontext=linphone-in\nallow=alaw,ulaw\n', [('custom/pjsip_custom.conf', '')], {'sip': {}})
        self.assertIn('match=100.64.10.20/32,100.64.1.2/32', r['content'])
        self.assertIn('allow=alaw,ulaw,opus', r['content'])


class IdentifyEntfernenTests(unittest.TestCase):
    def test_no_ip_removes_identify(self):
        pj = ('[linphone-in]\ntype=endpoint\ncontext=linphone-in\nallow=ulaw\n\n'
              '[linphone-in-identify]\ntype=identify\nendpoint=linphone-in\nmatch=100.64.10.40/32\n')
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {}, 'wege': [],
            'eingaenge': [{'name': 'linphone-in', 'quell_ips': []}],
            'teilnehmer': [{'nummer': '906', 'typ': 'extern_ziel', 'name': 'Android', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {}}]})
        r = G.gen_pjsip(m, pj, [('custom/pjsip_custom.conf', pj)], {'sip': {}})
        self.assertNotIn('100.64.10.40', r['content'])
        self.assertIn('[linphone-in]', r['content'])
        self.assertTrue(any('identify) wird entfernt' in a['text'] for a in r['aktionen']))


class RealmTests(unittest.TestCase):
    def model(self, realm=''):
        return A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {}, 'wege': [],
            'teilnehmer': [{'nummer': '130', 'typ': 'sip_telefon', 'name': 'Android', 'faehigkeiten': {}, 'realm': realm}]})

    def test_realm_written_and_kept(self):
        r = G.gen_pjsip(self.model('100.64.10.10'), '', [], {'sip': {}})
        self.assertIn('username=130\npassword=', r['content'])
        self.assertIn('realm=100.64.10.10', r['content'])
        # von Hand eingetragener realm bleibt erhalten, auch wenn das Modell-Feld leer ist
        again = G.gen_pjsip(self.model(''), r['content'], [], {'sip': {}})
        self.assertIn('realm=100.64.10.10', again['content'])

    def test_no_realm_by_default(self):
        self.assertNotIn('realm=', G.gen_pjsip(self.model(), '', [], {'sip': {}})['content'])


class GleichesGeraetTests(unittest.TestCase):
    """1.16.4: SIP-Konto 130 gehört zum Cloud-Teilnehmer 906 – ruft 130 die Gruppe, klingelt 906 nicht."""
    def model(self, mitglieder):
        return A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {},
            'teilnehmer': [{'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': {}},
                           {'nummer': '130', 'typ': 'sip_telefon', 'name': 'Android Tailscale', 'faehigkeiten': {}, 'gleiches_geraet': '906'},
                           {'nummer': '906', 'typ': 'extern_ziel', 'name': 'Android', 'endpoint': 'linphone-cloud',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {}}],
            'wege': [{'name': 'MaPa', 'nummer': '600', 'von': ['104'] if mitglieder else ['104', '130'], 'ziele': ['104', '906'],
                      'klingelzeit': 20, 'mitglieder_rufen': mitglieder}]})

    def test_member_alias(self):
        c = G.gen_dialplan(self.model(True), '[default]\n', {})['content']
        self.assertIn('GotoIf($["${SM_EP}" = "130"]?erlaubt)', c)          # 130 darf als Teil des Mitglieds 906 anrufen
        self.assertIn('GotoIf($["${SM_EP}" = "130"]?z2)\n same => n,Set(SM_DIAL=${SM_DIAL}&PJSIP/linphone-cloud/sip:r@sip.linphone.org)', c)
        self.assertEqual(A.validate(self.model(True))['teilnehmer'][1]['gleiches_geraet'], '906')

    def test_caller_alias_without_member_flag(self):
        c = G.gen_dialplan(self.model(False), '[default]\n', {})['content']
        self.assertIn('GotoIf($["${SM_EP}" = "130"]?z2)', c)

    def test_unknown_reference_dropped(self):
        m = self.model(True)
        m['teilnehmer'][1]['gleiches_geraet'] = 'sip:gibtsnicht@x.org'
        self.assertEqual([t for t in A.validate(m)['teilnehmer'] if t['nummer'] == '130'][0]['gleiches_geraet'], '')


class RealmAutoTests(unittest.TestCase):
    def test_auto_realm(self):
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'wege': [],
            'anlage': {'lan_ip': '192.168.2.65', 'tailscale_ip': '100.64.10.10'},
            'teilnehmer': [{'nummer': '130', 'typ': 'sip_telefon', 'name': 'Android', 'faehigkeiten': {}, 'gleiches_geraet': '906'},
                           {'nummer': '120', 'typ': 'sip_telefon', 'name': 'Büro', 'faehigkeiten': {}},
                           {'nummer': '906', 'typ': 'extern_ziel', 'name': 'Handy', 'endpoint': 'linphone-cloud',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {}}]})
        c = G.gen_pjsip(m, '', [], {'sip': {}})['content']
        a130 = c[c.index('[130]\ntype=auth'):c.index('[130]\ntype=endpoint')]
        a120 = c[c.index('[120]\ntype=auth'):c.index('[120]\ntype=endpoint')]
        self.assertIn('realm=100.64.10.10', a130)
        self.assertIn('realm=192.168.2.65', a120)

    def test_bad_tailscale_ip(self):
        with self.assertRaisesRegex(ValueError, 'Tailscale-IP'):
            A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {'tailscale_ip': '192.168.1.5'}, 'teilnehmer': [], 'wege': []})


class EingangDoppeltTests(unittest.TestCase):
    def test_tn_ip_not_repeated_in_eingang(self):
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {}, 'wege': [],
            'eingaenge': [{'name': 'linphone-in', 'quell_ips': ['100.64.10.20', '100.64.9.9']}],
            'teilnehmer': [{'nummer': '906', 'typ': 'extern_ziel', 'name': 'R', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {}, 'quell_ips': '100.64.10.20'}]})
        self.assertEqual(m['eingaenge'][0]['quell_ips'], ['100.64.9.9/32'])


class AvpfTests(unittest.TestCase):
    def test_use_received_transport(self):
        pj = '[linphone-in]\ntype=endpoint\ncontext=linphone-in\nallow=opus,ulaw,alaw\n'
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {}, 'wege': [],
            'teilnehmer': [{'nummer': '906', 'typ': 'extern_ziel', 'name': 'R', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {}}]})
        c = G.gen_pjsip(m, pj, [('custom/pjsip_custom.conf', pj)], {'sip': {}})['content']
        self.assertIn('allow=opus,ulaw,alaw\nmedia_use_received_transport=yes\nmedia_encryption=sdes\nmedia_encryption_optimistic=yes', c)
        self.assertEqual(G.gen_pjsip(m, c, [('custom/pjsip_custom.conf', c)], {'sip': {}})['content'], c)


class AvpfRepairTests(unittest.TestCase):
    def test_repairs_invalid_option(self):
        pj = '[linphone-in]\ntype=endpoint\ncontext=linphone-in\nallow=opus,ulaw,alaw\nuse_received_transport=yes\n'
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {}, 'wege': [],
            'teilnehmer': [{'nummer': '906', 'typ': 'extern_ziel', 'name': 'R', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {}}]})
        c = G.gen_pjsip(m, pj, [('custom/pjsip_custom.conf', pj)], {'sip': {}})['content']
        self.assertIn('\nmedia_use_received_transport=yes', c)
        self.assertNotIn('\nuse_received_transport', c)
        self.assertEqual(c.count('use_received_transport'), 1)


class SrtpTests(unittest.TestCase):
    def test_sdes_only_on_eingang(self):
        pj = ('[linphone-cloud]\ntype=endpoint\nallow=opus,ulaw,alaw\nmedia_use_received_transport=yes\n\n'
              '[linphone-in]\ntype=endpoint\ncontext=linphone-in\nallow=opus,ulaw,alaw\nmedia_use_received_transport=yes\n')
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {}, 'wege': [],
            'teilnehmer': [{'nummer': '906', 'typ': 'extern_ziel', 'name': 'R', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {}}]})
        c = G.gen_pjsip(m, pj, [('custom/pjsip_custom.conf', pj)], {'sip': {}})['content']
        cloud = c[c.index('[linphone-cloud]'):c.index('[linphone-in]')]
        lin = c[c.index('[linphone-in]'):]
        self.assertNotIn('media_encryption', cloud)
        self.assertIn('media_encryption=sdes\nmedia_encryption_optimistic=yes', lin)
