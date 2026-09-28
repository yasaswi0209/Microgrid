import unittest,json,math
from pathlib import Path
from dataset_chat import answer
from question_bank import catalog
class QuestionBankTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  data=Path(__file__).parent/'data';cls.rows=json.loads((data/'holdout.json').read_text());cls.report=json.loads((data/'evaluation.json').read_text())
 def test_all_100_questions_resolve_without_placeholders(self):
  self.assertEqual(len(catalog()),100)
  self.assertEqual(len({v['question'] for v in catalog()}),100)
  for entry in catalog():
   with self.subTest(id=entry['id']):
    response=answer(entry['question'],self.rows,self.report,71)
    self.assertEqual(response['question_id'],entry['id']);self.assertNotIn('{',response['answer']);self.assertGreater(len(response['answer']),20)
 def test_all_100_ids_resolve(self):
  for entry in catalog():self.assertEqual(answer('Q'+str(entry['id']),self.rows,self.report,0)['question_id'],entry['id'])
 def test_last_record_forecast_is_unavailable(self):self.assertIn('No saved',answer('Q31',self.rows,self.report,len(self.rows)-1)['answer'])
 def test_interval_bounds_and_reported_coverage(self):
  for key in ('solar','load'):
   coverage=sum(r[key+'_lower']<=r[key]<=r[key+'_upper'] for r in self.rows)/len(self.rows)
   self.assertAlmostEqual(coverage,self.report['targets'][key]['interval_test_coverage'],places=5)
   self.assertTrue(all(0<=r[key+'_lower']<=r[key+'_prediction']<=r[key+'_upper'] for r in self.rows))
 def test_winner_uses_validation_scores(self):
  for values in self.report['targets'].values():self.assertEqual(values['selected_model'],min(values['validation_mae_candidates'],key=values['validation_mae_candidates'].get))
