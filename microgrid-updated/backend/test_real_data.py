import json,math,unittest
from pathlib import Path
class RealDataTests(unittest.TestCase):
 def setUp(self):
  d=Path(__file__).parent/'data';self.report=json.loads((d/'evaluation.json').read_text());self.rows=json.loads((d/'holdout.json').read_text())
 def test_forecast_issue_precedes_target(self):
  self.assertTrue(all(r['timestamp']-r['issued_at']==3600 for r in self.rows))
 def test_split_has_no_boundary_overlap(self):
  m=self.report;self.assertLess(m['train_end'],m['validation_start']);self.assertLess(m['validation_end'],m['test_start'])
 def test_metrics_match_delivered_predictions(self):
  for key in ['solar','load']:
   errs=[r[key+'_prediction']-r[key] for r in self.rows]
   self.assertAlmostEqual(sum(abs(v) for v in errs)/len(errs),self.report['targets'][key]['test_mae'],places=5)
   self.assertAlmostEqual(math.sqrt(sum(v*v for v in errs)/len(errs)),self.report['targets'][key]['test_rmse'],places=5)
 def test_no_invented_equipment_readings(self):
  self.assertTrue(all(not any(k in r for k in ['soc','temperature','irradiance','efficiency']) for r in self.rows))
if __name__=='__main__':unittest.main()
