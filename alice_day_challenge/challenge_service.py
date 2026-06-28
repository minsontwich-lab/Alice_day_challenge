from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from storage import JsonStateStorage

CATEGORY_ALIASES = {
    "спорт": "sport",
    "спортзание": "sport",
    "sport": "sport",
    "интеллект": "intellect",
    "ум": "intellect",
    "iq": "intellect",
    "intellect": "intellect",
    "учёба": "study",
    "учеба": "study",
    "study": "study",
    "обучение": "study",
    "творчество": "creativity",
    "креатив": "creativity",
    "creativity": "creativity",
    "случайное": "random",
    "рандом": "random",
    "random": "random",
}

LEVEL_NAMES = {
    1: "Новичок",
    2: "Более менее",
    3: "Уже крут",
    4: "Почти мастер",
    5: "Герой привычки",
}

CATEGORY_LABELS = {
    "sport": "спорт",
    "intellect": "интеллект",
    "study": "учёба",
    "creativity": "творчество",
    "random": "случайное",
}

CHALLENGES = {
    "sport": [
        "Сделайте 10 приседаний.",
        "Пройдите 1000 шагов в удобном темпе.",
        "Планка на 30 секунд.",
        "Сделайте 15 выпадов.",
    ],
    "intellect": [
        "За 10 минут придумайте 5 способов использовать карандаш, кроме письма.",
        "Назовите 7 слов, которые начинаются на букву К.",
        "Решите короткую логическую задачу: что тяжелее — килограмм ваты или килограмм железа?",
        "Вспомните 3 факта про любимую тему и объясните их вслух.",
    ],
    "study": [
        "Повторите 5 новых слов и составьте с ними 2 предложения.",
        "Прочитайте 2 абзаца и перескажите их своими словами.",
        "Решите один небольшой пример и объясните ход решения.",
        "Составьте план на 3 пункта для ближайшей учёбы.",
    ],
    "creativity": [
        "Придумайте мини-историю из 3 предложений про чайник, который мечтал стать космонавтом.",
        "Нарисуйте предмет неведущей рукой.",
        "Назовите 4 необычных применения обычной ложки.",
        "Придумайте 3 названия для фантастического фильма.",
    ],
}

HARDCORE_SUFFIX = "Режим хардкор: усложните задание и постарайтесь выполнить его идеально."
BONUS_SUFFIX = "Бонусное событие: за это испытание вы получаете двойной опыт!"
QUESTS = {
    "sport": [
        "Сделать 10 приседаний.",
        "Сделать 20 прыжков на месте.",
        "Сделать растяжку 30 секунд.",
    ],
    "intellect": [
        "Назвать 3 слова на букву А.",
        "Придумать 5 применений обычной скрепки.",
        "Решить короткую загадку для себя.",
    ],
    "study": [
        "Повторить 5 терминов.",
        "Сделать 1 мини-конспект.",
        "Сказать вслух 3 цели на завтра.",
    ],
    "creativity": [
        "Придумать героя.",
        "Придумать его проблему.",
        "Придумать неожиданную развязку.",
    ],
}


@dataclass
class ChallengeState:
    active: bool = False
    category: str | None = None
    prompt: str | None = None
    reward_xp: int = 10
    multiplier: int = 1
    mode: str = "normal"
    quest_steps: list[str] = field(default_factory=list)
    created_at: str | None = None


