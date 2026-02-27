"""
Sentinel.DS 전역 설정
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent

# DB 경로
DB_PATH = PROJECT_ROOT / "data" / "sentinel.db"

# API 키 (환경변수에서 로드)
LAW_API_KEY = os.getenv("LAW_API_KEY", "")
FSS_API_KEY  = os.getenv("FSS_API_KEY") or "4b992ee15d8514a53aeb93a15169b8b4"

# 레이아웃 설정
LAYOUT = {
    "topbar_height": 68,
    "sidebar_width": 70,
    "sidebar_gap": 8,
}
