"""
AST 기반 영향 분석 도구

사용법:
    python ast_analyzer.py --file backend/app/services/stt.py --search ".mp3"
    python ast_analyzer.py --dir backend/app --search "audio_path"
"""

import argparse
import ast
import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionInfo:
    """함수 정보"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    calls: list[str] = field(default_factory=list)  # 호출하는 함수들
    called_by: list[str] = field(default_factory=list)  # 이 함수를 호출하는 함수들
    string_literals: list[str] = field(default_factory=list)  # 함수 내 문자열 리터럴
    variables_used: list[str] = field(default_factory=list)  # 사용하는 변수들


@dataclass
class ClassInfo:
    """클래스 정보"""
    name: str
    file_path: str
    line_start: int
    line_end: int
    methods: list[str] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)


class CodeAnalyzer(ast.NodeVisitor):
    """AST 기반 코드 분석기"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions: dict[str, FunctionInfo] = {}
        self.classes: dict[str, ClassInfo] = {}
        self.imports: list[str] = []
        self.string_literals: list[tuple] = []  # (line, value)
        self.current_function: str = None
        self.current_class: str = None

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        bases = [self._get_name(base) for base in node.bases]
        class_info = ClassInfo(
            name=node.name,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            base_classes=bases
        )
        self.classes[node.name] = class_info

        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        full_name = f"{self.current_class}.{node.name}" if self.current_class else node.name

        func_info = FunctionInfo(
            name=full_name,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno
        )
        self.functions[full_name] = func_info

        if self.current_class and self.current_class in self.classes:
            self.classes[self.current_class].methods.append(node.name)

        old_function = self.current_function
        self.current_function = full_name
        self.generic_visit(node)
        self.current_function = old_function

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        if self.current_function:
            call_name = self._get_call_name(node)
            if call_name:
                self.functions[self.current_function].calls.append(call_name)
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            self.string_literals.append((node.lineno, node.value))
            if self.current_function and self.current_function in self.functions:
                self.functions[self.current_function].string_literals.append(node.value)
        self.generic_visit(node)

    def _get_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def _get_call_name(self, node) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""


