"""環境変数からシークレットを取得するユーティリティ"""
import os
from typing import Optional


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key, default)
