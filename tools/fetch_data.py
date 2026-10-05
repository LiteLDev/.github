#!/usr/bin/env python3
"""Collect the live numbers behind the profile animation into tools/data.json.

Public data only: public repositories, public contributors, public members. Runs weekly in CI
(.github/workflows/refresh-profile.yml) and can be run locally:

    GITHUB_TOKEN=$(gh auth token) python3 tools/fetch_data.py

Pillow is optional: with it, contributor avatars are re-sampled into 8x8 Minecraft heads;
without it, the heads already in data.json are kept.
"""
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

ORG = "LiteLDev"
API = "https://api.github.com"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data.json")

FEATURED = ["LeviLamina", "LegacyScriptEngine", "LeviLaunchroid", "LeviLauncher", "LeviStone", "LeviOptimize",
            "LeviAntiCheat", "MoreDimensions", "LeviSchematic", "CrashLogger", "levilamina-mod-template",
            "docker-levilamina-server", "LiteLoaderBDS", "bedrinth", "LegacyMoney", "LegacyRemoteCall",
            "legacy-script-engine-api", "bdsdown", "PreLoader", "PeEditor", "lipr", "bedrock-runtime-data"]
YEARLY = ["LiteLoaderBDS", "LeviLamina"]  # commits per calendar year
JOIN_REPOS = ["LiteLoaderBDS", "LeviLamina", "LegacyScriptEngine", "LeviLaunchroid", "LeviLauncher", "LeviStone",
              "legacy-script-engine-api", "LeviOptimize", "MoreDimensions"]
HEAD_COUNT = 40          # avatars for the most active people
JOIN_COUNT = 30          # "x joined the game" for the most active people
BOTS = re.compile(r"(\[bot\]$|^crowdin-bot$|^dependabot|^github-actions|^LeviMCBot$)", re.I)

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def req(url, method="GET"):
    if not url.startswith("http"):
        url = API + url
    r = urllib.request.Request(url, method=method, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "levimc-profile",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(r, timeout=60) as resp:
        body = resp.read()
        return (json.loads(body) if body else None), resp.headers


def get(url):
    return req(url)[0]


def paged(url):
    out = []
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}per_page=100"
    while url:
        data, hdr = req(url)
        out += data
        m = re.search(r'<([^>]+)>;\s*rel="next"', hdr.get("Link", "") or "")
        url = m.group(1) if m else None
    return out


def count(url):
    """Number of items behind a list endpoint (per_page=1 + the rel=last page number)."""
    sep = "&" if "?" in url else "?"
    data, hdr = req(f"{url}{sep}per_page=1")
    m = re.search(r'[?&]page=(\d+)>;\s*rel="last"', hdr.get("Link", "") or "")
    return int(m.group(1)) if m else len(data or [])


def oldest(url):
    sep = "&" if "?" in url else "?"
    n = count(url)
    if not n:
        return None
    data = get(f"{url}{sep}per_page=1&page={n}")
    return data[0] if data else None


def heads_for(people, previous):
    try:
        from PIL import Image, ImageEnhance
    except ImportError:
        print("Pillow not installed: keeping previous heads", file=sys.stderr)
        return {k: v for k, v in previous.items() if k in people}
    out = {}
    for login, avatar in people.items():
        try:
            with urllib.request.urlopen(f"{avatar}{'&' if '?' in avatar else '?'}s=64", timeout=30) as r:
                im = Image.open(io.BytesIO(r.read())).convert("RGB")
        except (urllib.error.URLError, OSError) as e:
            print(f"avatar {login}: {e}", file=sys.stderr)
            if login in previous:
                out[login] = previous[login]
            continue
        im = ImageEnhance.Color(im).enhance(1.25).resize((8, 8), Image.Resampling.BOX)
        out[login] = ["".join("%02x%02x%02x" % im.getpixel((x, y)) for x in range(8)) for y in range(8)]
    return out


