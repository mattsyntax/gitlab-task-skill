#!/usr/bin/env python3
"""GitLab issues helper for the gitlab-task skill.

Works on the git repository of the current directory:
  project  - from `git remote get-url origin` (override: GITLAB_PROJECT=group/repo)
  token    - GITLAB_ACCESS_TOKEN_WRITE or GITLAB_TOKEN, from env or <repo>/.env (never printed)
  API base - GITLAB_API from env or <repo>/.env, default https://<origin host>/api/v4
             (http:// is refused unless GITLAB_ALLOW_INSECURE=1: the token would travel unencrypted)
  mock     - GITLAB_MOCK=<dir> (env or .env, relative to the repo root): read labels.json and
             issues.json from <dir>, never touch the network, and only pretend to create issues

Usage:
  gitlab.py labels
  gitlab.py issues [--state all|opened|closed] [--out file.json]
  gitlab.py issue 229
  gitlab.py relabel "Old label" "New label" [--dry-run]
  gitlab.py create docs/tasks/01-foo.md [--dry-run]
  gitlab.py create-all [docs/tasks] [--dry-run]
  gitlab.py dates --from 2026-09-21 --to 2026-10-05 --count 14 [--tz +03:00] [--seed N]

Task file format: front matter, then the issue body (markdown).
  ---
  title: Issue title
  labels: Backend, BUG 🐛, To Do 📋
  created_at: 2026-09-21T10:15:00+03:00   (optional, needs admin / project owner token)
  depends_on: 01-foo.md                   (optional, file in the same dir)
  iid: 515                                (written back by the script after creation)
  ---
A file with iid is never created twice. depends_on: the dependency is created first;
its quoted title in the body gets " (#iid)" appended and a relates_to link is created
(blocks/is_blocked_by needs GitLab Premium).
"""
import datetime as dt
import json
import os
import random
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

PER_PAGE = 100  # GitLab maximum


def repo_root():
    try:
        return subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return os.getcwd()


ROOT = repo_root()


def read_env(*keys, required=True):
    for key in keys:
        if os.environ.get(key):
            return os.environ[key]
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                for key in keys:
                    if line.startswith(key + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    if required:
        sys.exit(f"{' / '.join(keys)} not found in env or {path}")
    return None


def project_info():
    host, path = os.environ.get("GITLAB_HOST"), read_env("GITLAB_PROJECT", required=False)
    if MOCK and not path:
        path = "demo/app"
    if not (host and path):
        url = subprocess.check_output(["git", "-C", ROOT, "remote", "get-url", "origin"], text=True).strip()
        m = re.match(r"^(?:ssh://)?(?:git@([^:/]+)[:/]|https?://(?:[^@/]+@)?([^/]+)/)(.+?)(?:\.git)?$", url)
        if not m:
            sys.exit(f"Cannot parse origin url: {url}")
        host = host or m.group(1) or m.group(2)
        path = path or m.group(3)
    base = read_env("GITLAB_API", required=False) or f"https://{host}/api/v4"
    if base.startswith("http://") and read_env("GITLAB_ALLOW_INSECURE", required=False) not in ("1", "true"):
        sys.exit(f"Refusing plain HTTP {base}: the token would travel unencrypted. "
                 "If you accept that, set GITLAB_ALLOW_INSECURE=1 in .env")
    return base.rstrip("/"), urllib.parse.quote(path, safe="")


_mock_dir = read_env("GITLAB_MOCK", required=False)
MOCK = os.path.join(ROOT, _mock_dir) if _mock_dir else None
_mock_created = {}  # draft path -> fake iid, so depends_on works within one mock run

_ctx = {}


def ctx():
    if not _ctx:
        _ctx["token"] = "mock" if MOCK else read_env("GITLAB_ACCESS_TOKEN_WRITE", "GITLAB_TOKEN")
        _ctx["api"], _ctx["project"] = project_info()
    return _ctx


def mock_request(method, path, params, data):
    """Answer the few endpoints the commands use from <GITLAB_MOCK>/labels.json and issues.json."""
    def load(name):
        with open(os.path.join(MOCK, name), encoding="utf-8") as f:
            return json.load(f)
    project = urllib.parse.unquote(ctx()["project"])
    rest = path.split(f"/projects/{ctx()['project']}", 1)[1]
    issues = load("issues.json")
    if method == "GET" and rest == "":
        return {"id": 1, "path_with_namespace": project}, {}
    if method == "GET" and rest == "/labels":
        return load("labels.json"), {}
    if method == "GET" and rest == "/issues":
        state, label = (params or {}).get("state", "all"), (params or {}).get("labels")
        return [i for i in issues if state in ("all", i["state"]) and (not label or label in i["labels"])], {}
    m = re.match(r"^/issues/(\d+)$", rest)
    if method == "GET" and m:
        found = [i for i in issues if i["iid"] == int(m.group(1))]
        if not found:
            sys.exit(f"HTTP 404 GET {path}: issue not found")
        return found[0], {}
    if method == "POST" and rest == "/issues":
        iid = max([i["iid"] for i in issues] + list(_mock_created.values())) + 1
        created_at = data.get("created_at") or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        return {"iid": iid, "created_at": created_at,
                "web_url": f"https://gitlab.example.com/{project}/-/issues/{iid}"}, {}
    if method in ("POST", "PUT"):
        return {}, {}
    sys.exit(f"mock: unsupported {method} {path}")


def request(method, path, params=None, data=None):
    if MOCK:
        return mock_request(method, path, params, data)
    c = ctx()
    url = f"{c['api']}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("PRIVATE-TOKEN", c["token"])
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"null"), r.headers
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {method} {path}: {e.read().decode(errors='replace')[:500]}")
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach {c['api']}: {e.reason}. If the API lives elsewhere, set GITLAB_API in .env")


