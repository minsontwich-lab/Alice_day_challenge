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


def alice_payload(
    text: str = "",
    new: bool = False,
    user_id: str = "u1",
) -> dict:
    return {
        "session": {
            "new": new,
            "session_id": "s1",
            "message_id": 1,
            "user_id": user_id,
        },
        "request": {"original_utterance": text},
        "version": "1.0",
    }


def test_start_prompt():
    service = make_service()

    response = service.handle(alice_payload(new=True))
    text = response["response"]["text"].lower()

    assert "испытание дня" in text
    assert "спорт" in text
    assert "интеллект" in text


def test_create_challenge_and_complete_updates_xp_level_and_streak(
    monkeypatch,
):
    service = make_service(seed=2)

    create = service.handle(alice_payload("интеллект", user_id="u2"))
    assert "испытание" in create["response"]["text"].lower()

    monkeypatch.setattr(
        "challenge_service.date",
        type("D", (), {"today": staticmethod(lambda: date(2026, 6, 18))}),
    )

    done1 = service.handle(alice_payload("выполнил", user_id="u2"))
    text1 = done1["response"]["text"].lower()
    assert "получаете" in text1
    assert "уровень" in text1
    assert "хотите ещё одно задание" in text1

    service.handle(alice_payload("учёба", user_id="u2"))

    monkeypatch.setattr(
        "challenge_service.date",
        type("D", (), {"today": staticmethod(lambda: date(2026, 6, 19))}),
    )

    done2 = service.handle(alice_payload("выполнил", user_id="u2"))
    assert "серия дней: 2" in done2["response"]["text"].lower()


def test_random_category_selects_real_category():
    service = make_service(seed=3)

    response = service.handle(alice_payload("случайное", user_id="u3"))
    text = response["response"]["text"].lower()

    assert "испытание" in text
    assert any(word in text for word in ["спорт", "интеллект", "учёба", "учеба", "творчество"])


def test_unknown_command_gives_helpful_message():
    service = make_service()

    response = service.handle(alice_payload("что-то непонятное", user_id="u4"))

    text = response["response"]["text"].lower()

    assert "скажите категорию" in text or "спорт" in text or "интеллект" in text


def test_about_skill():
    service = make_service()

    response = service.handle(alice_payload("расскажи про навык", user_id="u5"))
    text = response["response"]["text"].lower()

    assert "максимка" in text
    assert "python" in text
    assert "flask" in text
    assert "pytest" in text


def test_show_xp():
    service = make_service()

    response = service.handle(alice_payload("сколько у меня очков", user_id="u6"))
    text = response["response"]["text"].lower()

    assert "очков опыта" in text


def test_show_level():
    service = make_service()

    response = service.handle(alice_payload("какой у меня уровень", user_id="u7"))
    text = response["response"]["text"].lower()

    assert "уровень" in text


def test_show_streak():
    service = make_service()

    response = service.handle(alice_payload("какая у меня серия дней", user_id="u8"))
    text = response["response"]["text"].lower()

    assert "серия" in text


def test_progress():
    service = make_service()

    response = service.handle(alice_payload("мой прогресс", user_id="u9"))
    text = response["response"]["text"].lower()

    assert "xp" in text or "до следующего уровня" in text or "текущий уровень" in text


def test_force_quest():
    service = make_service()

    response = service.handle(alice_payload("мини квест", user_id="u10"))
    text = response["response"]["text"].lower()

    assert "квест" in text
    assert "1." in text
    assert "2." in text
    assert "3." in text


def test_force_quest_does_not_stick():
    service = make_service()

    quest = service.handle(alice_payload("мини квест", user_id="u11"))
    assert "квест" in quest["response"]["text"].lower()

    normal = service.handle(alice_payload("спорт", user_id="u11"))
    challenge = normal["user_state_update"]["challenge"]

    assert challenge["active"] is True


def test_days_since_last_completion(monkeypatch):
    service = make_service(seed=2)

    service.handle(alice_payload("спорт", user_id="u12"))
    monkeypatch.setattr(
        "challenge_service.date",
        type("D", (), {"today": staticmethod(lambda: date(2026, 6, 18))}),
    )
    service.handle(alice_payload("выполнил", user_id="u12"))

    monkeypatch.setattr(
        "challenge_service.date",
        type("D", (), {"today": staticmethod(lambda: date(2026, 6, 21))}),
    )
    response = service.handle(alice_payload("сколько дней прошло", user_id="u12"))
    assert "3" in response["response"]["text"]
