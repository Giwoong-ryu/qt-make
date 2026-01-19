#!/usr/bin/env python3
"""
데이터 흐름 추적 도구

사용법:
    python debug_data_flow.py tasks.process_video_task

출력:
    - 각 함수가 받는 입력
    - 각 함수가 반환하는 출력
    - 데이터 변환 단계별 스냅샷
"""
import ast
import inspect
from pathlib import Path


class DataFlowTracer:
    """함수 호출 체인 추적"""

    def __init__(self, entry_point: str):
        self.entry = entry_point
        self.call_chain = []

    def trace(self):
        """
        entry_point부터 시작해서 모든 함수 호출 추적

        Returns:
            List[Dict]: [
                {
                    'function': 'process_video_task',
                    'input': 'audio_file_path',
                    'calls': [
                        {'function': 'whisper.transcribe_to_srt', 'input': 'audio_path', 'output': 'srt_path'},
                        {'function': 'correction_service.apply_replacement_dictionary', 'input': 'srt_content', 'output': 'corrected_srt'}
                    ],
                    'output': 'video_url'
                }
            ]
        """
        print(f"[데이터 흐름 추적] {self.entry}")
        print("=" * 80)

        # tasks.py 읽기
        tasks_path = Path(__file__).parent / "app" / "tasks.py"
        with open(tasks_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

        # process_video_task 함수 찾기
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "process_video_task":
                self._analyze_function(node, source)
                break

    def _analyze_function(self, func_node, source):
        """함수 내부 분석"""
        print(f"\n📍 함수: {func_node.name}")
        print(f"   파라미터: {[arg.arg for arg in func_node.args.args]}")

        # 함수 내부 코드 추출
        func_lines = source.split('\n')[func_node.lineno - 1:func_node.end_lineno]

        # Step 단계 추출
        steps = []
        current_step = None

        for i, line in enumerate(func_lines):
            # Step 주석 감지
            if "# Step" in line or "# ========" in line:
                if current_step:
                    steps.append(current_step)
                current_step = {
                    'line': func_node.lineno + i,
                    'comment': line.strip(),
                    'operations': []
                }

            # 함수 호출 감지
            if current_step and "=" in line and "(" in line:
                # whisper.transcribe_to_srt(...) 같은 패턴
                if "whisper." in line or "correction_service." in line or "video_service." in line:
                    current_step['operations'].append({
                        'line': func_node.lineno + i,
                        'code': line.strip()
                    })

        if current_step:
            steps.append(current_step)

        # Step별 출력
        for step in steps:
            print(f"\n   {step['comment']}")
            for op in step['operations']:
                print(f"      Line {op['line']}: {op['code']}")

                # 데이터 흐름 분석
                if "transcribe_to_srt" in op['code']:
                    print(f"         ⚠️  여기서 SRT 생성 → words 사용!")
                elif "apply_replacement_dictionary" in op['code']:
                    if "srt_content" in op['code']:
                        print(f"         ❌ SRT 생성 후 교정 → 이미 늦음!")
                    elif "raw_text" in op['code']:
                        print(f"         ✅ raw text 교정 → 올바름!")


class QuickFixGenerator:
    """문제 발견 시 자동 수정 제안"""

    @staticmethod
    def check_correction_timing(tasks_path: Path):
        """교정 타이밍 검증"""
        with open(tasks_path, encoding="utf-8") as f:
            content = f.read()

        issues = []

        # 패턴 1: SRT 생성 후 교정 (잘못됨)
        if "srt_path = whisper.transcribe_to_srt" in content:
            if "correction_service.apply_replacement_dictionary(srt_content" in content:
                issues.append({
                    'type': 'correction_after_srt',
                    'severity': 'high',
                    'message': 'SRT 생성 후 교정 시도 → words 배열이 이미 생성됨',
                    'fix': 'raw transcription에 먼저 교정 적용 필요'
                })

        # 패턴 2: transcription.text만 수정 (words 누락)
        if "transcription.text = corrected_text" in content:
            if "transcription.words" not in content:
                issues.append({
                    'type': 'words_not_updated',
                    'severity': 'high',
                    'message': 'transcription.text만 수정, words 배열 미수정',
                    'fix': 'words 배열도 함께 업데이트 필요'
                })

        return issues


if __name__ == "__main__":
    # 데이터 흐름 추적
    tracer = DataFlowTracer("process_video_task")
    tracer.trace()

    print("\n" + "=" * 80)
    print("[자동 검증]")
    print("=" * 80)

    # 자동 검증
    tasks_path = Path(__file__).parent / "app" / "tasks.py"
    issues = QuickFixGenerator.check_correction_timing(tasks_path)

    if issues:
        print(f"\n⚠️  {len(issues)}개 문제 발견:")
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. [{issue['severity'].upper()}] {issue['type']}")
            print(f"   문제: {issue['message']}")
            print(f"   해결: {issue['fix']}")
    else:
        print("\n✅ 문제 없음")
