import requests
from datetime import datetime

def a(num): return f"\033[{num}m"

def run_analysis(repo_path, prev_authors):
    response = requests.get(f"https://api.github.com/repos/{repo_path}/commits?per_page=100")
    return_headers, history_json = response.headers, response.json()
    print_notes = len(prev_authors) == 0

    if isinstance(history_json, list):
        num_commits = "100+" if len(history_json) == 100 else len(history_json)
        if print_notes:
            print(f"{a(0)}\nResults for{a(96)} https://github.com/{repo_path} {a(0)}({num_commits} commits):\n")
        for entry in history_json:
            login = entry["author"]["login"] if entry["author"] else ""
            name = entry["commit"]["author"]["name"]
            email = entry["commit"]["author"]["email"]

            tz_key, timezone = "", ""
            if entry["commit"]["verification"]["verified"]:
                signature = entry["commit"]["verification"]["payload"].split()
                for j, v in enumerate(signature):
                    if v == "committer" and tz_key == "":
                        timezone, timestamp = signature[j-1], int(signature[j-2])
                        day = datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d")
                        tz_key = timezone

                        hours = "+0" if int(timezone[1:3]) == 0 else timezone[0:3].strip("0")
                        minutes = "00" if timezone[3:5] == "0" else timezone[3:5]
                        timezone = f"UTC{hours}:{minutes} ({day})"

            author_string = " ".join([login, name, email, tz_key])

            if not author_string in prev_authors:
                if login != "": print(f"{a(0)}GH Username: {a(94)}{login}")
                print(f"{a(0)}Name: {a(91)}{name}\n{a(0)}Email: {a(92)}{email}{a(0)}")
                print("" if timezone == "" else f"{a(0)}Timezone: {a(95)}{timezone}{a(0)}\n")
                prev_authors.append(author_string)

        if len(history_json) == 100 and print_notes:
            print(f"{a(93)}Note: only scanned most recent 100 commits{a(0)}")
        if int(return_headers.get("X-RateLimit-Remaining")) < 20:
            reset = datetime.fromtimestamp(int(return_headers.get('X-RateLimit-Reset')))
            print(
                f"{a(36)}Ratelimit warning: {a(33)}{return_headers.get('X-RateLimit-Remaining')}"
                f"{a(36)}/{a(32)}{return_headers.get('X-RateLimit-Limit')}{a(36)} "
                f"requests remaining (reset at {a(37)}{reset:%H:%M:%S}{a(36)}){a(0)}"
            )
    else:
        if "rate limit" in history_json["message"]:
            print(f"{a(33)}Github rate limit exceeded!{a(0)}\n")
            return None
        else:
            print(f"{a(33)}Github returned error: {history_json["message"].lower()}{a(0)}\n")

    return prev_authors

print(f"\n{a(4)}{a(31)}Github LeakFinder CLI super haxx0r Xtreme edition pro max\n{a(0)}")

repo_url = input(f"Search github repo or @user: {a(96)}")

while repo_url != "" and repo_url != "q":
    if repo_url.startswith("https://github.com/") and repo_url.count("/") >= 4:
        repo_url = repo_url.split("/")
        repo_url = repo_url[3] + "/" + repo_url[4]
        run_analysis(repo_url, [])
    elif repo_url.count("/") == 1:
        run_analysis(repo_url, [])
    elif repo_url.startswith("@"):
        user_repos = requests.get(f"https://api.github.com/users/{repo_url[1:]}/repos?per_page=100").json()
        if isinstance(user_repos, list):
            sorted_repos = sorted(user_repos, key=lambda r: r["created_at"])
            for i, repo in enumerate(sorted_repos):
                color = 93 if repo["fork"] else 95
                date = repo["created_at"].split("T")[0].replace("-", "/")
                print(f"{a(0)}{i+1}. {a(color)}{repo["name"]}{a(0)} ({date})")

            if len(user_repos) > 0:
                index = input(f"{a(0)}Choose index to search: {a(96)}")
                if index == "scan":
                    print(f"{a(92)}Doing full scan for {a(96)}@{repo_url[1:]}{a(0)} ({len(user_repos)} repos):")
                    all_authors = [""]
                    for i, repo in enumerate(sorted_repos):
                        if not all_authors is None and not user_repos[i]["fork"]:
                            all_authors = run_analysis(user_repos[i]["full_name"], all_authors)
                else:
                    while index.isdigit() and int(index) <= len(user_repos):
                        run_analysis(sorted_repos[int(index) - 1]["full_name"], [])
                        index = input(f"Choose another index: {a(96)}")
            else:
                print(f"{a(33)}User {repo_url[1:]} has no repos!{a(0)}")
        else:
            print(f"{a(33)}Github returned error: {user_repos["message"].lower()}{a(0)}")
    else:
        print(f"{a(33)}Not a github repo or @user!{a(0)}")

    repo_url = input(f"{a(0)}Search github repo or @user: {a(96)}")
