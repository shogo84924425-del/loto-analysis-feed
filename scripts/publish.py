#!/usr/bin/env python3
"""Mirror sanitized, validated lottery forecast API results to GitHub raw files.

Only numbers and verification metadata are public. No credentials are needed.
A failed/stale source must erase previously-published predictions.
"""
import datetime as dt
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'feed'
API_BASE = 'https://loto-independent-analysis.imadokogo.workers.dev'
JST = dt.timezone(dt.timedelta(hours=9))
UTC = dt.timezone.utc
GAMES = {'loto6': (6, 43), 'loto7': (7, 37)}
CHECKS = (
    'loaded100', 'frequency', 'pairs', 'oddEven', 'lowHigh',
    'sums', 'dispersion', 'predictionRange', 'distinctTickets',
    'latestConfirmed', 'calendar'
)
SIX_CHECKS = ('frequency', 'pairs', 'oddEven', 'lowHigh', 'sums', 'dispersion')


def stamp(t):
    return t.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def failure(game, now, reason, code=None):
    return {
        'schemaVersion': 1,
        'game': game,
        'status': 'FAILED',
        'mirroredAt': stamp(now),
        'error': reason,
        'sourceHttpStatus': code,
        'predictions': [],
    }


def normalized(game, payload, now, http_status):
    if http_status != 200 or not isinstance(payload, dict):
        return failure(game, now, 'WORKER_UNAVAILABLE_OR_FAILED', http_status)
    try:
        assert payload.get('game') == game, 'GAME_MISMATCH'
        assert payload.get('status') == 'SUCCESS', 'SOURCE_NOT_SUCCESS'
        checks = payload['checks']
        assert all(checks.get(k) is True for k in CHECKS), 'CHECKS_INCOMPLETE'
        assert all(payload['sixChecks'].get(k) is True for k in SIX_CHECKS), 'SIX_CHECKS_INCOMPLETE'
        assert payload['analysisEndIssue'] - payload['analysisStartIssue'] == 99, 'WINDOW_NOT_100'
        assert isinstance(payload['targetIssue'], int) and payload['targetIssue'] > 0, 'TARGET_INVALID'
        verification = payload.get('verificationLevel')
        if checks.get('officialAll100') is True:
            quality = 'OFFICIAL_100'
        else:
            assert verification == 'SECONDARY_CROSSCHECK_100', 'NOT_VERIFIED'
            assert checks.get('secondaryCrosscheck100') is True, 'SECONDARY_NOT_COMPLETE'
            assert payload.get('crossCheckedLive', 0) + payload.get('crossCheckedFromStored', 0) >= 100, 'CROSSCHECK_COUNT'
            assert len(payload.get('sources') or []) >= 2, 'SOURCES_INCOMPLETE'
            quality = 'SECONDARY_CROSSCHECK_100'
        checked = dt.datetime.fromisoformat(payload['checkedAt'].replace('Z', '+00:00'))
        assert checked.tzinfo is not None, 'CHECKED_AT_TIMEZONE'
        assert dt.timedelta(minutes=-5) <= (now - checked) <= dt.timedelta(hours=8), 'SOURCE_STALE'
        draw_date = dt.date.fromisoformat(payload['targetDrawDate'])
        draw_cutoff = dt.datetime.combine(draw_date, dt.time(18, 20), tzinfo=JST)
        assert now < draw_cutoff, 'DRAW_CUTOFF_PASSED'
        length, maximum = GAMES[game]
        tickets = payload['predictions']
        assert isinstance(tickets, list) and len(tickets) == 5, 'TICKET_COUNT'
        assert [t.get('label') for t in tickets] == list('ABCDE'), 'TICKET_LABELS'
        result = []
        for t in tickets:
            ns = t['numbers']
            assert isinstance(ns, list) and len(ns) == length, 'NUMBER_COUNT'
            assert all(type(n) is int and 1 <= n <= maximum for n in ns), 'NUMBER_RANGE'
            assert ns == sorted(set(ns)), 'NUMBER_DUPLICATE_OR_UNSORTED'
            result.append({'label': t['label'], 'numbers': ns})
        assert len({tuple(t['numbers']) for t in result}) == 5, 'TICKETS_NOT_DISTINCT'
        return {
            'schemaVersion': 1,
            'game': game,
            'status': 'SUCCESS',
            'mirroredAt': stamp(now),
            'sourceCheckedAt': payload['checkedAt'],
            'targetIssue': payload['targetIssue'],
            'targetDrawDate': payload['targetDrawDate'],
            'analysisStartIssue': payload['analysisStartIssue'],
            'analysisEndIssue': payload['analysisEndIssue'],
            'verified100': True,
            'sixChecksComplete': True,
            'verificationLevel': quality,
            'scheduleVerification': payload.get('scheduleVerification', 'NOT_VERIFIED'),
            'purchaseCutoffOfficiallyVerified': False,
            'predictions': result,
        }
    except (AssertionError, KeyError, TypeError, ValueError, AttributeError) as e:
        msg = str(e) or 'INVALID_PAYLOAD'
        return failure(game, now, 'SOURCE_VALIDATION_FAILED:' + msg, http_status)


def fetch(game):
    url = f'{API_BASE}/api/v1/{game}?summary=1'
    request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'loto-github-feed/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=25) as r:
            return json.loads(r.read(150000).decode('utf-8')), r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read(150000).decode('utf-8')), e.code
        except (UnicodeError, ValueError):
            return {}, e.code
    except (urllib.error.URLError, TimeoutError, UnicodeError, ValueError, OSError):
        return {}, 0


def publish(fetcher=fetch, now=None, out=OUT):
    now = now or dt.datetime.now(UTC)
    out.mkdir(parents=True, exist_ok=True)
    data = {}
    for game in GAMES:
        payload, status = fetcher(game)
        normalized_result = normalized(game, payload, now, status)
        data[game] = normalized_result
        (out / f'{game}.json').write_text(
            json.dumps(normalized_result, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
            encoding='utf-8'
        )
    index = {'schemaVersion': 1, 'mirroredAt': stamp(now), 'games': data}
    (out / 'latest.json').write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8'
    )
    for game, result in data.items():
        print(f'{game}: {result["status"]} ({result.get("error", "validated")})')
    return data


if __name__ == '__main__':
    publish()
