from django.http import JsonResponse
from django.views import View
from .github_client import GitHubClient

# 0406 커밋용 주석
# GitHub 관련 API 엔드포인트
# github_client.py 를 가져다 쓰는 views
"""
플랜 상세 페이지에서 "오늘 커밋 불러오기" 버튼 클릭
→ JS 가 /github/commits/?repo=내깃허브아이디/레파지토리네임(프젝이름 나는github-ai-planner)&date=2025-04-06 호출
→ CommitListView.get() 실행
→ 오늘 커밋 목록 반환
→ 화면에 커밋 목록 표시
→ "AI 요약 생성" 버튼 활성화

HTTP 상태코드 정리
200 → 성공 (기본값)
201 → 생성 성공 (POST로 DB 저장할 때)
400 → 잘못된 요청 (파라미터 누락 등)
401 → 인증 필요 (로그인 안 됨)
404 → 없는 리소스
500 → 서버 오류
"""

def get_github_client(request):
    """세션에서 access_token 꺼내서 GitHubClient 생성"""
    # 로그인할 때 세션에 저장해둔 토큰 꺼내기
    # accounts/views.py 의 GithubCallbackView 에서 저장했던 그거
    access_token = request.session.get("github_access_token")
    if not access_token:
        return None     # 토큰 없으면 미로그인 상태
    return GitHubClient(access_token)   # 토큰으로 GitHubClient 객체 생성해서 반환

# ── GET /github/repos/ ────────────────────────────────────────
class RepoListView(View):
    """로그인한 유저의 레포 목록 반환"""

    def get(self, request):
        client = get_github_client(request)
        if not client:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

        try:
            repos = client.get_repos()
            return JsonResponse({"success": True, "repos": repos})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ── GET /github/commits/?repo=owner/name&date=2025-04-25 ─────
class CommitListView(View):
    """특정 레포의 날짜별 커밋 목록 반환"""

    def get(self, request):
        client = get_github_client(request)
        if not client:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

        repo = request.GET.get("repo")          # URL 파라미터에서 레포명
        target_date = request.GET.get("date")   # URL 파라미터에서 날짜
        github_user = request.session.get("github_user", {})
        author = github_user.get("login", "")   # 내 커밋만 조회

        if not repo:
            return JsonResponse({"error": "repo 파라미터가 필요합니다."}, status=400)

        try:
            # github_client.py 의 get_commits_by_date() 호출
            commits = client.get_commits_by_date(repo, author, target_date)
            return JsonResponse({
                "success": True,
                "commits": commits,  # 커밋 목록
                "total": len(commits),   # 오늘 총 커밋 수
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)