"""Ship the working tree as a pull request.

`main` is protected on the public repo, so the old `git push` straight to main
is refused. This commits whatever is in the working tree onto a fresh branch
cut from the current HEAD, rebases it onto origin/main, pushes it, and opens
the pull request through the GitHub API.

Token lookup, in order: the GITHUB_TOKEN or GH_TOKEN environment variable, then
the first line of BalanceLeadTools/GitHubToken.txt (gitignored, so it never
travels with a commit). A fine-grained token needs "Contents: read" and
"Pull requests: read and write" on the repo; a classic one needs `public_repo`.
Without a token the branch is still pushed and a prefilled "create pull
request" link is printed, so nothing is lost -- only the last click is manual.
"""

import os
import re
import subprocess
import sys
import urllib.parse
import webbrowser

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "BalanceLeadTools", "GitHubToken.txt")
API = "https://api.github.com"


def git(*args, check=True):
    """Run a git command in the repo and return its stdout, stripped."""
    r = subprocess.run(["git", "-C", BASE_DIR, *args],
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + "\n" + (r.stderr or r.stdout).strip())
    return r.stdout.strip()


def slugify(text):
    """Branch-name-safe form of the change title."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:60].strip("-")
    return slug or "change"


def free_branch_name(slug):
    """First unused branch name, locally and on origin."""
    taken = set(git("branch", "--format=%(refname:short)").splitlines())
    taken |= {b.split("/", 1)[1] for b in
              git("branch", "-r", "--format=%(refname:short)").splitlines()
              if b.startswith("origin/") and "/" in b}
    name, n = slug, 2
    while name in taken:
        name, n = "{}-{}".format(slug, n), n + 1
    return name


def read_token():
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var, "").strip():
            return os.environ[var].strip()
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8-sig") as fh:
            token = fh.readline().strip()
        if token:
            return token
    return None


def origin_slug():
    """owner/repo as written in the origin URL (may be a pre-transfer name)."""
    url = git("remote", "get-url", "origin")
    url = re.sub(r"^git@github\.com:", "https://github.com/", url)
    path = urllib.parse.urlparse(url).path.strip("/")
    return re.sub(r"\.git$", "", path)


def resolve_repo(session):
    """Real owner/repo and default branch, following any transfer redirect.

    The origin URL still reads Nilsix/Bleach-Rebirth-of-Souls-Community-Patch
    even though the repo now lives in the org, so ask the API rather than
    hardcoding either name.
    """
    slug = origin_slug()
    try:
        r = session.get("{}/repos/{}".format(API, slug), timeout=20)
        if r.ok:
            data = r.json()
            return data["full_name"], data.get("default_branch", "main")
    except requests.RequestException:
        pass
    return slug, "main"


def default_branch():
    """Default branch from the local remote HEAD, for use before any API call."""
    try:
        return git("symbolic-ref", "refs/remotes/origin/HEAD").rsplit("/", 1)[-1]
    except RuntimeError:
        return "main"


def compare_url(repo, branch, base, title, body):
    query = urllib.parse.urlencode({"expand": "1", "title": title, "body": body})
    return "https://github.com/{}/compare/{}...{}?{}".format(repo, base, branch, query)


def build_body(base):
    """PR body: the commits being shipped and the files they touch."""
    commits = git("log", "--format=- %s", "{}..HEAD".format(base))
    files = git("diff", "--name-status", "{}...HEAD".format(base))
    parts = []
    if commits:
        parts.append("**Commits**\n\n" + commits)
    if files:
        parts.append("**Files**\n\n```\n" + files + "\n```")
    parts.append("_Opened by ShipChanges._")
    return "\n\n".join(parts)


def open_pull_request(session, repo, branch, base, title, body):
    """Create the PR, or return the existing one if the branch already has one."""
    owner = repo.split("/")[0]
    r = session.post("{}/repos/{}/pulls".format(API, repo), timeout=30, json={
        "title": title,
        "body": body,
        "head": "{}:{}".format(owner, branch),
        "base": base,
    })
    if r.status_code == 201:
        return r.json()["html_url"], None
    if r.status_code == 422:
        existing = session.get("{}/repos/{}/pulls".format(API, repo), timeout=20,
                               params={"head": "{}:{}".format(owner, branch),
                                       "state": "open"})
        if existing.ok and existing.json():
            return existing.json()[0]["html_url"], "a pull request was already open for this branch"
    detail = ""
    try:
        payload = r.json()
        detail = payload.get("message", "")
        for err in payload.get("errors", []):
            detail += " | " + str(err.get("message", err))
    except ValueError:
        detail = r.text[:200]
    return None, "GitHub answered {}: {}".format(r.status_code, detail)


def main():
    print("== ShipChanges ==\n")

    try:
        git("rev-parse", "--git-dir")
    except RuntimeError:
        print("Not a git repository: " + BASE_DIR)
        return 1

    start_branch = git("rev-parse", "--abbrev-ref", "HEAD")
    base = default_branch()

    print("Fetching origin ...")
    git("fetch", "origin", "--quiet", check=False)

    dirty = git("status", "--porcelain")
    ahead = git("log", "--oneline", "origin/{}..HEAD".format(base), check=False)
    if not dirty and not ahead:
        print("\nNothing to ship: the working tree is clean and HEAD matches "
              "origin/{}.".format(base))
        return 0

    if dirty:
        print("\nChanges to ship:\n")
        print(git("status", "--short"))
    if ahead:
        print("\nCommits already made that will travel with this pull request:\n")
        print(ahead)

    title = input("\nName of the change (this becomes the commit and the PR title): ").strip()
    if not title:
        print("No name given, nothing shipped.")
        return 1

    branch = free_branch_name(slugify(title))
    print("\nBranch: {}".format(branch))

    # Cut the branch before committing, so local {base} is never left carrying
    # a commit that only belongs on the pull request.
    git("switch", "-c", branch)
    try:
        if dirty:
            git("add", "-A")
            git("commit", "-m", title)

        # Land on top of whatever main is now. Binary game files conflict badly,
        # so a failed rebase is abandoned rather than fought: the PR still opens
        # and GitHub reports the conflict.
        if git("rev-parse", "HEAD") != git("rev-parse", "origin/{}".format(base)):
            r = subprocess.run(["git", "-C", BASE_DIR, "rebase", "origin/" + base],
                               capture_output=True, text=True)
            if r.returncode != 0:
                subprocess.run(["git", "-C", BASE_DIR, "rebase", "--abort"],
                               capture_output=True, text=True)
                print("\nCould not rebase onto origin/{} cleanly, shipping the "
                      "branch as it is. Resolve the conflict on GitHub."
                      .format(base))

        print("\nPushing ...")
        git("push", "-u", "origin", branch)
    except RuntimeError as exc:
        print("\nFailed, and your commit is safe on branch {}:\n{}".format(branch, exc))
        return 1

    body = build_body("origin/" + base)

    session = requests.Session()
    session.headers.update({"Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28"})
    token = read_token()
    if token:
        session.headers["Authorization"] = "Bearer " + token

    repo, api_base = resolve_repo(session)
    base = api_base or base

    url, problem = (None, "no GitHub token found")
    if token:
        url, problem = open_pull_request(session, repo, branch, base, title, body)

    print()
    if url:
        if problem:
            print("Note: {}.".format(problem))
        print("Pull request: " + url)
        webbrowser.open(url)
    else:
        fallback = compare_url(repo, branch, base, title, body)
        print("The branch is pushed, but the pull request was not opened "
              "automatically ({}).".format(problem))
        print("Opening the prefilled page instead -- press 'Create pull request':")
        print(fallback)
        webbrowser.open(fallback)
        if not token:
            print("\nTo skip that click next time, put a GitHub token in:\n  "
                  + TOKEN_FILE)

    # Leave the dev where they started rather than on the shipped branch.
    if start_branch != branch:
        subprocess.run(["git", "-C", BASE_DIR, "switch", start_branch],
                       capture_output=True, text=True)
        print("\nBack on branch {}.".format(start_branch))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
