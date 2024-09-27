# app/background_tasks.py

import threading
import requests

from app.constants.routes_constants import LOCAL_BASE_URL


def start_analysis_thread(company_id, bot_id, user_id):
    def analyze_transcript_in_background():
        try:
            requests.get(
                f"{LOCAL_BASE_URL}/api/ml/analyse-transcript",
                params={"company_id": company_id,
                        "bot_id": bot_id, "user_id": user_id},
            )
        except Exception as e:
            print(f"Error analyzing transcript: {e}")

    thread = threading.Thread(target=analyze_transcript_in_background)
    thread.start()
