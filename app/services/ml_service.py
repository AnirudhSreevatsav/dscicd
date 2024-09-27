import asyncio
from venv import logger
import json
from flask import json
import requests
from app.constants.routes_constants import LOCAL_BASE_URL, ML_SERVICE_BASE_URL
from app.utils.response_util import api_response
from app.utils.mongo_util import mongo_util
from bson.objectid import ObjectId


from app.utils.mongo_util import mongo_util
from bson import ObjectId


class MLService:
    @staticmethod
    def save_chunk_to_stimulation_test(chunk):
        try:
            STIMULATION_TEST_COLLECTION = "stimulation_test"
            # Fetch the last document from the stimulation_test collection
            last_document = mongo_util.get_collection(STIMULATION_TEST_COLLECTION).find_one(
                sort=[('_id', -1)]
            )

            if last_document:
                # If a document exists, update it with the new chunk
                mongo_util.get_collection(STIMULATION_TEST_COLLECTION).update_one(
                    {'_id': last_document['_id']},
                    {'$push': {'chunks': chunk}}
                )
            else:
                # If no document exists, create a new one
                mongo_util.get_collection(STIMULATION_TEST_COLLECTION).insert_one({
                    'chunks': [chunk]
                })

            return True
        except Exception as e:
            logger.error(f"Error saving chunk to stimulation_test: {str(e)}")
            return False

    @staticmethod
    def analyse_on_call(data):
        transaction_id = data.get("transaction_id")
        transcript_chunk = data.get("transcript_chunk")
        current_question_index = data.get("current_question_index", -1)
        questions = data.get("questions", [])
        question_ids = data.get("question_ids", [])

        MLService.save_chunk_to_stimulation_test(transcript_chunk)

        question_index = MLService.detect_question(
            transcript_chunk, current_question_index, questions
        )
        highlighted_question = None
        if question_index != -1:
            highlighted_question = MLService.hightlight_question(
                transaction_id,
                question_ids[question_index],
                question_ids[current_question_index],
            )

        if current_question_index != -1:
            analysis = MLService.analyse_answer_new(
                transcript_chunk, questions[current_question_index]
            )
            if analysis:
                updated_analysis = MLService.update_anaylysis(
                    transaction_id, question_ids[current_question_index], analysis
                )
            return {
                "message": "Transcript chunk processed",
                "data": {
                    "current_question_index": current_question_index,
                    # "analysis_from_ml": str(analysis),
                    # "updated_analysis": str(updated_analysis),
                },
            }

        return {
            "message": "Transcript chunk processed",
            "data": {
                "current_question_index": current_question_index,
                },
        }

    @staticmethod
    async def stimulator(data, stop_event):
        transaction_id = data.get("transaction_id")
        stiumlator_id = ObjectId(data.get("stimulator_id"))
        buffer_time = data.get("buffer_time", 0)

        transcript = mongo_util.find_one("stimulation_test", {"_id": stiumlator_id})[
            "transcript"
        ]
        questions, question_ids = MLService.fetch_questions(transaction_id)
        current_question_index = -1

        # TODO: await initially for 30 seconds
        await asyncio.sleep(30 - 2 * buffer_time)

        while len(transcript) > 0:
            if stop_event.is_set():
                return api_response(
                    200, "Stimulator stopped", {"status": "interrupted"}
                )

            current_transcript = transcript[0]

            sleep_time = max(
                0,
                current_transcript["end_timestamp"]
                - current_transcript["start_timestamp"]
                - buffer_time,
            )
            await asyncio.sleep(sleep_time)

            question_index = MLService.detect_question(
                current_transcript["text"], current_question_index, questions
            )

            if question_index != -1 and question_index != current_question_index:
                MLService.hightlight_question(
                    transaction_id,
                    question_ids[question_index],
                    question_ids[current_question_index],
                )
                current_question_index = question_index
                transcript = transcript[1:]
                continue

            analysis = MLService.analyse_answer(
                current_transcript["text"], questions[current_question_index]
            )

            if analysis:
                MLService.update_anaylysis(
                    transaction_id, question_ids[current_question_index], analysis
                )
            else:
                print("no analysis detected")

            transcript = transcript[1:]

        return api_response(200, "Transcript processed", {"status": "completed"})

    @staticmethod
    def is_bot_active(bot_id):
        with requests.Session() as session:
            response = session.post(
                f"{LOCAL_BASE_URL}/api/bot/bot-status", json={"bot_id": bot_id}
            )
            result = response.json()
            return result.get("is_active", False)

    @staticmethod
    def hightlight_question(transaction_id, current_question_id, previous_question_id):
        try:
            url = f"{LOCAL_BASE_URL}/api/questions/update-question-data?transaction_id={transaction_id}"
            data = {
                "current_question_id": current_question_id,
                "question_id": previous_question_id,
                "is_answered": True
            }
            with requests.Session() as session:
                response = session.post(url, json=data)

            return response.json()

        except Exception as e:
            logger.error(f"Error highlighting question: {e}")
            return {"message": "Error highlighting question"}

    @staticmethod
    def update_anaylysis(transaction_id, question_id, analysis):
        data = {
            "question_id": question_id
        }
        if analysis.get("analysis_result"):
            average_score = analysis.get(
                "analysis_result").get("average_score", "0/0")
            average_score = average_score.split("/")
            if float(average_score[0]) < 75:
                data["analysis"] = analysis.get("analysis_result")

        if analysis.get("answer"):
            data["answer"] = analysis.get("answer")

        if analysis.get("answer_verbatim"):
            data["answer_verbatim"] = analysis.get("answer_verbatim")

        if analysis.get("objection"):
            data["objection"] = {
                "objection": analysis.get("objection"),
                "objection_explanation": analysis.get("objection_explanation")
            }

        try:
            url = f"{LOCAL_BASE_URL}/api/questions/update-question-data?transaction_id={transaction_id}"

            with requests.Session() as session:
                response = session.post(url, json=data)
            print("updated analysis ", response.json())
            return response.json()
        except Exception as e:
            logger.error(f"Error updating analysis: {e}")
            return {"message": "Error updating analysis"}

    @staticmethod
    def detect_question(transcript, current_question_index, questions):
        try:
            data = {
                "transcript": transcript,
                "current_question_index": current_question_index,
                "questions": questions,
            }

            print("data for detection", data)

            with requests.Session() as session:
                response = session.post(
                    f"{ML_SERVICE_BASE_URL}/api/on-call/question-detection",
                    json=data,
                )

                result = response.json()
                print("result of detection", result)
                index = result.get("data").get("question_index", -1)
                return index
        except Exception as e:
            logger.error(f"Error detecting question: {e}")
            return -1

    @staticmethod
    def create_follow_up(transcript, current_question):
        with requests.Session() as session:
            response = session.post(
                f"{ML_SERVICE_BASE_URL}/api/on-call/follow-up-detection",
                json={"transcript": transcript,
                      "current_question": current_question},
            )
            result = response.json()
            return result.get("follow_up", None)

    @staticmethod
    def analyse_answer_new(transcript, current_question):
        data = {
            "answer": transcript,
            "current_question": current_question,
        }


        try:
            with requests.Session() as session:
                response = session.post(
                    f"{ML_SERVICE_BASE_URL}/api/on-call/analyse-answer",
                    json=data,
                )
                result = response.json()
                print("result of analysis", result)
                return result.get("data", None)
        except Exception as e:
            logger.error(f"Error analysing answer: {e}")
            return None

    @staticmethod
    def analyse_answer(transcript, current_question):
        data = {
            "answer": transcript,
            "current_question": current_question,
        }
        try:
            with requests.Session() as session:
                response = session.post(
                    f"{ML_SERVICE_BASE_URL}/api/on-call/analyse-answer",
                    json=data,
                )
                result = response.json()
                return result.get("data").get("analysis_result", None)
        except Exception as e:
            logger.error(f"Error analysing answer: {e}")
            return None

    @staticmethod
    def fetch_questions(transaction_id):
        with requests.Session() as session:
            response = session.get(
                f"{LOCAL_BASE_URL}/api/questions/fetch-questions",
                params={"transaction_id": transaction_id},
            )
            result = response.json()
            questions = [item["question"]
                         for item in result["data"]["questions"]]
            question_ids = [item["question_id"]
                            for item in result["data"]["questions"]]
            return questions, question_ids


