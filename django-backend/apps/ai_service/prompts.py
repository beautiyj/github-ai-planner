from datetime import date


# AI에게 보낼 프롬프트 생성 함수 모음
# 프롬프트를 별도 파일로 분리해두면 나중에 수정하기 편함

def build_plan_prompt(data: dict) -> str:
    """
    프로젝트 플랜 생성용 프롬프트
    data: 폼에서 받은 딕셔너리
    modify_request 키가 있으면 수정 요청 모드로 동작
    """
    title          = data.get("title", "미정")
    purposes       = data.get("purposes", [])
    date_start     = data.get("date_start", "")
    date_end       = data.get("date_end", "")
    skills         = data.get("skills", [])
    features       = data.get("features", "")
    repo_url       = data.get("repo_url", "")
    tools          = data.get("tools", "")
    team_size      = data.get("team_size", 1)
    modify_request = data.get("modify_request", "").strip()  # 수정 요청

    # skills 형식: [{"name": "Python", "level": "초급"}, ...]
    skills_text = ", ".join(
        f"{s['name']}({s['level']})" for s in skills
    ) if skills else "미입력"

    date_text = (
        f"{date_start} ~ {date_end}"
        if date_start and date_end
        else "미정 (AI가 적절히 추천해주세요)"
    )

    # 목적 플래그
    is_team      = "팀 프로젝트" in purposes
    is_portfolio = "포트폴리오" in purposes
    is_study     = "학습용" in purposes

    # 아이디어 추천 요청 감지
    idea_keywords = ["아이디어", "추천", "제안", "뭐만들지", "뭐 만들지", "어떤 프로젝트", "응용"]
    needs_idea = any(kw in features for kw in idea_keywords)

    # 수정 요청 컨텍스트 블록
    modify_context = ""
    if modify_request:
        modify_context = f"""
[⚠️ 최우선 수정 요청]
사용자가 기존 플랜을 바탕으로 아래 수정을 요청했습니다:
"{modify_request}"
이 수정 사항을 반드시 최우선으로 반영하여 전체 플랜을 재구성하세요.
"""

    return f"""
당신은 실무 경험이 풍부한 시니어 개발자이자 프로젝트 멘토입니다.
{modify_context}
아래 정보를 바탕으로 구체적이고 실용적인 프로젝트 플랜을 작성해주세요.

== 프로젝트 정보 ==
제목: {title}
목적: {", ".join(purposes)}
희망 기간: {date_text}
팀원 수: {team_size}명
보유 기술 및 수준: {skills_text}
사용 가능한 툴/프로그램: {tools if tools else "미입력"}
요청 내용:
{features}
{f"연동 레포: {repo_url}" if repo_url else ""}

== 작성 규칙 ==
1. 반드시 아래 JSON 형식만 반환하세요. 앞뒤 설명 없이 JSON만.
2. milestones는 최소 4개, 최대 7개.
3. range 형식: "M/D ~ M/D" (예: "7/1 ~ 7/2")
4. tags는 ["백엔드","프론트엔드","AI","DB","배포","기획"] 중 복수 선택.
5. 오늘 날짜 기준으로 일정을 계산하세요. 오늘: {date.today().isoformat()}

== 아이디어 추천 규칙 ==
{"[아이디어 추천 요청 감지됨] 아래 규칙을 반드시 따르세요:" if needs_idea else "[구체적 기능 구현 요청]"}
{"- ideas 배열에 아이디어를 정확히 3개 작성하세요." if needs_idea else "- ideas 배열을 빈 배열([])로 반환하세요."}
{"- 각 아이디어는 id, title, features, difference, difficulty 필드를 모두 포함하세요." if needs_idea else ""}
{"- 3개 중 가장 적합한 아이디어 1개를 선택해서 마일스톤을 작성하고, 선택 이유를 stack_advice에 명시하세요." if needs_idea else ""}
{"- 단순 게시판/회원관리만 나열하지 말고, 이를 응용한 창의적인 서비스 아이디어를 제안하세요." if needs_idea else ""}

== 마일스톤 작성 규칙 ==
- 각 마일스톤 detail에 구체적인 구현 내용을 작성하세요 (클래스명, API 엔드포인트, DB 테이블 등)
{"- 팀원 " + str(team_size) + "명의 역할 분담을 마일스톤마다 명시하세요." if is_team else ""}
{"- Git 브랜치 전략(feature/develop/main)을 첫 마일스톤에 포함하세요." if is_team else ""}
{"- 마지막 마일스톤에 README 작성, 배포 방법, 면접 어필 포인트를 포함하세요." if is_portfolio else ""}
{"- 각 마일스톤에 학습 목표와 참고 자료 키워드를 포함하세요." if is_study else ""}

== 수준별 규칙 ==
- 입문/초급: 기본 CRUD 위주, 라이브러리 최소화, 단계별 학습 포함
- 중급: 설계 패턴, 성능 최적화, 테스트 코드 포함
- 고급: 아키텍처 설계, 확장성, CI/CD 포함

== 응답 JSON 형식 ==
{{
  "total_days": 숫자,
  "recommended_end_date": "YYYY-MM-DD",
  "analysis": "전체적인 프로젝트 총평 및 방향 요약 (2~3문장)",
  "ideas": [
    {{
      "id": 1,
      "title": "아이디어 제목",
      "features": "핵심 구현 기능 3~5가지",
      "difference": "차별점 또는 포폴 어필 포인트",
      "difficulty": "상/중/하 중 선택"
    }}
  ],
  "stack_advice": "기술 스택 활용 방법 및 추천 이유",
  "milestones": [
    {{
      "range": "M/D ~ M/D",
      "task": "이 기간 핵심 작업 제목",
      "tags": ["백엔드"],
      "detail": "구체적인 구현 내용{', 팀원 역할 분담 포함' if is_team else ''}"
    }}
  ],
  "daily_goal": "하루 권장 작업 목표",
  "warning_message": null
}}
"""


