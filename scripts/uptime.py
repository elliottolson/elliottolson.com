#!/usr/bin/env python3
"""Check that the live site is working, and keep a record of what each check found.

Every run adds one line to data/uptime.jsonl. The Status page is drawn from that
file: build.py asks summary() for the last 90 days and writes it into the page.

The record is kept on the repository's `uptime` branch, away from the site's own
history, so there is no data/ folder in a fresh copy of `main`. The preview shows
made-up records instead, marked as a sample.

    python3 scripts/uptime.py           Run the checks and record them
    python3 scripts/uptime.py --verify  Exit non-zero if the latest record has a failure
"""
import http.client
import json
import math
import random
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data" / "uptime.jsonl"

DOMAIN = "elliottolson.com"
HOME = f"https://{DOMAIN}/"
MIN_CERT_DAYS = 14
TIMEOUT = 20
RETRIES = 3
RETRY_DELAY = 10
USER_AGENT = f"Mozilla/5.0 (compatible; {DOMAIN} uptime check)"

DAYS = 90        # how far back the Status page looks
KEEP_DAYS = 100  # how long a record is kept, a little more than the page shows
RECENT = 48      # how many response times the page charts


class Failed(Exception):
    """A check found a problem. The message is shown on the Status page."""

    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details


# The checks

