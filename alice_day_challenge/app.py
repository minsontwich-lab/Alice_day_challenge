from __future__ import annotations

from flask import Flask, jsonify, request

from challenge_service import ChallengeService
from storage import JsonStateStorage

app = Flask(__name__)

storage = JsonStateStorage("data/state.json")
service = ChallengeService(storage=storage)


@app.post("/alice")
def alice_webhook():
    payload = request.get_json(force=True, silent=False)
    response = service.handle(payload)
    return jsonify(response)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