def build_summary_prompt(data: dict) -> str:
    """
    일일 커밋 요약용 프롬프트
    data: plan_id, date, commits, current_milestone, total_days, elapsed_days
    """
    from datetime import date as _date

    commits           = data.get("commits", [])
    target_date       = data.get("date", str(_date.today()))
    current_milestone = data.get("current_milestone", "미정")
    total_days        = data.get("total_days", 30)
    elapsed_days      = data.get("elapsed_days", 0)

    if commits:
        commit_list = "\n".join(
            f"{i+1}. {c.get('message', '')} "
            f"(+{c.get('additions', 0)} -{c.get('deletions', 0)}줄)"
            for i, c in enumerate(commits)
        )
    else:
        commit_list = "오늘 커밋 없음"

    progress_percent = round(
        (elapsed_days / total_days) * 100
    ) if total_days else 0

    return f"""
당신은 개발 프로젝트 진행 상황을 분석하는 AI입니다.
오늘의 GitHub 커밋 내역과 프로젝트 진도를 바탕으로 현황을 요약해주세요.

== 오늘 날짜 ==
{target_date}

== 오늘 커밋 내역 ==
{commit_list}

== 현재 진행 상황 ==
- 현재 마일스톤: {current_milestone}
- 전체 진도: {elapsed_days}일 / {total_days}일 ({progress_percent}% 경과)

== 응답 규칙 ==
1. 반드시 아래 JSON 형식만 반환하세요. 앞뒤 설명 없이 JSON만.
2. summary는 오늘 커밋 내용을 2~4문장으로 자연스럽게 요약.
3. advice는 현재 마일스톤 기준으로 내일 집중할 작업 1~2문장.
4. mood는 전체 진도 대비 현재 진행 상황 기준:
   - great: 일정보다 앞서 있음
   - good: 일정대로 진행 중
   - warning: 일정보다 약간 뒤처짐
   - danger: 일정보다 많이 뒤처짐
5. highlight는 오늘 커밋 중 가장 의미 있는 작업 한 줄. 커밋이 없으면 null.

== 응답 JSON 형식 ==
{{
  "summary": "오늘 작업 내용 요약",
  "advice": "내일 집중할 작업",
  "mood": "good",
  "progress_percent": {progress_percent},
  "highlight": "오늘 핵심 작업 한 줄 또는 null"
}}
"""