def check_site():
    """The homepage loads and contains the expected content."""
    request = urllib.request.Request(HOME, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        raise Failed(f"The homepage returned an error ({error.code})") from error
    except OSError as error:
        raise Failed("The homepage did not load") from error
    ms = round((time.monotonic() - started) * 1000)
    if "<title>Elliott Olson" not in body:
        raise Failed("The homepage loaded without its expected content")
    return {"ms": ms}


def check_redirects():
    """Plain HTTP and www both redirect to the secure address."""
    for url in (f"http://{DOMAIN}/", f"https://www.{DOMAIN}/"):
        parts = urlsplit(url)
        connect = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        connection = connect(parts.netloc, timeout=TIMEOUT)
        try:
            connection.request("GET", "/", headers={"User-Agent": USER_AGENT})
            target = connection.getresponse().getheader("Location", "")
        except (OSError, http.client.HTTPException) as error:
            raise Failed(f"{url} did not respond") from error
        finally:
            connection.close()
        if target != HOME:
            raise Failed(f"{url} does not redirect to {HOME}")
    return {}


def check_certificate():
    """The certificate is valid for at least MIN_CERT_DAYS more days."""
    try:
        with socket.create_connection((DOMAIN, 443), timeout=TIMEOUT) as plain:
            with ssl.create_default_context().wrap_socket(plain, server_hostname=DOMAIN) as secure:
                certificate = secure.getpeercert()
    except OSError as error:
        raise Failed("A secure connection could not be made") from error
    issued = ssl.cert_time_to_seconds(certificate["notBefore"])
    expires = ssl.cert_time_to_seconds(certificate["notAfter"])
    # days: how long the certificate has left. of: how long it was issued for.
    details = {"days": int((expires - time.time()) // 86400), "of": round((expires - issued) / 86400)}
    if details["days"] < MIN_CERT_DAYS:
        raise Failed(f"The certificate expires in {details['days']} days", **details)
    return details


Check = namedtuple("Check", "id name about run")

# To watch something new, write a function like the ones above and add it here
CHECKS = [
    Check("site", "Website", "elliottolson.com loads and shows the homepage.", check_site),
    Check("redirects", "Redirects", "Plain HTTP and www both lead to the secure address.", check_redirects),
    Check("certificate", "Certificate", "The secure connection is valid and not about to expire.", check_certificate),
]


# Recording what they find

def attempt(check):
    """Run one check, retrying so that a single dropped connection isn't recorded as an outage."""
    for tries_left in range(RETRIES, -1, -1):
        try:
            result = {"ok": True, **check.run()}
            print(f"ok: {check.name}")
            return result
        except Failed as problem:
            print(f"FAIL: {check.name}: {problem} ({problem.__cause__ or 'no further detail'})")
            if not tries_left:
                return {"ok": False, "error": str(problem), **problem.details}
            time.sleep(RETRY_DELAY)


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def when(record):
    return datetime.strptime(record["t"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def read_log():
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]


def record_run():
    record = {"t": stamp(datetime.now(timezone.utc))}
    for check in CHECKS:
        record[check.id] = attempt(check)
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
    records = [old for old in read_log() if when(old) >= cutoff] + [record]
    LOG.parent.mkdir(exist_ok=True)
    LOG.write_text("".join(json.dumps(line, separators=(",", ":")) + "\n" for line in records), encoding="utf-8")


def failures(record):
    return [check for check in CHECKS if check.id in record and not record[check.id]["ok"]]


def verify():
    records = read_log()
    if not records:
        sys.exit("No checks have been recorded")
    failed = failures(records[-1])
    if failed:
        sys.exit("\n".join(f"{check.name}: {records[-1][check.id].get('error')}" for check in failed))
    print("The latest check found no problems")


# Summarising the record for the Status page

def incidents(records):
    """Each unbroken run of failing checks, newest first."""
    found, current = [], None
    for record in records:
        failed = failures(record)
        if failed and current is None:
            current = {"checks": [], "error": record[failed[0].id].get("error", ""), "start": record["t"], "end": None}
            found.append(current)
        if failed:
            current["checks"] += [check.name for check in failed if check.name not in current["checks"]]
        elif current is not None:
            current["end"] = record["t"]
            current = None
    return found[::-1]


def summary(records):
    """What the Status page needs to know about the last DAYS days, or None if nothing is recorded."""
    now = datetime.now(timezone.utc)
    first_day = now.date() - timedelta(days=DAYS - 1)
    records = [record for record in records if check_day(record) >= first_day]
    if not records:
        return None
    latest = records[-1]

    checks = []
    for check in CHECKS:
        # One [passed, total] pair per day, oldest first
        history = [[0, 0] for _ in range(DAYS)]
        for record in records:
            if check.id in record:
                day = history[(check_day(record) - first_day).days]
                day[0] += record[check.id]["ok"]
                day[1] += 1
        passed, total = (sum(day[i] for day in history) for i in (0, 1))
        result = latest.get(check.id, {"ok": True})
        checks.append({
            "id": check.id,
            "name": check.name,
            "about": check.about,
            "ok": result["ok"],
            "error": result.get("error"),
            # Rounded down, so that 100 always means every check passed
            "uptime": math.floor(passed / total * 10000) / 100 if total else None,
            "total": total,
            "history": history,
        })

    times = [record["site"].get("ms") for record in records if "site" in record]
    last_day = [record["site"]["ms"] for record in records
                if when(record) >= now - timedelta(hours=24) and record.get("site", {}).get("ms") is not None]
    certificate = latest.get("certificate", {})
    return {
        "checked": latest["t"],
        "since": records[0]["t"],
        "from": first_day.isoformat(),
        "checks": checks,
        "response": {"average": round(sum(last_day) / len(last_day)) if last_day else None, "recent": times[-RECENT:]},
        "certificate": {"days": certificate.get("days"), "of": certificate.get("of")},
        "incidents": incidents(records),
    }


def check_day(record):
    return when(record).date()


# Made-up records, for previewing the page

SAMPLES = ("ok", "down", "new")

# (hours ago it began, hours it lasted, what failed)
SAMPLE_OUTAGES = [
    (61 * 24 + 5, 9, {"site": "The homepage did not load",
                      "redirects": f"http://{DOMAIN}/ did not respond",
                      "certificate": "A secure connection could not be made"}),
    (37 * 24 + 14, 3, {"site": "The homepage returned an error (503)"}),
    (12 * 24 + 2, 1, {"redirects": f"https://www.{DOMAIN}/ does not redirect to {HOME}"}),
]
SAMPLE_OUTAGE_NOW = (1, 2, {"site": "The homepage did not load"})


def sample(scenario="ok"):
    """Records that show the page in one of three states.

    ok    Three months of history with a few past incidents, everything working now
    down  The same, with the site failing right now
    new   The first two days after the checks were switched on
    """
    random.seed(7)
    latest = datetime.now(timezone.utc) - timedelta(minutes=12)
    hours = 2 * 24 if scenario == "new" else DAYS * 24
    outages = [] if scenario == "new" else SAMPLE_OUTAGES + ([SAMPLE_OUTAGE_NOW] if scenario == "down" else [])

    records = []
    for ago in range(hours - 1, -1, -1):
        at = latest - timedelta(hours=ago)
        slow = 1.9 if random.random() < 0.03 else 1
        ms = round((176 + 34 * math.sin(at.hour / 24 * math.tau) + random.gauss(0, 14)) * slow)
        # A certificate that lasts 90 days and is replaced once it has 30 left
        age = (at - datetime(2026, 1, 1, tzinfo=timezone.utc)).days % 60
        record = {
            "t": stamp(at),
            "site": {"ok": True, "ms": ms},
            "redirects": {"ok": True},
            "certificate": {"ok": True, "days": 90 - age, "of": 90},
        }
        for began, lasted, failed in outages:
            if began >= ago > began - lasted:
                record.update({check: {"ok": False, "error": error} for check, error in failed.items()})
        records.append(record)
    return records


if __name__ == "__main__":
    verify() if "--verify" in sys.argv[1:] else record_run()
