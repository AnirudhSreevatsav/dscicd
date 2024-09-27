import asyncio
import time
from venv import logger
import json
from flask import json
import requests
from app.constants.constants import COMPANY_COLLECTION
from app.constants.routes_constants import LOCAL_BASE_URL, ML_SERVICE_BASE_URL
from app.utils.response_util import api_response
from app.utils.mongo_util import mongo_util
from bson.objectid import ObjectId


from app.utils.mongo_util import mongo_util
from bson import ObjectId


class OnCallService:

    @staticmethod
    def on_call_simulation(data):

        opportunity_id = data.get("opportunity_id")
        meeting_id = data.get("meeting_id")
        transaction_id = data.get("transaction_id")

        questions, question_ids = OnCallService.fetch_questions(transaction_id)

        # print("questions_initial", questions)
        # print("question_ids_initial", question_ids)

        current_question_index = -1

        current_chunk = "-"

        loop_count = 0


        while True:
            time.sleep(5)
            transcript_chunk_list = OnCallService.fetch_transcript(
                opportunity_id, meeting_id)
            if transcript_chunk_list:
                transcript_chunks = transcript_chunk_list.get("transcript")
                if transcript_chunks is None:
                    continue
                if len(transcript_chunks) > 0:
                    transcript_chunk = transcript_chunks[-1].get("text")
                    print("transcript_chunk", transcript_chunk)
                    if transcript_chunk == current_chunk:
                        if loop_count > 35:
                            break
                        else:
                            loop_count += 1
                            continue
                    else:
                        loop_count = 0

                    current_chunk = transcript_chunk


            question_index = OnCallService.process_transcript_chunk(
                current_chunk, transaction_id, current_question_index, questions, question_ids
            )

            if question_index != -1 and question_index != current_question_index:
                current_question_index = question_index

        print("On call simulation completed")
        return api_response(status_code=200, message="On call simulation completed")

    @staticmethod
    def process_transcript_chunk(transcript_chunk, transaction_id, current_question_index, questions, question_ids):
        try:
            
            question_index = OnCallService.detect_question(
                transcript_chunk, current_question_index, questions
            )
            print("question_indexs", question_index, current_question_index)
            if question_index != -1:
                OnCallService.hightlight_question(
                    transaction_id,
                    question_ids[question_index],
                    question_ids[current_question_index],
                )

            if current_question_index != -1:
                analysis = OnCallService.analyse_answer(
                    transcript_chunk, questions[current_question_index]
                )
                if analysis:
                    OnCallService.update_anaylysis(
                        transaction_id, question_ids[current_question_index], analysis
                    )

            return question_index
        except Exception as e:
            logger.error(f"Error processing transcript chunk: {e}")
            return -1

    @staticmethod
    def fetch_transcript(opportunity_id, meeting_id):

        try:
            url = f"{LOCAL_BASE_URL}/api/bot/get-transcript"
            data = {
                "bot_id": "anything as is_dev",
                "is_dev": True,
                "opportunity_id": opportunity_id,
                "meeting_id": meeting_id

            }
            with requests.Session() as session:
                response = session.post(url, json=data)
                result = response.json()

                return result.get("data", None)

        except Exception as e:
            print(f"Error fetching transcript: {e}")
            return None

    @staticmethod
    def hightlight_question(transaction_id, current_question_id, previous_question_id):
        try:
            url = f"{LOCAL_BASE_URL}/api/questions/update-question-data?transaction_id={transaction_id}"
            data = {
                "current_question_id": current_question_id,
                "question_id": previous_question_id,
                "is_answered": True
            }

            print("highlighting question", data)
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
            follow_up_threshold = OnCallService.follow_up_threshold()
            print("is_follow_up", float(average_score[0]) <= float(follow_up_threshold))
            if float(average_score[0]) <= float(follow_up_threshold):
                data["analysis"] = analysis.get("analysis_result")

        if analysis.get("answer"):
            print("answer received")
            data["answer"] = analysis.get("answer")

        if analysis.get("answer_verbatim"):
            print("answer_verbatim received")
            data["answer_verbatim"] = analysis.get("answer_verbatim")

        if analysis.get("objection_problem"):
            print("objection_problem received")
            data["objection"] = {
                "objection_problem": analysis.get("objection_problem"),
                "objection_solution": analysis.get("objection_solution")
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
    def follow_up_threshold():
        try:
            # TODO: change to company id
            followup_details = mongo_util.find_one(
            COMPANY_COLLECTION,
            {"_id": ObjectId("66ee749b9bcf800de32bae80")},
            {"configuration.follow_up_threshold": 1}  
            )
            if followup_details:
                follow_up_threshold = followup_details.get("configuration", {}).get("follow_up_threshold")
                if follow_up_threshold is not None:
                    return (follow_up_threshold)
            
            return 100
        except Exception as e:
            logger.error(f"Error finding followup: {e}")
            return 100

    @staticmethod
    def detect_question(transcript, current_question_index, questions):
        try:
            data = {
                "transcript": transcript,
                "current_question_index": current_question_index,
                "questions": questions,
            }



            with requests.Session() as session:
                response = session.post(
                    f"{ML_SERVICE_BASE_URL}/api/on-call/question-detection",
                    json=data,
                )


                result = response.json()
                index = result.get("data").get("question_index", -1)
                return index
        except Exception as e:
            print(f"Error detecting question: {e}")
            return -1

    @staticmethod
    def analyse_answer(transcript, current_question):
        data = {
            "answer": transcript,
            "current_question": current_question,
        }

        print("analysing the answer for question", current_question)

        try:
            with requests.Session() as session:
                response = session.post(
                    f"{ML_SERVICE_BASE_URL}/api/on-call/analyse-answer",
                    json=data,
                )
                result = response.json()
                return result.get("data", None)
        except Exception as e:
            logger.error(f"Error analysing answer: {e}")
            return None

    @staticmethod
    def fetch_questions(transaction_id):
        try:
            with requests.Session() as session:
                response = session.get(
                f"{LOCAL_BASE_URL}/api/questions/fetch-questions",
                params={"transaction_id": transaction_id},
            )
            result = response.json()

            question_object = result.get("data").get("questions")
            non_answered_questions = [question for question in question_object if not question.get("is_answered")]
            # non_answered_questions = question_object
            questions = [item["question"] for item in non_answered_questions]
            question_ids = [item["question_id"]
                                for item in non_answered_questions]
            return questions, question_ids
        except Exception as e:
            logger.error(f"Error fetching questions: {e}")
            return [], []
