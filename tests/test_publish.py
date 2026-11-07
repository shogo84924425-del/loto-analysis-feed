import importlib.util
import pathlib
import tempfile
import unittest
import datetime as dt

P = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'publish.py'
spec = importlib.util.spec_from_file_location('loto_publish', P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NOW = dt.datetime(2026, 11, 7, 6, 0, tzinfo=dt.timezone.utc)


def fixture(game):
    cnt, mx = m.GAMES[game]
    return {
        'game': game, 'status': 'SUCCESS',
        'checkedAt': '2026-11-07T05:52:25Z',
        'targetIssue': 2153 if game == 'loto6' else 703,
        'targetDrawDate': '2026-11-09' if game == 'loto6' else '2026-11-13',
        'analysisStartIssue': 2053 if game == 'loto6' else 603,
        'analysisEndIssue': 2152 if game == 'loto6' else 702,
        'verificationLevel': 'SECONDARY_CROSSCHECK_100',
        'checks': {
            **{k: True for k in m.CHECKS},
            'officialAll100': False, 'secondaryCrosscheck100': True,
        },
        'sixChecks': {k: True for k in m.SIX_CHECKS},
        'sources': ['a', 'b'],
        'crossCheckedLive': 100,
        'crossCheckedFromStored': 0,
        'scheduleVerification': 'UNOFFICIAL_ESTIMATE',
        'predictions': [
            {'label': chr(65 + i), 'numbers': list(range(1 + i * cnt, 1 + (i + 1) * cnt))}
            for i in range(5)
        ],
    }


class CheckFeed(unittest.TestCase):
    def test_both_games_success(self):
        for game in m.GAMES:
            result = m.normalized(game, fixture(game), NOW, 200)
            self.assertEqual('SUCCESS', result['status'])
            self.assertEqual(5, len(result['predictions']))
            self.assertFalse(result['purchaseCutoffOfficiallyVerified'])

    def test_nonofficial_unmatched(self):
        payload = fixture('loto6')
        payload['checks']['secondaryCrosscheck100'] = False
        self.assertEqual('FAILED', m.normalized('loto6', payload, NOW, 200)['status'])

    def test_cutoff_rejects(self):
        payload = fixture('loto6')
        later = dt.datetime(2026, 11, 9, 9, 21, tzinfo=dt.timezone.utc)
        self.assertEqual('FAILED', m.normalized('loto6', payload, later, 200)['status'])

    def test_stale_rejects(self):
        payload = fixture('loto7')
        later = NOW + dt.timedelta(hours=10)
        self.assertEqual('FAILED', m.normalized('loto7', payload, later, 200)['status'])

    def test_unavailable_erases_tickets(self):
        payload = fixture('loto6')
        self.assertEqual([], m.normalized('loto6', payload, NOW, 503)['predictions'])

    def test_write_failure_for_failed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            result = m.publish(
                fetcher=lambda game: ({}, 503), now=NOW, out=pathlib.Path(directory)
            )
            self.assertEqual('FAILED', result['loto6']['status'])
            self.assertIn(
                '"predictions": []',
                (pathlib.Path(directory) / 'loto6.json').read_text(),
            )


if __name__ == '__main__':
    unittest.main()