def get_all(path, params=None):
    params = dict(params or {}, per_page=PER_PAGE, page=1)
    items = []
    while True:
        chunk, headers = request("GET", path, params)
        items.extend(chunk)
        nxt = headers.get("X-Next-Page")
        if not nxt:
            return items
        params["page"] = nxt


def P():
    return ctx()["project"]


def set_meta(file, key, value):
    text = open(file, encoding="utf-8").read()
    head, sep, rest = text.partition("\n---\n")
    lines = [l for l in head.splitlines() if not l.startswith(key + ":")]
    lines.append(f"{key}: {value}")
    open(file, "w", encoding="utf-8").write("\n".join(lines) + sep + rest)


def parse_task(file):
    text = open(file, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        sys.exit(f"{file}: no front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    if not meta.get("title"):
        sys.exit(f"{file}: title is required")
    return meta, m.group(2).strip()


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


# ---------------------------------------------------------------- commands

def cmd_labels(_args):
    for l in get_all(f"/projects/{P()}/labels"):
        print(f"{l['name']}\t{l.get('description') or ''}")


def cmd_issues(args):
    issues = get_all(f"/projects/{P()}/issues",
                     {"state": opt(args, "--state", "all"), "order_by": "created_at", "sort": "asc"})
    slim = [{k: i[k] for k in ("iid", "title", "state", "labels", "created_at", "web_url")} for i in issues]
    if "--out" in args:
        with open(opt(args, "--out"), "w", encoding="utf-8") as f:
            json.dump(slim, f, ensure_ascii=False, indent=1)
        print(f"{len(slim)} issues saved")
    else:
        for i in slim:
            print(f"#{i['iid']}\t{i['state']}\t{i['created_at'][:10]}\t{','.join(i['labels'])}\t{i['title']}")


def cmd_issue(args):
    issue, _ = request("GET", f"/projects/{P()}/issues/{int(args[0])}")
    print(f"#{issue['iid']} [{issue['state']}] {issue['title']}\n{', '.join(issue['labels'])}\n")
    print(issue.get("description") or "")


def cmd_relabel(args):
    old, new = args[0], args[1]
    known = {l["name"] for l in get_all(f"/projects/{P()}/labels")}
    if old not in known or new not in known:
        sys.exit(f"unknown label: {[l for l in (old, new) if l not in known]}")
    issues = get_all(f"/projects/{P()}/issues", {"state": "all", "labels": old})
    print(f"{len(issues)} issues with '{old}'")
    for i in issues:
        if "--dry-run" in args:
            print(f"#{i['iid']}\t{i['title']}")
            continue
        request("PUT", f"/projects/{P()}/issues/{i['iid']}", data={"add_labels": new, "remove_labels": old})
        print(f"#{i['iid']}\tdone")


def cmd_create(args):
    file, dry = args[0], "--dry-run" in args
    meta, body = parse_task(file)
    if meta.get("iid"):
        print(f"skip {file}: already created as #{meta['iid']}")
        return
    dep_iid = None
    if meta.get("depends_on"):
        dep_file = os.path.join(os.path.dirname(file), meta["depends_on"])
        dep_meta, _ = parse_task(dep_file)
        dep_iid = dep_meta.get("iid") or _mock_created.get(os.path.abspath(dep_file))
        if not dep_iid and not dry:
            sys.exit(f"{file}: create {meta['depends_on']} first")
        ref = f"#{dep_iid}" if dep_iid else "#<iid>"
        body = body.replace(f'"{dep_meta["title"]}"', f'"{dep_meta["title"]}" ({ref})')
    data = {"title": meta["title"], "description": body}
    if meta.get("labels"):
        labels = [l.strip() for l in meta["labels"].split(",") if l.strip()]
        known = {l["name"] for l in get_all(f"/projects/{P()}/labels")}
        unknown = [l for l in labels if l not in known]
        if unknown:
            sys.exit(f"{file}: unknown labels {unknown}")  # GitLab would silently create them
        data["labels"] = ",".join(labels)
    if meta.get("created_at"):
        data["created_at"] = meta["created_at"]
    if dry:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return
    issue, _ = request("POST", f"/projects/{P()}/issues", data=data)
    if MOCK:  # nothing was sent, so the draft must stay sendable
        _mock_created[os.path.abspath(file)] = issue["iid"]
        print("[mock] not sent, draft left without iid")
    else:
        set_meta(file, "iid", issue["iid"])
    if dep_iid:
        project_id = request("GET", f"/projects/{P()}")[0]["id"]
        request("POST", f"/projects/{P()}/issues/{issue['iid']}/links", data={
            "target_project_id": project_id, "target_issue_iid": int(dep_iid), "link_type": "relates_to"})
    print(f"#{issue['iid']}\t{issue['created_at']}\t{issue['web_url']}" + (f"\tlinked #{dep_iid}" if dep_iid else ""))


def cmd_create_all(args):
    folder = next((a for a in args if not a.startswith("--")), os.path.join(ROOT, "docs", "tasks"))
    files = sorted(f for f in os.listdir(folder) if re.match(r"^\d\d\w*-.*\.md$", f) and not f.startswith("00-"))
    metas = {f: parse_task(os.path.join(folder, f))[0] for f in files}
    ordered, seen = [], set()

    def visit(f):
        if f in seen:
            return
        seen.add(f)
        dep = metas[f].get("depends_on")
        if dep:
            if dep not in metas:
                sys.exit(f"{f}: depends_on {dep} not found")
            visit(dep)
        ordered.append(f)

    for f in sorted(files, key=lambda f: metas[f].get("created_at", "")):
        visit(f)
    for f in ordered:
        print(f"== {f}")
        cmd_create([os.path.join(folder, f)] + [a for a in args if a.startswith("--")])


def cmd_dates(args):
    """Spread --count timestamps over working days (Mon-Fri) between --from and --to,
    inside 09:20-12:00 and 13:00-17:30, never later than now. Sorted ascending."""
    tz = opt(args, "--tz", "+03:00")
    sign = 1 if tz[0] == "+" else -1
    hh, mm = map(int, tz[1:].split(":"))
    tzinfo = dt.timezone(sign * dt.timedelta(hours=hh, minutes=mm))
    start = dt.date.fromisoformat(opt(args, "--from"))
    now = dt.datetime.now(tzinfo)
    end = dt.date.fromisoformat(opt(args, "--to", now.date().isoformat()))
    count = int(opt(args, "--count", "1"))
    rnd = random.Random(int(opt(args, "--seed", "0")) or None)
    windows = [((9, 20), (12, 0)), ((13, 0), (17, 30))]
    minutes = []  # every allowed minute in the range
    d = start
    while d <= end:
        if d.weekday() < 5:
            for (h1, m1), (h2, m2) in windows:
                t = dt.datetime(d.year, d.month, d.day, h1, m1, tzinfo=tzinfo)
                stop = dt.datetime(d.year, d.month, d.day, h2, m2, tzinfo=tzinfo)
                while t < stop and t <= now:
                    minutes.append(t)
                    t += dt.timedelta(minutes=1)
        d += dt.timedelta(days=1)
    if len(minutes) < count:
        sys.exit("not enough working minutes in the range")
    # one random minute inside each of `count` equal buckets: evenly spread, not mechanical
    step = len(minutes) / count
    picks = [minutes[int(i * step + rnd.random() * step)] for i in range(count)]
    for p in picks:
        print(p.isoformat(timespec="seconds"))


if __name__ == "__main__":
    cmds = {"labels": cmd_labels, "issues": cmd_issues, "issue": cmd_issue, "relabel": cmd_relabel,
            "create": cmd_create, "create-all": cmd_create_all, "dates": cmd_dates}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](sys.argv[2:])
