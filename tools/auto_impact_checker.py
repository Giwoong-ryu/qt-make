"""
자동 영향 분석 및 검증 도구

기능:
1. 파일 형식 변경 시 관련 코드 자동 검색
2. 하드코딩된 값 탐지
3. 자동 수정 제안

Claude가 검증 시 자동으로 실행해야 하는 도구
"""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Issue:
    """발견된 문제"""
    file: str
    line: int
    severity: str  # HIGH, MEDIUM, LOW
    category: str
    description: str
    current_code: str
    suggested_fix: str


class AutoImpactChecker:
    """자동 영향 분석 검증기"""

    # 하드코딩 패턴 (문제가 될 수 있는 것들)
    HARDCODED_PATTERNS = {
        # 파일 확장자 하드코딩
        r'\.replace\(["\']\.mp3["\']': {
            "category": "file_extension_hardcode",
            "severity": "HIGH",
            "description": ".mp3 확장자 하드코딩 - 다른 오디오 형식(M4A, WAV) 미지원",
            "fix_pattern": "os.path.splitext() 사용"
        },
        r'\.replace\(["\']\.wav["\']': {
            "category": "file_extension_hardcode",
            "severity": "HIGH",
            "description": ".wav 확장자 하드코딩",
            "fix_pattern": "os.path.splitext() 사용"
        },
        r'\.endswith\(["\']\.mp3["\']\)': {
            "category": "file_extension_hardcode",
            "severity": "MEDIUM",
            "description": ".mp3만 체크 - 다른 형식 누락 가능",
            "fix_pattern": ".endswith(('.mp3', '.m4a', '.wav')) 사용"
        },

        # URL/경로 하드코딩
        r'http://localhost:\d+': {
            "category": "url_hardcode",
            "severity": "MEDIUM",
            "description": "localhost URL 하드코딩 - 배포 시 문제",
            "fix_pattern": "환경변수 사용"
        },
        r'/tmp/[a-zA-Z]': {
            "category": "path_hardcode",
            "severity": "LOW",
            "description": "/tmp 경로 하드코딩 - Windows 호환성 문제",
            "fix_pattern": "tempfile.gettempdir() 사용"
        },

        # API 키 하드코딩
        r'api_key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']': {
            "category": "security",
            "severity": "HIGH",
            "description": "API 키 하드코딩 - 보안 위험",
            "fix_pattern": "환경변수 사용"
        },
    }

    # 변경 유형별 영향 검사 규칙
    CHANGE_IMPACT_RULES = {
        "audio_format_change": {
            "triggers": ["mp3", "m4a", "wav", "audio", "오디오"],
            "search_patterns": [
                r"\.mp3",
                r"\.m4a",
                r"\.wav",
                r"audio_path",
                r"audio_file",
                r"음성",
                r"오디오"
            ],
            "check_files": ["stt.py", "video.py", "tasks.py", "main.py"]
        },
        "file_path_change": {
            "triggers": ["경로", "path", "파일", "저장"],
            "search_patterns": [
                r"file_path",
                r"save_path",
                r"output_path",
                r"\.replace\(",
                r"os\.path"
            ],
            "check_files": ["*.py"]
        },
        "api_change": {
            "triggers": ["API", "엔드포인트", "endpoint"],
            "search_patterns": [
                r"@app\.(get|post|put|delete)",
                r"fetch\(",
                r"axios\.",
                r"httpRequest"
            ],
            "check_files": ["main.py", "*.ts", "*.tsx"]
        }
    }

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues: list[Issue] = []

    def scan_hardcoded_patterns(self) -> list[Issue]:
        """하드코딩 패턴 스캔"""
        issues = []

        for py_file in self.project_root.rglob("*.py"):
            # 제외 경로
            if any(x in str(py_file) for x in ["__pycache__", "venv", ".git", "tools"]):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for pattern, info in self.HARDCODED_PATTERNS.items():
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            issues.append(Issue(
                                file=str(py_file.relative_to(self.project_root)),
                                line=i,
                                severity=info["severity"],
                                category=info["category"],
                                description=info["description"],
                                current_code=line.strip(),
                                suggested_fix=info["fix_pattern"]
                            ))
            except Exception as e:
                print(f"[WARN] 파일 읽기 실패: {py_file} - {e}")

        self.issues.extend(issues)
        return issues

    def analyze_change_impact(self, change_description: str) -> dict:
        """변경 사항에 대한 영향 분석"""
        result = {
            "triggered_rules": [],
            "files_to_check": set(),
            "patterns_to_search": [],
            "potential_issues": []
        }

        # 변경 설명에서 관련 규칙 찾기
        for rule_name, rule in self.CHANGE_IMPACT_RULES.items():
            for trigger in rule["triggers"]:
                if trigger.lower() in change_description.lower():
                    result["triggered_rules"].append(rule_name)
                    result["patterns_to_search"].extend(rule["search_patterns"])
                    result["files_to_check"].update(rule["check_files"])
                    break

        # 파일 검색
        files_found = []
        for pattern in result["files_to_check"]:
            if pattern.startswith("*"):
                files_found.extend(self.project_root.rglob(pattern))
            else:
                files_found.extend(self.project_root.rglob(f"**/{pattern}"))

        # 패턴 검색
        for file_path in files_found:
            if any(x in str(file_path) for x in ["__pycache__", "venv", ".git"]):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                for search_pattern in result["patterns_to_search"]:
                    for i, line in enumerate(lines, 1):
                        if re.search(search_pattern, line, re.IGNORECASE):
                            result["potential_issues"].append({
                                "file": str(file_path.relative_to(self.project_root)),
                                "line": i,
                                "code": line.strip(),
                                "matched_pattern": search_pattern
                            })
            except Exception:
                pass

        result["files_to_check"] = list(result["files_to_check"])
        return result

    def generate_verification_report(self) -> str:
        """검증 리포트 생성 (Claude가 사용자에게 보여줄 형식)"""
        self.scan_hardcoded_patterns()

        report = []
        report.append("=" * 60)
        report.append("[자동 검증 리포트]")
        report.append("=" * 60)

        # 심각도별 분류
        high_issues = [i for i in self.issues if i.severity == "HIGH"]
        medium_issues = [i for i in self.issues if i.severity == "MEDIUM"]
        low_issues = [i for i in self.issues if i.severity == "LOW"]

        if high_issues:
            report.append("\n[HIGH] 즉시 수정 필요:")
            for issue in high_issues:
                report.append(f"  - {issue.file}:{issue.line}")
                report.append(f"    문제: {issue.description}")
                report.append(f"    현재: {issue.current_code}")
                report.append(f"    수정: {issue.suggested_fix}")
                report.append("")

        if medium_issues:
            report.append("\n[MEDIUM] 수정 권장:")
            for issue in medium_issues:
                report.append(f"  - {issue.file}:{issue.line}")
                report.append(f"    문제: {issue.description}")
                report.append(f"    수정: {issue.suggested_fix}")
                report.append("")

        if low_issues:
            report.append("\n[LOW] 참고:")
            for issue in low_issues:
                report.append(f"  - {issue.file}:{issue.line}: {issue.description}")

        if not self.issues:
            report.append("\n[OK] 하드코딩 패턴 발견 안됨")

        report.append("\n" + "=" * 60)
        report.append(f"총 {len(self.issues)}개 이슈 (HIGH: {len(high_issues)}, MEDIUM: {len(medium_issues)}, LOW: {len(low_issues)})")
        report.append("=" * 60)

        return "\n".join(report)


def run_verification(project_root: str, change_description: str = None):
    """검증 실행 (Claude가 호출)"""
    checker = AutoImpactChecker(project_root)

    # 1. 기본 하드코딩 패턴 검사
    print(checker.generate_verification_report())

    # 2. 변경 사항 영향 분석
    if change_description:
        print("\n" + "=" * 60)
        print(f"[변경 영향 분석] '{change_description}'")
        print("=" * 60)

        impact = checker.analyze_change_impact(change_description)

        if impact["triggered_rules"]:
            print(f"\n적용된 규칙: {', '.join(impact['triggered_rules'])}")

        if impact["potential_issues"]:
            print(f"\n확인 필요한 위치 ({len(impact['potential_issues'])}개):")
            for issue in impact["potential_issues"][:20]:  # 최대 20개
                print(f"  - {issue['file']}:{issue['line']}")
                print(f"    코드: {issue['code'][:80]}...")
                print(f"    매칭: {issue['matched_pattern']}")
                print()
        else:
            print("\n[OK] 관련 영향 없음")


if __name__ == "__main__":
    import sys

    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    change_desc = sys.argv[2] if len(sys.argv) > 2 else None

    run_verification(project_root, change_desc)
