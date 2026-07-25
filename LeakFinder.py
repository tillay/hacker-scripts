import re, socket, requests, threading
from collections import Counter
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
try:
    from dulwich.client import get_transport_and_path
    from dulwich.repo import MemoryRepo
except ImportError:
    print("Please install the dulwich library")
    exit(1)

lock = threading.Lock()
login_cache = {}
token = None
DEPTH = 400
DEADLINE = 5
socket.setdefaulttimeout(DEADLINE)
IDENT_RE = re.compile(r"^(.*?)\s*<([^>]+)>$")

def a(num): return f"\033[{num}m"

def api_request(endpoint, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"https://api.github.com{endpoint}", headers=headers)

def with_deadline(fn, seconds):
    ex = ThreadPoolExecutor(max_workers=1)
    try:
        return ex.submit(fn).result(timeout=seconds)
    finally:
        ex.shutdown(wait=False)

def normalise_repo(user_input):
    s = user_input.strip().removesuffix(".git")
    if s.startswith("https://github.com/") or s.startswith("git@github.com:"):
        s = s.split("github.com", 1)[1].lstrip("/:")
    parts = [p for p in s.split("/") if p]
    return f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else None

def tz_info(off_sec):
    return timezone(timedelta(seconds=max(-86340, min(86340, off_sec))))

