import unittest
from unittest.mock import Mock,patch
import server
class DisconnectTests(unittest.TestCase):
 def test_windows_stream_abort(self):
  h=object.__new__(server.Handler);h.path='/api/events?mode=dataset'
  h.send_response=Mock();h.send_header=Mock();h.end_headers=Mock()
  h.wfile=Mock();h.wfile.write.side_effect=ConnectionAbortedError(10053,'Client disconnected')
  with patch.object(server,'snapshot',return_value={'history':[]}):h.do_GET()
  h.wfile.write.assert_called_once()
 def test_regular_response_abort(self):
  h=object.__new__(server.Handler)
  with patch.object(server.SimpleHTTPRequestHandler,'handle',side_effect=ConnectionAbortedError(10053,'Client disconnected')):h.handle()
  self.assertTrue(h.close_connection)
