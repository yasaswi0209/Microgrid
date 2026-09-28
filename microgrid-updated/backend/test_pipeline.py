import unittest,tempfile,time,json,sqlite3
from pathlib import Path
import server
class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=server.DB;server.DB=Path(self.tmp.name)/'test.sqlite3';server.ENGINES.clear()
  with server.connect() as c:c.executescript('CREATE TABLE readings(id INTEGER PRIMARY KEY, device TEXT, source TEXT, ts REAL, data TEXT, UNIQUE(device,source,ts)); CREATE TABLE alerts(id INTEGER PRIMARY KEY, device TEXT, source TEXT, factor TEXT, status TEXT, opened REAL, updated REAL, data TEXT);')
 def tearDown(self):server.DB=self.old;self.tmp.cleanup()
 def sample(self,t):
  r=json.loads((Path(__file__).parent/'example-payload.json').read_text());r.update(timestamp=t,source='simulation');return r
 def test_energy_and_duplicates(self):
  t=time.time()-20;r=self.sample(t);a=server.ingest(r);b=server.ingest(self.sample(t+10))
  self.assertAlmostEqual(b['energy_kwh'],.45*10/3600);self.assertAlmostEqual(b['balance_residual'],0)
  with self.assertRaises(ValueError):server.ingest(self.sample(t+10))
  with self.assertRaises(ValueError):server.ingest(self.sample(t+5))
 def test_alert_dedup_recovery(self):
  t=time.time()-20
  for i in range(2):
   r=self.sample(t+i);r['temperature']=60;server.ingest(r)
  a=server.snapshot('simulation')['alerts'];self.assertEqual(len(a),1)
  server.ingest(self.sample(t+3));self.assertEqual(server.snapshot('simulation')['alerts'][0]['status'],'resolved')
 def test_invalid_suppresses_risk(self):
  r=self.sample(time.time());r['quality']='invalid';a=server.ingest(r);self.assertIsNone(a['risk']['score']);self.assertEqual(a['predictions'],[])
 def test_live_limits_absent(self):
  r=self.sample(time.time());r['source']='live';a=server.ingest(r);self.assertIsNone(a['risk']['score'])
if __name__=='__main__':unittest.main()
