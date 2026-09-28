import unittest
from engine import Engine,validate
class RiskTests(unittest.TestCase):
 def sample(self,**kw):return dict(device_id='a',timestamp=0,voltage=230,current=50,temperature=30,soc=80,converter_temperature=45,**kw)
 def test_normal(self):self.assertEqual(Engine().assess(self.sample())['score'],0)
 def test_critical_override(self):
  r=self.sample();r['temperature']=55
  self.assertEqual(Engine().assess(r)['level'],'Critical')
 def test_missing_coverage(self):
  r=self.sample();r['temperature']=None;r['soc']=None
  result=Engine().assess(r);self.assertIsNone(result['score']);self.assertEqual(result['coverage'],60)
 def test_persistence_and_recovery(self):
  e=Engine();r=self.sample();r['temperature']=50
  self.assertEqual(e.assess(r)['level'],'Normal');r['timestamp']=6
  self.assertEqual(e.assess(r)['level'],'Warning');r['temperature']=44.9;r['timestamp']=7
  self.assertEqual(e.assess(r)['level'],'Warning');r['temperature']=44;r['timestamp']=8
  self.assertEqual(e.assess(r)['level'],'Normal')
 def test_boundary(self):
  r=self.sample();r['temperature']=45
  self.assertEqual(Engine().assess(r)['score'],0)
 def test_unconfigured(self):self.assertIsNone(Engine([]).assess(self.sample())['score'])
 def test_invalid_unit(self):
  r=self.sample();r.update(component_id='bus',source='live',quality='good',units={})
  with self.assertRaises(ValueError):validate(r)
if __name__=='__main__':unittest.main()
