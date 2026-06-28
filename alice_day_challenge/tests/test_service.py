from __future__ import annotations

import random
import tempfile
from datetime import date
from pathlib import Path

from challenge_service import ChallengeService
from storage import JsonStateStorage


def make_service(seed: int = 1) -> ChallengeService:
    tmp = tempfile.TemporaryDirectory()
    storage = JsonStateStorage(Path(tmp.name) / "state.json")
    service = ChallengeService(storage=storage, rng=random.Random(seed))
    service._tmpdir = tmp  # keep alive for test lifetime
    return service


def alice_payload(text: str = "", new: bool = False, user_id: str = "u1") -> dict:
    return {
        "session": {"new": new, "session_id": "s1", "message_id": 1, "user_id": user_id},
        "request": {"original_utterance": text},
        "version": "1.0",
    }


def test_start_prompt():
    service = make_service()
    response = service.handle(alice_payload(new=True))
    assert "Выберите категорию" in response["response"]["text"]


def test_create_challenge_and_complete_updates_xp_level_and_streak(monkeypatch):
    service = make_service(seed=2)
    create = service.handle(alice_payload("интеллект", user_id="u2"))
    assert "Ваше испытание" in create["response"]["text"]

    monkeypatch.setattr(
        "challenge_service.date", type("D", (), {"today": staticmethod(lambda: date(2026, 6, 18))})
    )
    done1 = service.handle(alice_payload("выполнил", user_id="u2"))
    assert "Получаете" in done1["response"]["text"]
    assert any(xp in done1["response"]["text"] for xp in ["10", "20"])
    assert "уровень: 1" in done1["response"]["text"].lower()

    service.handle(alice_payload("учёба", user_id="u2"))
    monkeypatch.setattr(
        "challenge_service.date", type("D", (), {"today": staticmethod(lambda: date(2026, 6, 19))})
    )
    done2 = service.handle(alice_payload("выполнил", user_id="u2"))
    assert "Серия дней: 2" in done2["response"]["text"]


def test_random_category_selects_real_category():
    service = make_service(seed=3)
    response = service.handle(alice_payload("случайное", user_id="u3"))
    text = response["response"]["text"].lower()
    assert "ваше испытание" in text
    assert any(word in text for word in ["спорт", "интеллект", "учёба", "творчество", "учеба"])


def test_unknown_command_gives_helpful_message():
    service = make_service()
    response = service.handle(alice_payload("что-то непонятное", user_id="u4"))
    assert "не понял" in response["response"]["text"].lower()
