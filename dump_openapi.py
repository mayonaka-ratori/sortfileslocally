import json
from server.main import app

with open("openapi.json", "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f)
