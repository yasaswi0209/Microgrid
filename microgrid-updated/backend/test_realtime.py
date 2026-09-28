import unittest,time
import server
from engine import Engine,validate
class RealtimeTests(unittest.TestCase):
 def test_warning_timer_resets_on_gap(self):
  e=Engine([['temperature','Battery','C',None,None,45,55,1,'Inspect']]);r={'device_id':'a','timestamp':0,'temperature':50};e.assess(r);r['timestamp']=20
  self.assertEqual(e.assess(r)['factors'][0]['status'],'Pending')
 def test_nonfinite_limits_rejected(self):
  with self.assertRaises(ValueError):Engine([['temperature','Battery','C',None,None,45,float('inf'),1,'Inspect']])
 def test_live_old_reading_rejected(self):
  with self.assertRaisesRegex(ValueError,'older than'):
   server.ingest({'device_id':'clock-test','component_id':'bus','timestamp':time.time()-40,'source':'live','quality':'good','units':{}})
 def test_negative_generation_rejected(self):
  with self.assertRaises(ValueError):validate({'device_id':'x','component_id':'bus','timestamp':time.time(),'source':'live','quality':'good','units':{'solar':'kW'},'solar':-1})
 def test_dataset_cache_reused(self):
  self.assertIs(server.dataset_files()[0],server.dataset_files()[0])
 def test_revision_changes(self):
  before=server.REVISION;server.signal_change();self.assertEqual(server.REVISION,before+1)
if __name__=='__main__':unittest.main()
