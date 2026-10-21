"""Regression: Cloud-Push darf Gruppe 601 nutzen, nicht aber Direktwahl 906 via Asterisk."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'smartify_sip_manager'))
import anlage, generator, verbindungen

class CloudGroupAndDirectTests(unittest.TestCase):
    def test_cloud_group_independent_of_direct_extension(self):
        m = anlage.leer()
        m['teilnehmer'] = [
            {'nummer':'100','name':'iPhone','typ':'ha_geraet'},
            {'nummer':'906','name':'Raphael Push','typ':'extern_ziel','endpoint':'linphone-cloud','eingang':'linphone-in','sip_adresse':'raphael@sip.linphone.org','darf_anrufen':['601'],'angerufen_von':[]},
            {'nummer':'907','name':'Lisi Push','typ':'extern_ziel','endpoint':'linphone-cloud','eingang':'linphone-in','sip_adresse':'lisi@sip.linphone.org','darf_anrufen':['601'],'angerufen_von':[]},
        ]
        m['wege']=[{'nummer':'601','name':'Smartify','von':['906','907'],'ziele':['906','907'],'klingelzeit':30}]
        m=anlage.validate(m)
        eps={'100':{'context':'default'},'linphone-in':{'context':'linphone-in'}}
        out=generator.gen_dialplan(m,'',eps)['content']
        self.assertIn('exten => 601,1,',out)
        self.assertIn('sip:raphael@sip.linphone.org',out)
        self.assertIn('sip:lisi@sip.linphone.org',out)
        self.assertIn('exten => 906,1,',out)
        self.assertIn('exten => 907,1,',out)
        self.assertIn('1 = 0',out)  # Asterisk-Direktwahl: niemand
        g=verbindungen.graph(m,eps,out)
        pairs={(e['von'],e['nach'],e['art']) for e in g['kanten']}
        self.assertIn(('tn:907','weg:601','cloud_ein'),pairs)
        self.assertIn(('weg:601','tn:906','weg'),pairs)
        self.assertNotIn(('tn:100','tn:906','cloud_aus'),pairs)
        self.assertNotIn(('tn:100','tn:907','cloud_aus'),pairs)
        self.assertIn(('tn:906','tn:907','cloud_direkt'),pairs)
        self.assertEqual(sum(1 for e in g['kanten'] if e['von']=='tn:907' and e['nach']=='weg:601'),1)

if __name__=='__main__':
    unittest.main()
