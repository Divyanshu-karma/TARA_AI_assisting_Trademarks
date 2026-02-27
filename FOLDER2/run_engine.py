# run_engine.py
import json
import logging
logging.basicConfig(level=logging.INFO)

from core.search_engine import conduct_tmep_704_02_search
from adapters.rapidapi_trademark import RapidApiTrademarkAdapter

app = {
    "application_id":  "123456789",
    "mark_text":       "ADAMS APPLE",
    "mark_type":       "standard_character",
    "goods_services":  [{"class": "029", "description": "Dried fruits"}],
    "event_trigger":   "first_review"
}

adapter = RapidApiTrademarkAdapter(
    rapidapi_key  = "98a0f5f309msh1b73f5dbf6c468dp116aa4jsna6736d27a876",
    status_filter = "all"
)

result = conduct_tmep_704_02_search(app, tess_adapter=adapter)
print(json.dumps(result, indent=2))