@dataclass
class UserProfile:
    xp: int = 0
    level: int = 1
    streak: int = 0
    last_completed_date: str | None = None
    challenge: ChallengeState = field(default_factory=ChallengeState)

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "UserProfile":
        if not data:
            return UserProfile()
        challenge_data = data.get("challenge") or {}
        return UserProfile(
            xp=int(data.get("xp", 0)),
            level=int(data.get("level", 1)),
            streak=int(data.get("streak", 0)),
            last_completed_date=data.get("last_completed_date"),
            challenge=ChallengeState(
                active=bool(challenge_data.get("active", False)),
                category=challenge_data.get("category"),
                prompt=challenge_data.get("prompt"),
                reward_xp=int(challenge_data.get("reward_xp", 10)),
                multiplier=int(challenge_data.get("multiplier", 1)),
                mode=challenge_data.get("mode", "normal"),
                quest_steps=list(challenge_data.get("quest_steps") or []),
                created_at=challenge_data.get("created_at"),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "xp": self.xp,
            "level": self.level,
            "streak": self.streak,
            "last_completed_date": self.last_completed_date,
            "challenge": asdict(self.challenge),
        }


class ChallengeService:
    def __init__(self, storage: JsonStateStorage, *, rng: random.Random | None = None):
        self.storage = storage
        self.rng = rng or random.Random()

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = payload.get("session", {})
        user_id = session.get("user_id", "anonymous")
        profile = UserProfile.from_dict(self.storage.get_user(user_id))

        request_obj = payload.get("request", {})
        original = self._normalize_text(request_obj.get("original_utterance", ""))
        command = self._detect_command(original)

        if session.get("new"):
            text = (
                "Привет! Это Испытание дня. "
                "Выберите категорию: спорт, интеллект, учёба, творчество или случайное."
            )
            return self._wrap_response(text, profile, user_id)

        if command == "help":
            text = (
                "Скажите категорию: спорт, интеллект, учёба, творчество или случайное. "
                "После выполнения скажите: выполнил."
            )
            return self._wrap_response(text, profile, user_id)

        if command == "complete":
            return self._complete_challenge(profile, user_id)

        if command in CATEGORY_ALIASES.values():
            return self._create_challenge(profile, user_id, command)

        if original:
            maybe_category = CATEGORY_ALIASES.get(original)
            if maybe_category:
                return self._create_challenge(profile, user_id, maybe_category)

        text = (
            "Не понял команду. Скажите категорию: "
            "спорт, интеллект, учёба, творчество "
            "или случайное."
        )
        return self._wrap_response(text, profile, user_id)

    def _create_challenge(
        self, profile: UserProfile, user_id: str, category: str
    ) -> dict[str, Any]:
        selected = category
        if category == "random":
            selected = self.rng.choice(["sport", "intellect", "study", "creativity"])

        is_quest = self.rng.random() < 0.20
        hardcore = self.rng.random() < 0.10
        bonus = not hardcore and self.rng.random() < 0.10

        base_prompt = ""
        quest_steps: list[str] = []

        if is_quest:
            quest_steps = list(self.rng.sample(QUESTS[selected], k=3))
            base_prompt = "Сегодняшний квест:\n" + "\n".join(
                f"{idx + 1}. {step}" for idx, step in enumerate(quest_steps)
            )
        else:
            base_prompt = self.rng.choice(CHALLENGES[selected])

        if hardcore:
            prompt = f"{base_prompt} {HARDCORE_SUFFIX}"
            multiplier = 2
            mode = "hardcore"
        elif bonus:
            prompt = f"{base_prompt} {BONUS_SUFFIX}"
            multiplier = 2
            mode = "bonus"
        else:
            prompt = base_prompt
            multiplier = 1
            mode = "normal"

        profile.challenge = ChallengeState(
            active=True,
            category=selected,
            prompt=prompt,
            reward_xp=10,
            multiplier=multiplier,
            mode=mode,
            quest_steps=quest_steps,
            created_at=datetime.now().isoformat(),
        )
        self.storage.save_user(user_id, profile.to_dict())

        category_label = CATEGORY_LABELS[selected]
        intro = f"Ваше испытание по категории «{category_label}»."
        if quest_steps:
            text = f"{intro} {prompt} Скажите «выполнил», когда закончите."
        else:
            text = f"{intro} {prompt} Скажите «выполнил», когда закончите."
        return self._wrap_response(text, profile, user_id)

    def _complete_challenge(self, profile: UserProfile, user_id: str) -> dict[str, Any]:
        if not profile.challenge.active:
            text = "Сначала выберите категорию и получите испытание."
            return self._wrap_response(text, profile, user_id)

        today = date.today()
        last_date = self._parse_date(profile.last_completed_date)
        new_streak = 1
        if last_date and (today - last_date).days == 1:
            new_streak = profile.streak + 1
        elif last_date and (today - last_date).days == 0:
            new_streak = profile.streak if profile.streak > 0 else 1

        gained = profile.challenge.reward_xp * profile.challenge.multiplier
        profile.xp += gained
        profile.level = self._calc_level(profile.xp)
        profile.streak = new_streak
        profile.last_completed_date = today.isoformat()
        profile.challenge = ChallengeState()

        self.storage.save_user(user_id, profile.to_dict())

        level_name = LEVEL_NAMES.get(profile.level, f"Уровень {profile.level}")
        text = (
            f"Отлично! Получаете {gained} очков опыта. "
            f"Ваш уровень: {profile.level} — {level_name}. "
            f"Серия дней: {profile.streak}."
        )
        return self._wrap_response(text, profile, user_id)

    def _wrap_response(self, text: str, profile: UserProfile, user_id: str) -> dict[str, Any]:
        return {
            "version": "1.0",
            "session": {"session_id": user_id, "message_id": 0, "user_id": user_id},
            "response": {"text": text, "end_session": False},
            "session_state": {"challenge": asdict(profile.challenge)},
            "user_state_update": profile.to_dict(),
        }

    def _detect_command(self, text: str) -> str:
        if not text:
            return ""
        if re.search(r"\b(выполнил|готово|сделал|сделала|готов|done)\b", text):
            return "complete"
        if re.search(r"\b(помощь|help|что делать)\b", text):
            return "help"
        for key, value in CATEGORY_ALIASES.items():
            if text == key or key in text:
                return value
        return ""

    @staticmethod
    def _normalize_text(text: str) -> str:
        return text.strip().lower().replace("ё", "е")

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    @staticmethod
    def _calc_level(xp: int) -> int:
        return max(1, xp // 50 + 1)
