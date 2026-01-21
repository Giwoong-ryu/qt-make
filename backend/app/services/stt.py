"""
Groq Whisper 음성 인식 서비스
"""
import logging
import os

from groq import Groq

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WhisperService:
    """Groq Whisper Large v3 Turbo STT 서비스"""

    # 자막 길이 설정 프리셋
    SUBTITLE_PRESETS = {
        "short": {  # QT 영상 최적화 (기본값)
            "max_chars_per_line": 8,
            "max_chars_per_subtitle": 16,
        },
        "long": {  # Netflix 한국어 기준
            "max_chars_per_line": 16,
            "max_chars_per_subtitle": 32,
        }
    }

    def __init__(self, subtitle_length: str = "short"):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = "whisper-large-v3-turbo"  # $0.04/hour

        # 자막 길이 설정 적용
        preset = self.SUBTITLE_PRESETS.get(subtitle_length, self.SUBTITLE_PRESETS["short"])
        self.MAX_CHARS_PER_LINE = preset["max_chars_per_line"]
        self.MAX_CHARS_PER_SUBTITLE = preset["max_chars_per_subtitle"]
        self.subtitle_length = subtitle_length

        logger.info(f"WhisperService initialized with subtitle_length={subtitle_length} "
                    f"(MAX_CHARS_PER_LINE={self.MAX_CHARS_PER_LINE}, "
                    f"MAX_CHARS_PER_SUBTITLE={self.MAX_CHARS_PER_SUBTITLE})")
    MIN_DURATION = 0.83  # 자막 최소 표시 시간 (초) - Netflix 기준 5/6초
    MAX_DURATION = 5.0  # 자막 최대 표시 시간 (초) - 더 짧게 (7초→5초)
    MIN_GAP_FRAMES = 2  # 자막 간 최소 간격 (프레임) @ 30fps = 약 67ms
    TARGET_CPS = 14  # 목표 CPS (Characters Per Second) - 더 여유롭게 (16→14)

    # 한국어 문장 종결 패턴 (우선순위 순)
    # Netflix/Kss 기준: 확실한 종결어미만 포함
    # 주의: 1글자 종결어미(가, 와, 봐, 줘)는 조사와 혼동되므로 제외!
    KOREAN_SENTENCE_ENDINGS = (
        # 격식체 종결어미 (가장 확실함)
        '습니다', '입니다', '됩니다', '합니다', '갑니다', '옵니다',
        '십시오', '십니다', '셨습니다', '었습니다', '았습니다',
        '겠습니다', '이었습니다', '셨어요', '였습니다',
        # 존댓말 종결어미
        '세요', '시죠', '시네요', '으세요', '으시죠',
        '으십시오', '하세요', '주세요', '보세요', '가세요', '오세요',
        # 해요체 종결어미
        '해요', '네요', '죠', '어요', '아요', '예요', '에요',
        '겠죠', '잖아요', '거예요', '건가요', '나요', '을까요',
        '했어요', '됐어요', '였어요', '이에요', '데요', '래요',
        '볼게요', '할게요', '줄게요', '갈게요', '올게요',
        '봐요', '해봐요', '가요', '와요', '줘요',
        # 반말 종결어미 (2글자 이상만! 1글자는 조사와 혼동)
        '했다', '됐다', '었다', '았다', '인다', '한다', '이다',
        '간다', '온다', '본다', '던다', '준다', '쓴다',
        '했어', '됐어', '었어', '았어', '거야', '이야',
        '해봐', '가봐', '와봐',  # 2글자 이상 반말
        '해줘', '가줘', '와줘',  # 2글자 이상 반말
        # 의문형 종결어미
        '습니까', '입니까', '는가', '은가', '냐', '나',
        '을까', '할까', '볼까', '갈까',
        '할래', '볼래', '갈래', '할까요', '볼까요',
        # 청유형/명령형
        '읍시다', '합시다', '하자', '해라', '가자', '보자',
        '하세요', '가세요', '오세요', '보세요',
        # 감탄형
        '구나', '군요', '구만', '더라', '던데요',
    )

    # 한국어 조사 (절대 끊으면 안 되는 패턴!)
    # 이 패턴으로 끝나면 문장이 불완전함
    KOREAN_PARTICLES = (
        # 주격/목적격 조사
        '이', '가', '을', '를', '은', '는',
        # 부사격 조사
        '에', '에서', '에게', '한테', '께',
        '로', '으로', '부터', '까지', '보다',
        '와', '과', '랑', '이랑', '하고',
        # 관형격/소유격
        '의',
        # 보조사
        '도', '만', '뿐', '밖에', '조차', '마저', '까지도',
        # 접속조사
        '나', '이나', '거나', '든지', '든가',
    )

    # 한국어 접속부사 (새 문장/절 시작 신호)
    # 이 단어들이 나오면 앞에서 끊어야 함
    # 참조: docs/KOREAN_SUBTITLE_SEGMENTATION_GUIDE.md (Netflix/Kss 기준)
    KOREAN_CONJUNCTIONS = (
        # 순접 (6개)
        '그리고', '그래서', '그러므로', '따라서', '그러니까', '그러니',
        # 역접 (6개)
        '그러나', '하지만', '그렇지만', '그런데', '다만', '반면에',
        # 전환 (5개)
        '그래도', '어쨌든', '아무튼', '한편', '그나저나',
        # 예시/부연 (5개)
        '예를 들어', '즉', '다시 말해', '특히', '물론',
        # 추가 (설교/교육 콘텐츠 특화)
        '또한', '게다가', '더구나', '뿐만아니라', '심지어',
        '왜냐하면', '그러면', '그렇다면', '만약', '만일', '오히려',
    )

    # 보조 용언 패턴 (분리하면 안 되는 복합 표현)
    # "할 수" 같은 의존명사 + 보조동사 구성
    AUXILIARY_VERB_PATTERNS = (
        '수 있',   # "할 수 있다", "볼 수 있어"
        '수 없',   # "할 수 없다", "볼 수 없어"
        '줄 알',   # "할 줄 알아", "할 줄 알았어"
        '줄 모',   # "할 줄 모르다"
        '게 되',   # "하게 되다", "보게 됐어"
        '게 하',   # "하게 하다", "보게 해"
        '지 않',   # "하지 않다", "가지 않아"
        '지 말',   # "하지 말아", "가지 마"
        '고 싶',   # "하고 싶다", "보고 싶어"
        '고 있',   # "하고 있다", "보고 있어"
    )

    def get_transcription(
        self,
        audio_path: str,
        language: str = "ko",
        initial_prompt: str | None = None
    ):
        """
        Whisper API 호출 → raw transcription 객체 반환
        (교정을 먼저 적용하기 위해 SRT 생성과 분리)

        Args:
            audio_path: 오디오 파일 경로
            language: 언어 코드 (ko, en, etc)
            initial_prompt: Whisper 힌트

        Returns:
            transcription: Groq Whisper API 응답 객체 (verbose_json)
        """
        try:
            logger.info(f"Transcribing audio: {audio_path}")

            # 기본 프롬프트 (교회/설교 관련 용어 + 성경 비유)
            default_prompt = (
                "묵상, 말씀, 은혜, 성경, 하나님, 예수님, 예수 그리스도, 성령, 기도, 찬양, 예배, 구원, 십자가, 부활, "
                "겨자씨, 씨앗, 씨뿌리는 자, 포도원, 무화과나무, 감람산, 올리브, 빛과 소금, 양과 목자, 천국, 비유, "
                "마가복음, 마태복음, 누가복음, 요한복음, 사도행전, 로마서, 고린도전서, 에베소서, 빌립보서, "
                "아멘, 할렐루야, 호산나, 마라나타, 주님, 그리스도, 메시아, 구세주, 복음, 제자, 사도, "
                "꽃동산, 교회, 성도, 형제, 자매, 목사님, 집사님, 권사님, 장로님"
            )
            prompt = initial_prompt if initial_prompt else default_prompt

            # 오디오 파일 읽기
            with open(audio_path, "rb") as audio_file:
                # Groq Whisper API 호출 (word 단위 타임스탬프)
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.model,
                    language=language,  # 한국어 최적화
                    response_format="verbose_json",  # 타임스탬프 포함
                    timestamp_granularities=["word"],  # 단어 단위
                    temperature=0.0,  # 일관성 최대화
                    prompt=prompt  # 도메인 특화 힌트
                )

            return transcription

        except Exception as e:
            logger.exception(f"Transcription failed: {e}")
            raise

    def create_srt_from_transcription(
        self,
        transcription,
        audio_path: str
    ) -> str:
        """
        교정된 transcription 객체 → SRT 파일 생성

        Args:
            transcription: Whisper API 응답 (교정 후)
            audio_path: 오디오 파일 경로 (SRT 저장 경로 결정용)

        Returns:
            srt_path: 생성된 SRT 파일 경로
        """
        try:
            # SRT 형식으로 변환 (적절한 길이로 분할)
            srt_content = self._convert_to_srt(transcription)

            # SRT 파일 저장 (확장자 관계없이 .srt로 변환)
            base_path = os.path.splitext(audio_path)[0]
            srt_path = f"{base_path}.srt"
            with open(srt_path, "w", encoding="utf-8") as srt_file:
                srt_file.write(srt_content)

            logger.info(f"SRT file created: {srt_path}")
            return srt_path

        except Exception as e:
            logger.exception(f"SRT creation failed: {e}")
            raise

    def transcribe_to_srt(
        self,
        audio_path: str,
        language: str = "ko",
        initial_prompt: str | None = None
    ) -> str:
        """
        MP3 → SRT 자막 파일 생성 (기존 호환성 유지)

        Args:
            audio_path: MP3 파일 경로
            language: 언어 코드 (ko, en, etc)
            initial_prompt: Whisper 힌트 (교회별 용어, 최대 224토큰)

        Returns:
            srt_path: 생성된 SRT 파일 경로
        """
        transcription = self.get_transcription(audio_path, language, initial_prompt)
        return self.create_srt_from_transcription(transcription, audio_path)

    def _convert_to_srt(self, transcription) -> str:
        """
        Groq verbose_json → SRT 형식 변환 (적절한 길이로 분할)

        - 최대 40자 (2줄 x 20자)
        - 최대 5초 표시
        - 자연스러운 끊김 (한국어 문장 종결 패턴 기준)
        - 자막 간 겹침 방지
        """
        srt_lines = []
        index = 1

        # words 속성이 있으면 word 단위, 없으면 segment 단위
        if hasattr(transcription, 'words') and transcription.words:
            subtitles = self._group_words_into_subtitles(transcription.words)
        else:
            # fallback: segment 기반
            subtitles = self._split_segments_into_subtitles(transcription.segments)

        # 불완전한 자막 병합 (조사로 끝나는 짧은 자막 합치기)
        subtitles = self._merge_incomplete_subtitles(subtitles)

        # 자막 겹침 방지: 다음 자막 시작 전에 현재 자막 종료
        subtitles = self._prevent_subtitle_overlap(subtitles)

        for subtitle in subtitles:
            start_time = self._format_timestamp(subtitle['start'])
            end_time = self._format_timestamp(subtitle['end'])
            text = subtitle['text']

            # 항상 2줄로 분리 (QT 영상 통일성)
            text = self._split_into_two_lines(text)

            srt_lines.append(f"{index}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text)
            srt_lines.append("")

            index += 1

        return "\n".join(srt_lines)

    def _merge_incomplete_subtitles(self, subtitles: list) -> list:
        """
        불완전한 자막 병합 (한국어 문법 후처리)

        병합 조건:
        1. 현재 자막이 조사로 끝남 (문장 불완전)
        2. 현재 자막이 너무 짧음 (3글자 이하)
        3. 병합 후에도 최대 길이/시간 초과하지 않음

        예시:
        - "오늘 우리가" + "예배드립니다" → "오늘 우리가 예배드립니다"
        - "씨보다 작은 것이로" + "돼 심긴 후에는" → "씨보다 작은 것이로 돼 심긴 후에는"
        """
        if not subtitles or len(subtitles) < 2:
            return subtitles

        merged = []
        i = 0

        while i < len(subtitles):
            current = subtitles[i].copy()

            # 마지막 자막이면 그냥 추가
            if i >= len(subtitles) - 1:
                merged.append(current)
                break

            # 현재 자막 분석
            current_text = current['text'].strip()
            words = current_text.split()
            last_word = words[-1] if words else ""

            # 병합 필요 여부 판단
            should_merge = False

            # 조건 1: 조사로 끝나면 불완전
            for particle in self.KOREAN_PARTICLES:
                if last_word.endswith(particle) and len(last_word) <= len(particle) + 3:
                    should_merge = True
                    break

            # 조건 2: 너무 짧은 자막 (5글자 이하)
            if len(current_text.replace(' ', '')) <= 5:
                should_merge = True

            # 조건 3: 연결어미로 끝나면 불완전
            for connecting in self.KOREAN_CONNECTING_ENDINGS:
                if current_text.endswith(connecting):
                    should_merge = True
                    break

            if should_merge:
                next_sub = subtitles[i + 1]
                merged_text = current_text + " " + next_sub['text'].strip()
                merged_duration = next_sub['end'] - current['start']

                # 병합 가능 조건: 길이/시간 초과 안 함
                if (len(merged_text) <= self.MAX_CHARS_PER_SUBTITLE * 1.5 and
                    merged_duration <= self.MAX_DURATION * 1.2):
                    # 병합 실행
                    current['text'] = merged_text
                    current['end'] = next_sub['end']
                    merged.append(current)
                    i += 2  # 다음 자막 스킵
                    continue

            # 병합 안 하고 그대로 추가
            merged.append(current)
            i += 1

        return merged

    def _prevent_subtitle_overlap(self, subtitles: list) -> list:
        """
        자막 간 겹침 방지 + 최소/최대 표시 시간 적용

        Netflix/YouTube 표준:
        - 자막 간 최소 2프레임(67ms @ 30fps) 간격
        - 최소 표시 시간: 1.5초 (깜빡임 방지)
        - 최대 표시 시간: 7초
        """
        if not subtitles:
            return subtitles

        MIN_GAP = self.MIN_GAP_FRAMES / 30.0  # 2프레임 @ 30fps = 약 67ms

        for i in range(len(subtitles)):
            # 1. 최소 표시 시간 보장 (깜빡임 방지)
            duration = subtitles[i]['end'] - subtitles[i]['start']
            if duration < self.MIN_DURATION:
                subtitles[i]['end'] = subtitles[i]['start'] + self.MIN_DURATION

            # 2. 최대 표시 시간 제한
            duration = subtitles[i]['end'] - subtitles[i]['start']
            if duration > self.MAX_DURATION:
                subtitles[i]['end'] = subtitles[i]['start'] + self.MAX_DURATION

            # 3. 다음 자막과 겹침 방지
            if i < len(subtitles) - 1:
                next_start = subtitles[i + 1]['start']

                # 겹치거나 간격이 부족하면 현재 자막 종료 시간 조정
                if subtitles[i]['end'] >= next_start - MIN_GAP:
                    # 다음 자막 시작 전에 종료 (최소 간격 유지)
                    subtitles[i]['end'] = next_start - MIN_GAP

                    # 종료 시간이 시작 시간보다 빠르면 최소 0.5초 유지
                    if subtitles[i]['end'] <= subtitles[i]['start']:
                        subtitles[i]['end'] = subtitles[i]['start'] + 0.5

        return subtitles

    def _group_words_into_subtitles(self, words: list) -> list:
        """
        단어들을 적절한 길이의 자막 블록으로 그룹화

        Netflix/Kss 기준 분리 규칙:
        1. 접속부사 앞에서 끊기 (하지만, 그러나, 그래서 등)
        2. 종결어미 뒤에서 끊기 (습니다, 해요 등)
        3. 글자수/시간 초과 시 끊기
        4. 연결어미는 끊지 않기 (해서, 니까, 지만 등)
        """
        subtitles = []
        current_words = []
        current_text = ""
        current_start = None

        for word_data in words:
            word = word_data.get('word', '').strip()
            start = word_data.get('start', 0)
            end = word_data.get('end', 0)

            if not word:
                continue

            # 접속부사 앞에서 끊기 체크 (Netflix 스타일)
            # "앉으십니다 하지만" → "앉으십니다" / "하지만..."
            if current_text and self._should_break_before_word(word):
                # 현재 블록 저장 (접속부사 전까지)
                if current_words:
                    subtitles.append({
                        'start': current_start,
                        'end': current_words[-1].get('end', end),
                        'text': current_text
                    })
                # 접속부사부터 새 블록 시작
                current_words = [word_data]
                current_text = word
                current_start = start
                continue

            # 첫 단어
            if current_start is None:
                current_start = start

            # 새 단어 추가 시 길이/시간 체크
            new_text = (current_text + " " + word).strip() if current_text else word
            duration = end - current_start

            # 한국어 문장 종결 패턴 체크
            is_sentence_end = self._is_korean_sentence_end(new_text)

            # 조건: 글자수 초과 또는 시간 초과 또는 문장 끝
            should_break = (
                len(new_text) > self.MAX_CHARS_PER_SUBTITLE or
                duration > self.MAX_DURATION or
                is_sentence_end
            )

            if should_break and current_text:
                # 문장 끝이면 현재 단어까지 포함해서 저장
                if is_sentence_end and len(new_text) <= self.MAX_CHARS_PER_SUBTITLE:
                    current_words.append(word_data)
                    current_text = new_text

                # 현재 블록 저장
                subtitles.append({
                    'start': current_start,
                    'end': current_words[-1].get('end', end),
                    'text': current_text
                })

                # 새 블록 시작
                if is_sentence_end and len(new_text) <= self.MAX_CHARS_PER_SUBTITLE:
                    # 문장 끝으로 끊었으면 새 블록은 빈 상태로
                    current_words = []
                    current_text = ""
                    current_start = None
                else:
                    # 글자수/시간 초과로 끊었으면 현재 단어부터 새 블록
                    current_words = [word_data]
                    current_text = word
                    current_start = start
            else:
                current_words.append(word_data)
                current_text = new_text

        # 마지막 블록
        if current_text:
            subtitles.append({
                'start': current_start,
                'end': current_words[-1].get('end', 0) if current_words else 0,
                'text': current_text
            })

        return subtitles

    # 한국어 연결어미 (끊으면 안 되는 패턴)
    # Kss 라이브러리 기준: 이 패턴으로 끝나면 문장이 이어짐
    # 주의: 너무 일반적인 패턴('고', '는', '은' 등)은 오탐 방지를 위해 제외
    KOREAN_CONNECTING_ENDINGS = (
        # 원인/이유 연결어미 (2글자 이상만)
        '해서', '에서', '어서', '아서', '라서', '이라서',
        '니까', '으니까', '니깐', '으니깐',
        '때문에', '탓에', '덕분에',
        # 대조/양보 연결어미
        '지만', '는데', '은데', '더니', '던데',
        '는데도', '은데도', '지만은',
        # 동시/나열 연결어미 (2글자 이상)
        '면서', '으면서', '으며', '고서', '고는',
        # 목적/의도 연결어미
        '려고', '으려고', '으러', '려면', '으려면',
        # 조건/가정 연결어미 (2글자 이상)
        '으면', '거든', '다면', '라면', '이라면',
        # 정도/비교 연결어미
        '도록', '게끔', '듯이', '처럼', '만큼', '대로',
        # 인용 연결어미
        '다고', '라고', '냐고', '자고',
        '다는', '라는', '다니', '라니',
        # 보조적 연결어미 (2글자 이상)
        '아서', '어서', '여서', '아도', '어도', '여도',
        '하게', '하지',  # "~하게 되다", "~하지 않다"
    )

    def _is_korean_sentence_end(self, text: str) -> bool:
        """
        한국어 문장 종결 패턴 체크 (Netflix/Kss 기준)

        핵심 원칙:
        1. 문장부호 → 무조건 끊음
        2. 조사로 끝남 → 절대 끊지 않음 (문장 불완전)
        3. 연결어미 → 끊지 않음 (문장이 이어짐)
        4. 종결어미 → 끊음 (문장 완료)
        5. 애매한 경우 → 끊지 않음 (안전하게)
        """
        if not text:
            return False

        text = text.strip()
        if not text:
            return False

        # 1. 문장부호로 끝나는 경우 - 무조건 끊음
        if text[-1] in '.!?。':
            return True

        # 2. 마지막 단어 추출
        words = text.split()
        if not words:
            return False

        last_word = words[-1]

        # 3. 조사로 끝나는 경우 - 절대 끊지 않음 (최우선!)
        # 예: "오늘 우리가" → 끊으면 안 됨
        # 긴 조사부터 체크 (예: "에서"가 "서"보다 먼저)
        for particle in sorted(self.KOREAN_PARTICLES, key=len, reverse=True):
            if last_word.endswith(particle):
                # 단어가 조사만으로 이루어진 경우도 체크
                # 예: "가", "를", "에서" 등
                return False

        # 4. 연결어미로 끝나는 경우 - 절대 끊지 않음
        # 긴 패턴부터 체크 (정확도 향상)
        for connecting in sorted(self.KOREAN_CONNECTING_ENDINGS, key=len, reverse=True):
            if text.endswith(connecting):
                return False

        # 5. 종결어미로 끝나는 경우 - 끊음
        # 긴 패턴부터 체크 (정확도 향상)
        for ending in sorted(self.KOREAN_SENTENCE_ENDINGS, key=len, reverse=True):
            if last_word.endswith(ending):
                # 최소 길이 검증: 종결어미보다 단어가 길어야 함
                if len(last_word) > len(ending) or len(last_word) >= 2:
                    return True

        # 6. 애매한 경우 - 끊지 않음 (안전하게)
        return False

    def _should_break_before_word(self, word: str) -> bool:
        """
        특정 단어 앞에서 끊어야 하는지 체크 (Netflix 스타일)

        접속부사로 시작하는 경우:
        - "하지만", "그러나", "그래서" 등은 새 문장 시작
        - 이 단어들 앞에서 끊어야 자연스러움
        """
        if not word:
            return False

        word = word.strip()

        # 접속부사로 시작하면 앞에서 끊어야 함
        for conj in self.KOREAN_CONJUNCTIONS:
            if word.startswith(conj):
                return True

        return False

    def _split_segments_into_subtitles(self, segments: list) -> list:
        """세그먼트를 적절한 길이로 분할 (fallback)"""
        subtitles = []

        for segment in segments:
            text = segment['text'].strip()
            start = segment['start']
            end = segment['end']
            duration = end - start

            # 짧은 세그먼트는 그대로
            if len(text) <= self.MAX_CHARS_PER_SUBTITLE and duration <= self.MAX_DURATION:
                subtitles.append({'start': start, 'end': end, 'text': text})
                continue

            # 긴 세그먼트는 분할
            chunks = self._split_text_naturally(text)
            chunk_duration = duration / len(chunks) if chunks else duration

            for i, chunk in enumerate(chunks):
                chunk_start = start + (i * chunk_duration)
                chunk_end = start + ((i + 1) * chunk_duration)
                subtitles.append({
                    'start': chunk_start,
                    'end': chunk_end,
                    'text': chunk
                })

        # 타이밍 겹침 보정: 다음 자막 시작시간이 이전 자막 종료시간보다 빠르면 조정
        subtitles = self._fix_overlapping_timestamps(subtitles)

        return subtitles

    def _fix_overlapping_timestamps(self, subtitles: list) -> list:
        """
        타이밍 겹침 보정: 자막 간 시간이 겹치면 조정

        원인: Whisper STT가 반환하는 segment 타이밍이 가끔 겹침
        해결: 다음 자막 시작시간 = max(다음 자막 시작, 이전 자막 종료 + gap)
        """
        if not subtitles:
            return subtitles

        MIN_GAP = 0.05  # 최소 50ms 간격

        for i in range(1, len(subtitles)):
            prev_end = subtitles[i-1]['end']
            curr_start = subtitles[i]['start']

            # 겹침 발견: 이전 자막 종료 > 현재 자막 시작
            if prev_end > curr_start - MIN_GAP:
                # 이전 자막 종료시간 직후로 현재 자막 시작시간 조정
                new_start = prev_end + MIN_GAP
                old_duration = subtitles[i]['end'] - subtitles[i]['start']

                subtitles[i]['start'] = new_start
                # 종료 시간도 같은 duration 유지하도록 조정 (단, 다음 자막과 안 겹치게)
                subtitles[i]['end'] = new_start + old_duration

                logger.debug(
                    f"[TimingFix] Subtitle {i}: adjusted start {curr_start:.2f}s → {new_start:.2f}s"
                )

        return subtitles

    def _split_text_naturally(self, text: str) -> list:
        """텍스트를 자연스럽게 분할 (문장부호, 조사 기준)"""
        import re

        # 문장 부호로 먼저 분할 (마침표, 느낌표, 물음표)
        # 핵심: 마침표 뒤에서 무조건 끊음 (최소 길이 제한 없음!)
        sentences = re.split(r'([.!?。])', text)
        chunks = []
        current = ""

        for i, part in enumerate(sentences):
            if not part:
                continue

            # 문장부호는 이전 텍스트에 붙임
            if part in '.!?。':
                current += part
                # 마침표 뒤에서 무조건 분할 (최소 길이 제한 제거!)
                if current.strip():
                    chunks.append(current.strip())
                    current = ""
            else:
                if len(current + part) > self.MAX_CHARS_PER_SUBTITLE:
                    if current:
                        chunks.append(current.strip())
                    # 여전히 긴 경우 강제 분할 (한국어 단어 중간 분리 방지!)
                    while len(part) > self.MAX_CHARS_PER_SUBTITLE:
                        # 1순위: 공백 기준 분할
                        split_pos = part.rfind(' ', 0, self.MAX_CHARS_PER_SUBTITLE)
                        if split_pos == -1:
                            # 2순위: 조사로 끝나지 않는 위치 찾기
                            split_pos = self._find_safe_split_position(part, self.MAX_CHARS_PER_SUBTITLE)
                        chunks.append(part[:split_pos].strip())
                        part = part[split_pos:].strip()
                    current = part
                else:
                    current += part

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [text]

    def _find_safe_split_position(self, text: str, max_pos: int) -> int:
        """
        한국어 단어 중간에서 끊기지 않는 안전한 분할 위치 찾기

        규칙:
        1. 조사로 끝나는 위치는 피함 (문장 불완전)
        2. 종결어미로 끝나는 위치 우선
        3. 없으면 max_pos 반환 (불가피한 경우)
        """
        # 뒤에서부터 검사 (최대한 길게 유지)
        for pos in range(min(max_pos, len(text)), max(max_pos - 6, 1), -1):
            candidate = text[:pos]

            # 조사로 끝나면 SKIP (문장 불완전)
            is_particle = False
            for particle in self.KOREAN_PARTICLES:
                if candidate.endswith(particle) and len(candidate) > len(particle):
                    # 단, "때", "데" 등은 조사가 아닐 수 있음
                    # 길이가 1인 조사만 검사
                    if len(particle) == 1:
                        is_particle = True
                        break

            if not is_particle:
                # 종결어미로 끝나면 최고! (우선 선택)
                for ending in self.KOREAN_SENTENCE_ENDINGS:
                    if candidate.endswith(ending):
                        return pos

                # 종결어미 아니더라도 조사 아니면 OK
                return pos

        # 안전한 위치 못 찾으면 max_pos 반환
        return max_pos

    def _split_into_two_lines(self, text: str) -> str:
        """
        텍스트를 2줄로 분리 (한국어 특성 고려)

        규칙:
        1. 각 줄 최대 16자 (Netflix 한국어 기준)
        2. 짧은 텍스트(16자 이하)는 1줄 유지
        3. 조사/어미가 분리되지 않도록 공백 기준 분할
        4. 공백 없는 한국어는 중간에서 분리
        """
        logger.info(f"[DEBUG 2줄 분할] 입력: '{text[:30]}...'")  # 🔴 디버그 로그
        text = text.strip()

        # 16자 이하면 1줄로 유지 (불필요한 줄바꿈 방지)
        if len(text) <= self.MAX_CHARS_PER_LINE:
            return text

        # 공백이 없는 경우 (붙여쓴 한국어)
        if ' ' not in text:
            # 중간에서 분리하되 최대 16자 유지
            mid = min(len(text) // 2, self.MAX_CHARS_PER_LINE)
            line1 = text[:mid].strip()
            line2 = text[mid:].strip()

            # 2줄 모두 16자 이내인지 확인
            if len(line2) > self.MAX_CHARS_PER_LINE:
                line2 = line2[:self.MAX_CHARS_PER_LINE]

            return line1 + "\n" + line2

        # 공백 있는 경우 - 문맥 기반 분할 (한국어 종결어미 우선)
        words = text.split(' ')

        if len(words) == 1:
            return text

        # 최적의 분할 지점 찾기 (우선순위 순서)
        # 1순위: 종결어미 뒤 + 16자 이내
        # 2순위: 균등 분할 + 보조 용언 회피
        best_split = len(words) // 2
        best_diff = float('inf')
        best_score = -1  # 높을수록 좋음

        for i in range(1, len(words)):
            # 보조 용언 패턴 검사 (분리하면 안 되는 지점)
            should_skip = False
            if i < len(words):
                # 분할 지점 앞뒤 2단어 확인
                context = ' '.join(words[max(0, i-1):min(len(words), i+2)])
                for pattern in self.AUXILIARY_VERB_PATTERNS:
                    if pattern in context:
                        # 패턴이 분할 지점에 걸치는지 확인
                        left = ' '.join(words[:i])
                        right = ' '.join(words[i:])
                        # 패턴이 완전히 한쪽에 있으면 OK, 걸치면 SKIP
                        if pattern in left or pattern in right:
                            pass  # 완전히 한쪽에 있음 - OK
                        else:
                            should_skip = True  # 패턴이 걸침 - SKIP
                            break

            if should_skip:
                continue

            line1 = ' '.join(words[:i])
            line2 = ' '.join(words[i:])

            # 두 줄 모두 16자 이내인 경우만 고려
            if len(line1) <= self.MAX_CHARS_PER_LINE and len(line2) <= self.MAX_CHARS_PER_LINE:
                # 점수 계산 (높을수록 좋음)
                score = 0

                # 1순위: line2가 종결어미로 끝나는가? (가장 중요!)
                # → 한국어 자연스러운 패턴: 두 번째 줄이 완전한 문장으로 끝남
                # 예: "말씀으로" / "좋은 아침입니다."
                line2_words = line2.split()
                if line2_words:
                    last_word_line2 = line2_words[-1]
                    # 구두점 제거 후 종결어미 검사 (쉼표, 마침표 등이 종결어미 뒤에 붙는 경우 대응)
                    last_word_clean = last_word_line2.rstrip(',.!?…')
                    for ending in self.KOREAN_SENTENCE_ENDINGS:
                        if last_word_clean.endswith(ending) and len(last_word_clean) > len(ending):
                            logger.info(f"[DEBUG] line2 종결어미 발견: '{line2}' (점수 +100)")
                            score += 100  # 종결어미 발견 시 큰 보너스
                            break

                # 2순위: 균등 분할 (글자수 차이가 적을수록 좋음)
                diff = abs(len(line1) - len(line2))
                score += (20 - diff)  # 차이가 0이면 +20, 10이면 +10

                # 최고 점수 갱신
                if score > best_score or (score == best_score and diff < best_diff):
                    best_score = score
                    best_diff = diff
                    best_split = i

        line1 = ' '.join(words[:best_split])
        line2 = ' '.join(words[best_split:])

        # 둘 다 내용이 있어야 함
        if not line1 or not line2:
            mid = len(text) // 2
            return text[:mid].strip() + "\n" + text[mid:].strip()

        logger.info(f"[DEBUG 분할 결과] line1: '{line1}' / line2: '{line2}'")  # 🔴
        return line1 + "\n" + line2

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """
        초 → SRT 타임스탬프 변환

        Args:
            seconds: 3.5

        Returns:
            "00:00:03,500"
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# 싱글톤 인스턴스
_whisper_service: WhisperService | None = None


def get_whisper_service(subtitle_length: str = "short") -> WhisperService:
    """
    WhisperService 팩토리 함수

    Args:
        subtitle_length: 자막 길이 설정 ("short" 또는 "long")
            - "short": 8자/줄, 16자/블록 (QT 영상 최적화)
            - "long": 16자/줄, 32자/블록 (Netflix 한국어 기준)
    """
    # subtitle_length에 따라 매번 새 인스턴스 생성 (설정이 다를 수 있으므로)
    return WhisperService(subtitle_length=subtitle_length)