"""import aiohttp
from flask import request
from app.utils.logging import setup_logging

logger = setup_logging()


class MLService:

    @staticmethod
    async def analyse_transcript(company_id, bot_id, user_id, transcript):
        logger.info("Analyzing transcript")
        # Fetch questions and their IDs
        questions, question_ids = await MLService.fetch_questions(
            company_id, bot_id, user_id
        )

        logger.info(f"Questions fetched, length: {len(questions)}")ipt
        await asyncio.sleep(1)

        current_question_index = 0
        transcript_index = 0

        while transcript_index < len(transcript):
            current_transcript = transcript[transcript_index]
            transcript_index += 1

            logger.info(f"Current question is: {current_question_index}")

            index = await MLService.detect_question(
                current_transcript, current_question_index, questions
            )

            if index == -1:
                logger.info("No question detected")
                continue

            logger.info(f"Question detected at index: {index}")

            if index != current_question_index:
                # update to db - highlight the current question and answered to previous question
                await MLService.hightlight_question(
                    bot_id, question_ids[index], question_ids[current_question_index]
                )
                logger.info(f"Update db with {question_ids[index]}")
                current_question_index = index
            else:
                logger.info(f"No new question detected and index is {index}")

            if current_question_index == -1:
                continue

            await asyncio.sleep(1)

            analysis = await MLService.analyse_answer(
                transcript, questions[current_question_index]
            )

            if analysis:
                # if follow_up, then update to db
                await MLService.update_anaylysis(
                    bot_id, question_ids[current_question_index], analysis
                )
                logger.info(f"Update db with analysis")
            else:
                logger.info("No analysis detected")

            input("Press Enter to continue to the next iteration...")

    @staticmethod
    async def is_bot_active(bot_id):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/bot/bot-status", json={"bot_id": bot_id}
            ) as response:
                result = await response.json()
                return result.get("is_active", False)

    @staticmethod
    async def get_transcript(bot_id, char_limit=1500):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/bot/get-transcript", json={"bot_id": bot_id}
            ) as response:
                result = await response.json()
                combined_text = ""
                for transcript in reversed(result.get("transcript", [])):
                    combined_text = (
                        f"{transcript['speaker']}: {transcript['text']} {combined_text}"
                    )
                    if len(combined_text) > char_limit:
                        break
                return combined_text.strip()

    @staticmethod
    async def detect_question(transcript, current_question_index, questions):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://13.60.53.44/ml-copilot/api/on-call/question-detection",
                    # async with session.get("http://localhost:5000/api/on-call/question-detection",
                    json={
                        "transcript": transcript,
                        "current_question_index": current_question_index,
                        "questions": questions,
                    },
                ) as response:
                    result = await response.json()
                    return result.get("index", -1)
        except Exception as e:
            logger.error(f"Error detecting question: {e}")
            return -1

    @staticmethod
    async def hightlight_question(bot_id, current_question_id, previous_question_id):
        try:
            url = f"http://localhost:8000/api/questions/update-question-data/bot-id/{bot_id}"
            data = {
                "current_question_id": current_question_id,
                "question_id": previous_question_id,
                "is_answered": True,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
        except Exception as e:
            logger.error(f"Error highlighting question: {e}")

    @staticmethod
    async def create_follow_up(transcript, current_question):
        async with aiohttp.ClientSession() as session:
            # async with session.post("http://localhost:5000/api/on-call/follow-up-detection",
            async with session.post(
                "http://ml_service_container:5000/api/on-call/follow-up-detection",
                json={"transcript": transcript, "current_question": current_question},
            ) as response:
                result = await response.json()
                return result.get("follow_up", None)

    @staticmethod
    async def analyse_answer(transcript, current_question):
        try:
            async with aiohttp.ClientSession() as session:
                # async with session.post("http://localhost:5000/api/on-call/analyse-answer",
                async with session.post(
                    "http://ml_service_container:5000/api/on-call/analyse-answer",
                    json={"answer": transcript, "current_question": current_question},
                ) as response:
                    result = await response.json()
                    return result.get("analysis", None)
        except Exception as e:
            logger.error(f"Error analysing answer: {e}")
            return None

    @staticmethod
    async def update_follow_up(bot_id, question_id, follow_up):
        try:
            url = f"http://localhost:8000/api/questions/update-question-data/bot-id/{bot_id}"
            data = {"question_id": question_id, "follow_up": follow_up}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data):
                    pass
        except Exception as e:
            logger.error(f"Error updating follow up: {e}")

    @staticmethod
    async def update_anaylysis(bot_id, question_id, analysis):
        try:
            url = f"http://localhost:8000/api/questions/update-question-data/bot-id/{bot_id}"
            data = {"question_id": question_id, "analysis": analysis}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data):
                    pass

        except Exception as e:
            logger.error(f"Error updating analysis: {e}")

    @staticmethod
    async def fetch_questions(company_id, bot_id, user_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8000/api/questions/fetch-questions",
                params={"company_id": company_id, "bot_id": bot_id, "user_id": user_id},
            ) as response:
                result = await response.json()
                questions = [item["question"] for item in result["data"]["questions"]]
                question_ids = [
                    item["question_id"] for item in result["data"]["questions"]
                ]
                return questions, question_ids """
