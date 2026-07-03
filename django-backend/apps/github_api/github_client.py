import requests
from datetime import datetime, timezone


# 0406 커밋용 주석
# GitHub REST API 호출 헬퍼 ( GitHub API 관련 코드를 한 번에 모아둬서 클린아키텍처 구현 )
# 커밋 조회, 레포 목록 등 GitHub API 관련 기능 전담 클래스
# 나중에 스프링부트로 리펙토링할 때 여기만 교체해도 됨
# https://docs.github.com/en/rest

"""
오늘 날짜 범위 설정 (00:00 ~ 23:59)
→ GitHub API로 내 커밋 목록 조회
→ 각 커밋마다 추가/삭제 줄 수 조회
→ AI 요약에 넘길 데이터로 정리해서 반환

코드 작성 기준
1. 역할이 다르면 파일을 분리해라
   → GitHub API 호출은 github_client.py
   → AI 호출은 ai_provider.py
   → DB 저장/조회는 views.py

2. 중복 코드는 함수로 빼라
   → _get() 처럼 공통 로직은 하나로

3. 외부 API 호출은 항상 try-except
   → 네트워크 오류, 인증 오류 등 언제든 날 수 있음

4. 필요한 데이터만 추려서 반환
   → API 응답 그대로 쓰지 말고 필요한 것만
"""

class GitHubClient:
    """GitHub REST API 호출을 담당하는 클래스"""

    BASE_URL = "https://api.github.com"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",  # 로그인한 유저 토큰
            "Accept": "application/vnd.github+json",  # GitHub API 응답 형식
            "X-GitHub-Api-Version": "2022-11-28",  # API 버전 고정
        }

    # 내부에서만 쓰는 함수라서 _ 앞에붙임
    def _get(self, endpoint: str, params: dict = None):
        """GET 요청 공통 처리"""
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(
            url,
            headers=self.headers,   # 인증 헤더 자동 포함
            params=params,          # ?sort=updated&per_page=50 같은 쿼리스트링
            timeout=15              # 15초 안에 응답 없으면 에러
        )
        response.raise_for_status()
        return response.json()

    # 깃허브 레포 목록 조회
    def get_repos(self, per_page: int = 50) -> list:
        """
        로그인한 유저의 레포 목록 반환
        """
        raw = self._get(
            "/user/repos",
            params={"sort": "updated", "per_page": per_page}
        )   # 필요한 것만 반환

        return [
            {
                "full_name": r["full_name"],
                "name": r["name"],
                "description": r.get("description", ""),    # 없으면 빈 문자열
                "language": r.get("language", ""),
                "updated_at": r["updated_at"],
                "is_private": r["private"],
            }
            for r in raw    # 리스트 컴프리헨션 (for문 축약)
        ]

    # 날짜별 커밋 조회
    def get_commits_by_date(
            self, repo: str, author: str, target_date: str = None
    ) -> list:
        """
        특정 날짜의 커밋 목록 반환
        repo: "owner/repoName"
        author: GitHub 유저명
        target_date: "2025-04-25" (없으면 오늘)
        """
        if target_date:
            dt = datetime.fromisoformat(target_date)
        else:
            dt = datetime.now(timezone.utc)

        # 당일 00:00 ~ 23:59 UTC 범위
        since = dt.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        until = dt.replace(
            hour=23, minute=59, second=59, microsecond=0, tzinfo=timezone.utc
        )

        raw_commits = self._get(
            f"/repos/{repo}/commits",
            params={
                "author": author,
                "since": since.isoformat(),
                "until": until.isoformat(),
                "per_page": 100,        # 최대100개
            },
        )

        result = []
        for c in raw_commits:
            sha = c["sha"]      # 커밋 고유 ID
            commit_data = {
                "sha": sha[:7],
                "message": c["commit"]["message"],
                "date": c["commit"]["author"]["date"],
                "url": c["html_url"],
                "additions": 0,
                "deletions": 0,
            }

            # 줄 수 변경 정보는 별도 API 호출 필요
            try:
                detail = self._get(f"/repos/{repo}/commits/{sha}")
                stats = detail.get("stats", {})
                commit_data["additions"] = stats.get("additions", 0)
                commit_data["deletions"] = stats.get("deletions", 0)
            except Exception:
                pass    # 상세 조회 실패해도 기본 정보는 반환

            result.append(commit_data)

        return result

    def get_contribution_stats(self, repo: str) -> dict:
        """레포 전체 기여도 통계 반환"""
        try:
            stats = self._get(f"/repos/{repo}/stats/contributors")
            if not stats:
                return {"total_commits": 0}
            total_commits = sum(s.get("total", 0) for s in stats)
            return {"total_commits": total_commits}
        except Exception:
            return {"total_commits": 0}
