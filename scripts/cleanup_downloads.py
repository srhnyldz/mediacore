#!/usr/bin/env python3
"""Paylasilan download klasorunde suresi dolan task dizinlerini temizler."""

from __future__ import annotations

import json
import sys

from app.services.cleanup_service import cleanup_expired_downloads


def main() -> int:
    result = cleanup_expired_downloads()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
