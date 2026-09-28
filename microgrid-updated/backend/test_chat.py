import unittest
from dataset_chat import answer
class ChatTests(unittest.TestCase):
 def setUp(self):
  self.rows=[dict(timestamp=3600,issued_at=0,solar=1,load=2,grid=1,solar_prediction=.8,load_prediction=1.9),dict(timestamp=7200,issued_at=3600,solar=99,load=100,grid=1,solar_prediction=1.2,load_prediction=2.1)]
 def test_forecast_uses_estimate_not_future_actual(self):
  text=answer('next hour forecast',self.rows,{},0)['answer'];self.assertIn('1.200',text);self.assertNotIn('99',text)
 def test_summary_excludes_future_rows(self):self.assertIn('solar 1.000 kWh',answer('energy summary',self.rows,{},0)['answer'])
 def test_no_sensor_invention(self):self.assertIn('does not contain',answer('battery SOC',self.rows,{},0)['answer'])
 def test_bad_position(self):
  with self.assertRaises(ValueError):answer('forecast',self.rows,{},100)
 def test_missing_future_not_invented(self):self.assertIn('No saved',answer('forecast',self.rows,{},1)['answer'])