def main():
    previous = {}
    if os.path.exists(OUT):
        previous = json.load(open(OUT, encoding="utf-8"))
    org = get(f"/orgs/{ORG}")
    repos = [r for r in paged(f"/orgs/{ORG}/repos?type=public") if not r["private"]]
    own = [r for r in repos if not r["fork"]]
    data = {
        "as_of": dt.date.today().isoformat(),
        "org": {"name": org["name"], "public_repos": len(own), "followers": org["followers"],
                "stars": sum(r["stargazers_count"] for r in own),
                "public_members": len(paged(f"/orgs/{ORG}/public_members"))},
        "repos": {}, "created": [], "yearly_commits": {}, "joined": {}, "heads": {},
    }
    for r in own:
        data["created"].append([r["created_at"][:10], r["name"], r["archived"]])
    data["created"].sort()

    commits_by_user, avatars = {}, {}
    contrib_counts = {}
    for r in own:
        try:
            cs = paged(f"/repos/{ORG}/{r['name']}/contributors")
        except urllib.error.HTTPError:
            cs = []
        cs = [c for c in (cs or []) if c.get("type") == "User" and not BOTS.search(c["login"])]
        contrib_counts[r["name"]] = cs
        for c in cs:
            commits_by_user[c["login"]] = commits_by_user.get(c["login"], 0) + c["contributions"]
            avatars[c["login"]] = c["avatar_url"]
    data["org"]["contributors"] = len(commits_by_user)

    by_name = {r["name"]: r for r in own}
    for name in FEATURED:
        r = by_name.get(name)
        if not r:
            continue
        rels = paged(f"/repos/{ORG}/{name}/releases")
        stable = [x for x in rels if not x["prerelease"] and not x["draft"]]
        latest = max(stable, key=lambda x: x["published_at"] or "", default=None)
        data["repos"][name] = {
            "stars": r["stargazers_count"], "forks": r["forks_count"], "created": r["created_at"][:10],
            "archived": r["archived"], "language": r["language"], "description": r["description"],
            "releases": len(rels), "downloads": sum(a["download_count"] for x in rels for a in x["assets"]),
            "latest": latest["tag_name"] if latest else None,
            "latest_date": latest["published_at"][:10] if latest else None,
            "first_release": min((x["published_at"][:10] for x in rels if x["published_at"]), default=None),
            "commits": count(f"/repos/{ORG}/{name}/commits"),
            "contributors": len(contrib_counts.get(name, [])),
            "top": [[c["login"], c["contributions"]] for c in contrib_counts.get(name, [])[:8]],
        }
    for name in YEARLY:
        data["yearly_commits"][name] = {}
        for y in range(2021, dt.date.today().year + 1):
            n = count(f"/repos/{ORG}/{name}/commits?since={y}-01-01T00:00:00Z&until={y}-12-31T23:59:59Z")
            if n:
                data["yearly_commits"][name][str(y)] = n

    # releases worth a toast: first, every new major, the latest
    marks = []
    for name in ("LeviLamina",):
        rels = sorted((x for x in paged(f"/repos/{ORG}/{name}/releases") if x["published_at"]),
                      key=lambda x: x["published_at"])
        seen = set()
        for x in rels:
            tag = x["tag_name"]
            major = tag.lstrip("v").split(".")[0]
            minor = ".".join(tag.lstrip("v").split(".")[:2])
            key = minor if major not in ("0", "1") else major
            if key not in seen and "-" not in tag:
                seen.add(key)
                marks.append([x["published_at"][:10], name, tag])
    data["release_marks"] = marks

    ranked = sorted(commits_by_user, key=lambda k: -commits_by_user[k])
    data["people"] = [[k, commits_by_user[k]] for k in ranked[:60]]
    for login in ranked[:JOIN_COUNT]:
        first = None
        for name in JOIN_REPOS:
            if name not in by_name or not any(c["login"] == login for c in contrib_counts.get(name, [])):
                continue
            try:
                c = oldest(f"/repos/{ORG}/{name}/commits?author={login}")
            except urllib.error.HTTPError:
                continue
            if c:
                d = c["commit"]["author"]["date"][:10]
                if not first or d < first[0]:
                    first = [d, name]
        if first:
            data["joined"][login] = first
    wanted = {k: avatars[k] for k in ranked[:HEAD_COUNT]}
    data["heads"] = heads_for(wanted, previous.get("heads", {}))

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {OUT}: {len(own)} repos, {data['org']['contributors']} contributors, {len(data['heads'])} heads")


if __name__ == "__main__":
    main()