def tz_label(off_sec):
    sign = "-" if off_sec < 0 else "+"
    h, m = divmod(abs(off_sec) // 60, 60)
    return f"UTC{sign}{h}:{m:02d}"

def fmt_range(first_ts, last_ts, off_sec):
    d1 = datetime.fromtimestamp(first_ts, tz_info(off_sec))
    d2 = datetime.fromtimestamp(last_ts, tz_info(off_sec))
    s1, s2 = f"{d1:%b} {d1.day}", f"{d2:%b} {d2.day}"
    if d1.date() == d2.date(): return f"{s1}, {d1.year}"
    if d1.year == d2.year: return f"{s1}-{s2}, {d1.year}"
    return f"{s1}, {d1.year}-{s2}, {d2.year}"

def wants(refs, **kwargs):
    return list({sha for ref, sha in refs.items()
                 if (ref.startswith(b"refs/heads/") or ref.startswith(b"refs/tags/"))
                 and not ref.endswith(b"^{}")})

def resolve_logins(repo_path, emails):
    with lock:
        emails = {e for e in emails if e not in login_cache}
    if not emails: return
    try:
        r = api_request(f"/repos/{repo_path}/commits?per_page=100", token)
        data = r.json() if r.status_code == 200 else []
    except Exception:
        data = []
    resolved = {}
    if isinstance(data, list):
        for c in data:
            if c["author"]: resolved.setdefault(c["commit"]["author"]["email"], c["author"]["login"])
    with lock:
        for e in emails: login_cache.setdefault(e, resolved.get(e, ""))

def get_identities(repo_path):
    client, path = get_transport_and_path(f"https://github.com/{repo_path}")
    repo = MemoryRepo()
    client.fetch(path, repo, determine_wants=wants, depth=DEPTH)
    store = repo.object_store
    commits = [store[sha] for sha in store if store[sha].type_name == b"commit"]

    parsed = []
    for c in commits:
        m = IDENT_RE.match(c.author.decode("utf-8", "replace"))
        if m:
            parsed.append((m.group(1), m.group(2), c.author_time, c.author_timezone))

    resolve_logins(repo_path, {e for _, e, _, _ in parsed})

    identities = []
    for name, email, ts, off_sec in parsed:
        with lock: login = login_cache.get(email, "")
        identities.append((login, name, email, ts, off_sec))
    return len(commits), identities

def run_analysis(repo_path, prev_authors, summary=None, unknowns=None):
    with lock: print_notes = len(prev_authors) == 0

    try:
        n_commits, identities = with_deadline(lambda: get_identities(repo_path), DEADLINE)
    except FuturesTimeoutError:
        print(f"{a(91)}Timed out: {repo_path}{a(0)}\n")
        return prev_authors
    except Exception as e:
        print(f"{a(91)}Failed: {repo_path} ({e}){a(0)}\n")
        return prev_authors

    if print_notes:
        print(f"{a(0)}\nResults for{a(96)} https://github.com/{repo_path} {a(0)}({n_commits} commits):\n")

    skip_summary = len({login for login, *_ in identities if login}) > 8
    repo_name = repo_path.split("/")[-1]
    for login, name, email, ts, off_sec in identities:
        author_string = " ".join([login, name, email])
        with lock:
            if summary is not None and not skip_summary:
                if login:
                    u = summary.setdefault(login, {"names": [], "emails": [], "repos": [], "tz": []})
                    if name not in u["names"]: u["names"].append(name)
                    if email not in u["emails"]: u["emails"].append(email)
                    if repo_name not in u["repos"]: u["repos"].append(repo_name)
                    u["tz"].append((ts, off_sec))
                elif unknowns is not None:
                    unknowns.append((name, email, ts, off_sec, repo_name))
            if author_string in prev_authors: continue
            if login != "": print(f"{a(0)}GH Username: {a(94)}{login}")
            print(f"{a(0)}Name: {a(91)}{name}\n{a(0)}Email: {a(92)}{email}{a(0)}\n")
            prev_authors.append(author_string)

    return prev_authors

def group_tz(entries):
    runs = []
    for ts, off_sec in sorted(entries):
        if runs and runs[-1][2] == off_sec:
            runs[-1][1] = ts
        else:
            runs.append([ts, ts, off_sec])

    days = lambda run: (run[1] - run[0]) / 86400
    merged = True
    while merged and len(runs) >= 3:
        merged = False
        for i in range(1, len(runs) - 1):
            l, m, r = runs[i - 1], runs[i], runs[i + 1]
            if m[2] == 0 and l[2] == r[2] and days(m) < 0.2 * (days(l) + days(r)):
                runs[i - 1:i + 2] = [[l[0], r[1], l[2]]]
                merged = True
                break

    return runs

def local_hours(entries):
    return Counter(datetime.fromtimestamp(ts, tz_info(off_sec)).hour for ts, off_sec in entries)

def barchart(data, labels, color, bar_width, height):
    max_count = max(data.values(), default=0)
    if not max_count: return
    scalar = max_count / height
    for row in range(height, 0, -1):
        cells = []
        for label in labels:
            v = data.get(label, 0) / scalar
            if v >= row: cells.append("█" * bar_width)
            elif v >= row - 0.25: cells.append("▆" * bar_width)
            elif v >= row - 0.5: cells.append("▄" * bar_width)
            elif v >= row - 0.75: cells.append("▂" * bar_width)
            else: cells.append(" " * bar_width)
        print(f"  {a(color)}{' '.join(cells)}{a(0)}")

def print_wakefulness(entries):
    counts = local_hours(entries)
    if not counts: return
    print(f"{a(0)}Commits by local hour:{a(0)}")
    barchart(counts, range(24), 96, 2, 8)
    print(f"  {a(37)}{' '.join(f'{h:02d}' for h in range(24))}{a(0)}")

def aggregate_unknowns(summary, unknowns):
    name_idx, email_idx = {}, {}
    for login, u in summary.items():
        for n in u["names"]:
            if n: name_idx.setdefault(n, set()).add(login)
        for e in u["emails"]:
            if e: email_idx.setdefault(e, set()).add(login)
    others = {}
    for name, email, ts, off_sec, repo_name in unknowns:
        logins = name_idx.get(name, set()) | email_idx.get(email, set())
        if len(logins) == 1:
            u = summary[next(iter(logins))]
            if name and name not in u["names"]: u["names"].append(name)
            if email and email not in u["emails"]: u["emails"].append(email)
            if repo_name not in u["repos"]: u["repos"].append(repo_name)
            u["tz"].append((ts, off_sec))
        elif name:
            o = others.setdefault(name, {"emails": [], "repos": [], "tz": []})
            if email and email not in o["emails"]: o["emails"].append(email)
            if repo_name not in o["repos"]: o["repos"].append(repo_name)
            o["tz"].append((ts, off_sec))
    return others

def print_summary(summary):
    print(f"{a(0)}\n{a(4)}Scan summary{a(0)}\n")
    for login in sorted(summary, key=lambda k: len(summary[k]["tz"]), reverse=True):
        u = summary[login]
        print(f"{a(0)}GH Username: {a(94)}{login}{a(0)} {a(37)}({len(u['tz'])} commits){a(0)}")
        print(f"{a(0)}Names: {a(91)}{', '.join(u['names'])}{a(0)}")
        print(f"{a(0)}Emails: {a(92)}{', '.join(u['emails'])}{a(0)}")
        repos = ', '.join(u['repos'][:10]) + (f" ... (+{len(u['repos']) - 10})" if len(u['repos']) > 10 else "")
        print(f"{a(0)}Repos: {a(33)}{repos}{a(0)}")
        print(f"{a(0)}Timezones:{a(0)}")
        for first_ts, last_ts, off_sec in group_tz(u["tz"]):
            print(f"  {a(95)}{tz_label(off_sec)}: {a(37)}{fmt_range(first_ts, last_ts, off_sec)}{a(0)}")
        print_wakefulness(u["tz"])
        print()

def print_others(others):
    if not others: return
    print(f"{a(0)}\n{a(4)}Other identities{a(0)}\n")
    for name in sorted(others, key=lambda k: len(others[k]["tz"]), reverse=True):
        o = others[name]
        print(f"{a(0)}Name: {a(91)}{name}{a(0)} {a(37)}({len(o['tz'])} commits){a(0)}")
        print(f"{a(0)}Emails: {a(92)}{', '.join(o['emails'])}{a(0)}")
        repos = ', '.join(o['repos'][:10]) + (f" ... (+{len(o['repos']) - 10})" if len(o['repos']) > 10 else "")
        print(f"{a(0)}Repos: {a(33)}{repos}{a(0)}")
        print(f"{a(0)}Timezones:{a(0)}")
        for first_ts, last_ts, off_sec in group_tz(o["tz"]):
            print(f"  {a(95)}{tz_label(off_sec)}: {a(37)}{fmt_range(first_ts, last_ts, off_sec)}{a(0)}")
        print()

def handle_user(user):
    target_repos = api_request(f"/users/{user}/repos?per_page=100", token).json()
    if not isinstance(target_repos, list):
        print(f"{a(33)}Github returned error: {target_repos['message'].lower()}{a(0)}")
        return
    if len(target_repos) == 0:
        print(f"{a(33)}User {user} has no repos!{a(0)}")
        return

    sorted_repos = sorted(target_repos, key=lambda r: r["created_at"])
    for i, repo in enumerate(sorted_repos):
        color = 93 if repo["fork"] else 95
        date = repo["created_at"].split("T")[0].replace("-", "/")
        print(f"{a(0)}{i+1}. {a(color)}{repo['name']}{a(0)} ({date})")

    index = input(f"{a(0)}Choose index to search (or 'scan' for all): {a(96)}")
    if index == "scan":
        targets = [r["full_name"] for r in sorted_repos if not r["fork"]]
        print(f"\n{a(0)}Doing full scan of {a(96)}@{user}{a(0)} ({len(targets)} repos):\n")
        all_authors, summary, unknowns = [""], {}, []
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(run_analysis, name, all_authors, summary, unknowns) for name in targets]
            for f in as_completed(futures): f.result()
        others = aggregate_unknowns(summary, unknowns)
        print_summary(summary)
        print_others(others)
    else:
        while index.isdigit() and 1 <= int(index) <= len(sorted_repos):
            run_analysis(sorted_repos[int(index) - 1]["full_name"], [])
            index = input(f"Choose another index: {a(96)}")

def main(user_input):
    global token
    while user_input != "" and user_input != "q":
        if user_input.startswith("ghp_") or user_input.startswith("github_pat_"):
            r = api_request("/user", user_input)
            if r.status_code == 200:
                token = user_input
                print(f"{a(32)}Logged in as {r.json()['login']}!{a(0)}")
            else:
                print(f"{a(31)}Unable to log in: {r.json()['message']}.{a(0)}")
        elif user_input.startswith("@"):
            handle_user(user_input[1:])
        else:
            repo_path = normalise_repo(user_input)
            if repo_path: run_analysis(repo_path, [])
            else: print(f"{a(33)}Not a github repo or @user!{a(0)}")

        user_input = input(f"{a(0)}Search github repo or @user: {a(96)}")

if __name__ == "__main__":
    print(f"\n{a(4)}{a(31)}Github LeakFinder CLI super haxx0r Xtreme edition pro max\n{a(0)}")
    try: main(input(f"Search github repo or @user: {a(96)}"))
    except KeyboardInterrupt: print()
