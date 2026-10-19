"""Offline unit tests for the /us-picks scripts — no API keys, no network.

Run:  python3 -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
import uspicks_data as ud          # noqa: E402
import uspicks_trade_sim as sim    # noqa: E402
import uspicks_controls as ctrl    # noqa: E402
import uspicks_premarket_check as pm  # noqa: E402


def ms(y, mo, d, h, mi):
    """Epoch milliseconds for a UTC wall-clock time."""
    return int(datetime(y, mo, d, h, mi, tzinfo=timezone.utc).timestamp() * 1000)


class TimeHelpers(unittest.TestCase):
    def test_ts_unit_detection(self):
        base = ms(2026, 7, 15, 13, 30)
        self.assertEqual(ud._ts_to_ms(base), base)
        self.assertEqual(ud._ts_to_ms(base * 1000), base)          # microseconds
        self.assertEqual(ud._ts_to_ms(base * 1000000), base)       # nanoseconds
        self.assertEqual(ud._ts_to_ms(base // 1000), base // 1000 * 1000)  # seconds

    def test_open_is_0930_in_summer_and_winter(self):
        self.assertEqual(ud._et_minutes(ms(2026, 7, 15, 13, 30)), 570)   # EDT, UTC-4
        self.assertEqual(ud._et_minutes(ms(2026, 1, 15, 14, 30)), 570)   # EST, UTC-5

    def test_regular_session_window_is_dst_aware(self):
        # 09:00 EST is pre-market; the old fixed UTC-4 formula read it as 10:00.
        self.assertFalse(ud.in_regular_session(ms(2026, 1, 15, 14, 0)))
        self.assertTrue(ud.in_regular_session(ms(2026, 1, 15, 14, 30)))
        self.assertTrue(ud.in_regular_session(ms(2026, 1, 15, 20, 59)))   # 15:59 EST
        self.assertFalse(ud.in_regular_session(ms(2026, 1, 15, 21, 0)))   # 16:00 EST
        self.assertTrue(ud.in_regular_session(ms(2026, 7, 15, 19, 59)))   # 15:59 EDT
        self.assertFalse(ud.in_regular_session(ms(2026, 7, 15, 20, 0)))


class _Resp:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class PolygonRequests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'POLYGON_API_KEY': 'TESTKEY'})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_key_goes_in_header_not_url(self):
        seen = []

        def fake_urlopen(req, timeout=None):
            seen.append(req)
            return _Resp({'results': []})

        with mock.patch.object(ud.urllib.request, 'urlopen', fake_urlopen):
            ud._pget('/v3/reference/splits', {'execution_date.gt': '2026-01-05', 'tickers': 'A,B'})
        req = seen[0]
        self.assertNotIn('TESTKEY', req.full_url)
        self.assertNotIn('apiKey', req.full_url)
        self.assertEqual(req.get_header('Authorization'), 'Bearer TESTKEY')
        self.assertIn('execution_date.gt=2026-01-05', req.full_url)
        self.assertIn('tickers=A,B', req.full_url)

    def test_splits_follow_next_url_verbatim(self):
        calls = []
        pages = [
            {'results': [{'ticker': 'X', 'split_from': 1, 'split_to': 2}],
             'next_url': ud.POLY + '/v3/reference/splits?cursor=abc%3D%3D'},
            {'results': [{'ticker': 'Y', 'split_from': 10, 'split_to': 1}]},
        ]

        def fake_pget(path, params=None, retries=4):
            calls.append((path, params))
            return pages[len(calls) - 1]

        with mock.patch.object(ud, '_pget', fake_pget):
            out = ud.splits_in_range('2026-01-05', '2026-01-09')
        self.assertEqual(out, {'X': 0.5, 'Y': 10.0})
        # the encoded cursor is passed through untouched (no double encoding)
        self.assertEqual(calls[1], (ud.POLY + '/v3/reference/splits?cursor=abc%3D%3D', None))

    def test_options_chain_refuses_off_host_next_url(self):
        first = {'results': [{'a': 1}], 'next_url': 'https://evil.example/steal'}
        with mock.patch.object(ud, '_pget', return_value=first) as p:
            out = ud.options_chain('AAPL')
        self.assertEqual(out, [{'a': 1}])
        self.assertEqual(p.call_count, 1)


class FlatFileDownload(unittest.TestCase):
    def test_interrupted_download_leaves_no_cached_file(self):
        with tempfile.TemporaryDirectory() as d:
            class FakeS3:
                def download_file(self, bucket, key, path):
                    with open(path, 'wb') as f:
                        f.write(b'partial')
                    raise IOError('connection reset')

            with mock.patch.object(ud, 'CACHE_DIR', d), \
                    mock.patch.object(ud, '_s3', return_value=(FakeS3(), 'b')):
                with self.assertRaises(IOError):
                    ud.download_flatfile('day_aggs', '2026-01-05')
            self.assertEqual(os.listdir(d), [])


def bar(t, o, h, l, c):
    return {'t': t, 'o': o, 'h': h, 'l': l, 'c': c}


class TradeSim(unittest.TestCase):
    def _run(self, by_day, entry='2026-01-12', exit_='2026-01-13'):
        with mock.patch.object(sim.ud, 'minute_bars', lambda tk, d: by_day.get(d, [])):
            return sim.simulate('TEST', entry, exit_)

    def test_winter_premarket_bar_is_not_the_entry(self):
        # 14:00 UTC on a January day is 09:00 EST (pre-market) and must be skipped
        r = self._run({'2026-01-12': [
            bar(ms(2026, 1, 12, 14, 0), 50, 50, 50, 50),
            bar(ms(2026, 1, 12, 14, 30), 100, 100, 100, 100),
            bar(ms(2026, 1, 12, 20, 59), 100, 100, 100, 100)]}, exit_='2026-01-12')
        self.assertEqual(r['entry_open'], 100)
        self.assertEqual(r['armed_at'], None)

    def test_overnight_gap_fills_at_open_not_trail(self):
        day1 = [bar(ms(2026, 1, 12, 14, 30), 100, 100, 100, 100),
                bar(ms(2026, 1, 12, 15, 0), 100, 103, 102.5, 103)]       # arms, peak 103
        day2 = [bar(ms(2026, 1, 13, 14, 30), 95, 96, 94, 95)]             # gaps far below trail
        r = self._run({'2026-01-12': day1, '2026-01-13': day2})
        self.assertTrue(r['armed'])
        self.assertEqual(r['exit_reason'], 'trail_gap')
        self.assertEqual(r['exit_price'], 95)
        self.assertEqual(r['armed_at'], '2026-01-12 10:00 ET')

    def test_never_armed_holds_to_close(self):
        r = self._run({'2026-01-12': [bar(ms(2026, 1, 12, 14, 30), 100, 101, 99, 100)],
                       '2026-01-13': [bar(ms(2026, 1, 13, 20, 59), 98, 98, 97, 97)]})
        self.assertFalse(r['armed'])
        self.assertEqual(r['exit_reason'], 'held_to_close_unarmed')
        self.assertEqual(r['realized_return_pct'], -3.0)


class Controls(unittest.TestCase):
    def test_outcome_tiers(self):
        self.assertIsNone(ctrl._outcome(None))
        self.assertEqual(ctrl._outcome(100), 'BIG WIN')
        self.assertEqual(ctrl._outcome(101), 'WIN')
        self.assertEqual(ctrl._outcome(500), 'WIN')
        self.assertEqual(ctrl._outcome(1500), 'FLAT')
        self.assertEqual(ctrl._outcome(1501), 'LOSS')

    def test_grade_survives_missing_close(self):
        with tempfile.TemporaryDirectory() as d:
            ctrl_path = os.path.join(d, 'us-controls.jsonl')
            with open(ctrl_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({'type': 'random5', 'week_start': '2026-01-12',
                                    'tickers': ['AAA', 'BBB']}) + '\n')
            grouped = {'results': [{'T': 'AAA', 'o': 10, 'h': 11, 'c': None},
                                   {'T': 'BBB', 'o': 10, 'h': 12, 'c': 11}]}
            with mock.patch.object(ctrl, 'STOCKS', d), mock.patch.object(ctrl, 'CTRL', ctrl_path), \
                    mock.patch.object(ctrl.ud, '_pget', return_value=grouped), \
                    mock.patch('builtins.print'):
                ctrl.grade('2026-01-12', '2026-01-12', '2026-01-16')
            with open(ctrl_path, encoding='utf-8') as f:
                rows = [json.loads(x) for x in f]
            g = rows[-1]
            self.assertEqual(g['type'], 'grade')
            by = {r['ticker']: r for r in g['random5']}
            self.assertIsNone(by['AAA']['policy_return_pct'])
            self.assertEqual(by['BBB']['policy_return_pct'], 10.0)


class PremarketParse(unittest.TestCase):
    def test_reads_ticker_and_last_close_by_header(self):
        chunk = ('2026-01-12\n\n| # | Ticker | Score | Last Close |\n|---|---|---|---|\n'
                 '| 1 | NVDA | 82 | $120.50 |\n| 2 | BRK-B | 75 | 410 |\n| Sell plan | - | - | - |\n')
        self.assertEqual(pm._parse_picks_table(chunk), [('NVDA', 120.5), ('BRK-B', 410.0)])


if __name__ == '__main__':
    unittest.main()