class ImpactAnalyzer:
    """변경 영향 분석기"""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.all_functions: dict[str, FunctionInfo] = {}
        self.all_classes: dict[str, ClassInfo] = {}
        self.file_analyzers: dict[str, CodeAnalyzer] = {}

    def analyze_directory(self, extensions: list[str] = [".py"]):
        """디렉토리 전체 분석"""
        for ext in extensions:
            for file_path in self.root_dir.rglob(f"*{ext}"):
                self.analyze_file(str(file_path))

        # 함수 호출 관계 구축
        self._build_call_graph()

    def analyze_file(self, file_path: str) -> CodeAnalyzer:
        """단일 파일 분석"""
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)
            analyzer = CodeAnalyzer(file_path)
            analyzer.visit(tree)

            self.file_analyzers[file_path] = analyzer
            self.all_functions.update(analyzer.functions)
            self.all_classes.update(analyzer.classes)

            return analyzer
        except SyntaxError as e:
            print(f"[WARN] 구문 오류: {file_path} - {e}")
            return None
        except Exception as e:
            print(f"[WARN] 분석 실패: {file_path} - {e}")
            return None

    def _build_call_graph(self):
        """함수 호출 그래프 구축"""
        for func_name, func_info in self.all_functions.items():
            for called in func_info.calls:
                # 호출되는 함수 찾기
                for target_name, target_info in self.all_functions.items():
                    if target_name.endswith(f".{called}") or target_name == called:
                        if func_name not in target_info.called_by:
                            target_info.called_by.append(func_name)

    def search_string(self, search_term: str) -> list[dict]:
        """문자열 리터럴 검색"""
        results = []
        for file_path, analyzer in self.file_analyzers.items():
            for line, value in analyzer.string_literals:
                if search_term in value:
                    # 이 문자열이 속한 함수 찾기
                    containing_func = self._find_containing_function(file_path, line)
                    results.append({
                        "file": file_path,
                        "line": line,
                        "value": value,
                        "function": containing_func,
                        "impact": self._get_impact_chain(containing_func) if containing_func else []
                    })
        return results

    def _find_containing_function(self, file_path: str, line: int) -> str:
        """특정 라인이 속한 함수 찾기"""
        for func_name, func_info in self.all_functions.items():
            if func_info.file_path == file_path:
                if func_info.line_start <= line <= func_info.line_end:
                    return func_name
        return None

    def _get_impact_chain(self, func_name: str, visited: set[str] = None) -> list[str]:
        """함수 변경 시 영향받는 함수 체인"""
        if visited is None:
            visited = set()

        if func_name in visited:
            return []
        visited.add(func_name)

        chain = []
        if func_name in self.all_functions:
            for caller in self.all_functions[func_name].called_by:
                chain.append(caller)
                chain.extend(self._get_impact_chain(caller, visited))

        return chain

    def find_function_impacts(self, func_name: str) -> dict:
        """특정 함수 변경 시 영향 분석"""
        if func_name not in self.all_functions:
            # 부분 매칭 시도
            matches = [f for f in self.all_functions if func_name in f]
            if matches:
                func_name = matches[0]
            else:
                return {"error": f"함수 '{func_name}'을 찾을 수 없습니다."}

        func_info = self.all_functions[func_name]
        return {
            "function": func_name,
            "file": func_info.file_path,
            "lines": f"{func_info.line_start}-{func_info.line_end}",
            "calls": func_info.calls,
            "called_by": func_info.called_by,
            "string_literals": func_info.string_literals,
            "impact_chain": self._get_impact_chain(func_name)
        }

    def generate_report(self, search_term: str = None) -> dict:
        """분석 리포트 생성"""
        report = {
            "summary": {
                "files_analyzed": len(self.file_analyzers),
                "total_functions": len(self.all_functions),
                "total_classes": len(self.all_classes)
            },
            "functions": {},
            "classes": {}
        }

        for name, info in self.all_functions.items():
            report["functions"][name] = {
                "file": info.file_path,
                "lines": f"{info.line_start}-{info.line_end}",
                "calls": info.calls,
                "called_by": info.called_by
            }

        if search_term:
            report["search_results"] = self.search_string(search_term)

        return report


def main():
    parser = argparse.ArgumentParser(description="AST 기반 코드 영향 분석 도구")
    parser.add_argument("--file", "-f", help="분석할 파일")
    parser.add_argument("--dir", "-d", help="분석할 디렉토리")
    parser.add_argument("--search", "-s", help="검색할 문자열 (예: .mp3)")
    parser.add_argument("--function", help="영향 분석할 함수명")
    parser.add_argument("--output", "-o", help="결과 저장 파일 (JSON)")

    args = parser.parse_args()

    if args.dir:
        analyzer = ImpactAnalyzer(args.dir)
        analyzer.analyze_directory()

        if args.search:
            print(f"\n[검색] '{args.search}' 포함된 문자열:\n")
            results = analyzer.search_string(args.search)
            for r in results:
                print(f"  파일: {r['file']}")
                print(f"  라인: {r['line']}")
                print(f"  값: {r['value']}")
                print(f"  함수: {r['function']}")
                if r['impact']:
                    print(f"  영향받는 함수: {' -> '.join(r['impact'])}")
                print()

        if args.function:
            print(f"\n[영향 분석] '{args.function}':\n")
            impact = analyzer.find_function_impacts(args.function)
            print(json.dumps(impact, indent=2, ensure_ascii=False))

        if args.output:
            report = analyzer.generate_report(args.search)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n[저장] {args.output}")

    elif args.file:
        analyzer = ImpactAnalyzer(os.path.dirname(args.file))
        result = analyzer.analyze_file(args.file)
        if result:
            print(f"\n[분석 결과] {args.file}\n")
            print(f"  함수: {list(result.functions.keys())}")
            print(f"  클래스: {list(result.classes.keys())}")
            print(f"  임포트: {result.imports}")

            if args.search:
                matches = [(l, v) for l, v in result.string_literals if args.search in v]
                if matches:
                    print(f"\n  '{args.search}' 검색 결과:")
                    for line, value in matches:
                        print(f"    라인 {line}: {value}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
