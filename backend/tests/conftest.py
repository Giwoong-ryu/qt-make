"""
pytest 설정 및 fixture
"""
import warnings

# gotrue 관련 deprecation warning 무시
warnings.filterwarnings("ignore", message=".*gotrue.*deprecated.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pytest
