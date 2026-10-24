import requests
from datetime import datetime, timezone


class GitHubClient:
    """GitHub REST API 호출을 담당하는 클래스"""

    BASE_URL = "https://api.github.com"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, endpoint: str, params: dict = None):
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def get_repos(self, per_page: int = 50) -> list:
        raw = self._get(
            "/user/repos",
            params={"sort": "updated", "per_page": per_page},
        )

        return [
            {
                "full_name": r["full_name"],
                "name": r["name"],
                "description": r.get("description", ""),
                "language": r.get("language", ""),
                "updated_at": r["updated_at"],
                "is_private": r["private"],
                "html_url": r.get("html_url", ""),
            }
            for r in raw
        ]

    def get_repo_detail(self, repo: str) -> dict:
        data = self._get(f"/repos/{repo}")
        return {
            "full_name": data.get("full_name", repo),
            "name": data.get("name", repo.split("/")[-1]),
            "description": data.get("description", ""),
            "language": data.get("language", ""),
            "default_branch": data.get("default_branch", "main"),
            "html_url": data.get("html_url", ""),
            "topics": data.get("topics", []),
            "stargazers_count": data.get("stargazers_count", 0),
            "open_issues_count": data.get("open_issues_count", 0),
        }

    def get_repo_readme(self, repo: str) -> str:
        try:
            response = requests.get(
                f"{self.BASE_URL}/repos/{repo}/readme",
                headers={**self.headers, "Accept": "application/vnd.github.raw"},
                timeout=15,
            )
            if response.status_code == 404:
                return ""
            response.raise_for_status()
            return response.text[:4000]
        except Exception:
            return ""

    def get_recent_commits(self, repo: str, author: str = None, per_page: int = 5) -> list:
        params = {"per_page": per_page}
        if author:
            params["author"] = author
        raw_commits = self._get(f"/repos/{repo}/commits", params=params)
        results = []
        for c in raw_commits[:per_page]:
            message = c.get("commit", {}).get("message", "").split("\n")[0]
            results.append({
                "message": message,
                "date": c.get("commit", {}).get("author", {}).get("date", ""),
                "sha": c.get("sha", "")[:7],
            })
        return results

    def get_commits_by_date(
            self, repo: str, author: str, target_date: str = None
    ) -> list:
        if target_date:
            dt = datetime.fromisoformat(target_date)
        else:
            dt = datetime.now(timezone.utc)

        since = dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        until = dt.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=timezone.utc)

        raw_commits = self._get(
            f"/repos/{repo}/commits",
            params={
                "author": author,
                "since": since.isoformat(),
                "until": until.isoformat(),
                "per_page": 100,
            },
        )

        result = []
        for c in raw_commits:
            sha = c["sha"]
            commit_data = {
                "sha": sha[:7],
                "message": c["commit"]["message"],
                "date": c["commit"]["author"]["date"],
                "url": c["html_url"],
                "additions": 0,
                "deletions": 0,
            }
            try:
                detail = self._get(f"/repos/{repo}/commits/{sha}")
                stats = detail.get("stats", {})
                commit_data["additions"] = stats.get("additions", 0)
                commit_data["deletions"] = stats.get("deletions", 0)
            except Exception:
                pass
            result.append(commit_data)
        return result

    def get_contribution_stats(self, repo: str) -> dict:
        try:
            stats = self._get(f"/repos/{repo}/stats/contributors")
            if not stats:
                return {"total_commits": 0}
            total_commits = sum(s.get("total", 0) for s in stats)
            return {"total_commits": total_commits}
        except Exception:
            return {"total_commits": 0}
