import time
import requests
from bson import ObjectId

from app.constants.constants import COMPANY_COLLECTION
from app.constants.routes_constants import LOCAL_BASE_URL, ML_SERVICE_BASE_URL
from app.utils.mongo_util import mongo_util
from app.utils.response_util import api_response

from app.utils.logging import setup_logging
import concurrent.futures

logger = setup_logging()

class PostCallService:

    @staticmethod
    def post_call_analysis(data):
        opportunity_id = data.get("opportunity_id")
        meeting_id = data.get("meeting_id")

        # Fetch opportunity details and transcript concurrently
        opportunity_details = PostCallService.fetch_opportunity_details_async(opportunity_id)
        # transcript_future = PostCallService.fetch_transcript_async(opportunity_id, meeting_id)

        if opportunity_details.get("status_code") < 200 or opportunity_details.get("status_code") >= 300:
            return api_response(opportunity_details.get("status_code"), opportunity_details.get("message"))

        # Process transcript 
        transaction_id = opportunity_details.get("data").get("transactional_discovery_question_id")
        transcript = PostCallService.fetch_transcript(opportunity_id, meeting_id)

        if not transcript:
            transcript = ""
        else:
            transcript_list = transcript.get("transcript", [])
            transcript = " ".join(text.get("text", "") for text in transcript_list or [])


        seller_company_id = opportunity_details.get("data").get("seller_company_id")
        company_configuration = PostCallService.fetch_company_configuration(seller_company_id)
        framework = None
        lead_qualify_threshold = 0        
        if company_configuration is not None:
            framework = company_configuration.get("sales_framework").get("framework_text")
            lead_qualify_threshold = float(company_configuration.get("lead_qualify_threshold"))

        # Prepare data for concurrent API calls
        transaction_id = opportunity_details.get("data").get("transactional_discovery_question_id")
        questions_object_list = opportunity_details.get("data").get("transactional_discovery_questions")["questions"]
        questions_without_id = [question.get("question") for question in questions_object_list]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(PostCallService.framework_analysis_async, transcript, framework),
                executor.submit(PostCallService.fetch_blockers_async, transcript, questions_without_id),
                executor.submit(PostCallService.fetch_actionable_items_async, transcript),
                executor.submit(PostCallService.fetch_recap_async, transcript)
            ]
            concurrent.futures.wait(futures)

        sales_framework_analysis = futures[0].result().get("data")
        blockers = futures[1].result().get("data")
        actionable_items = futures[2].result().get("data").get("action_items")
        recap = futures[3].result().get("data").get("summary")

        #from the sales framework, get the max score and append it to the opportunity
        if sales_framework_analysis is not None and futures[0].result().get("data") is not None:
            sales_framework_scores = [sales_framework_analysis.get("total_score") for meeting in opportunity_details.get("data").get("meetings") if meeting.get("sales_framework_analysis") and meeting.get("sales_framework_analysis").get("total_score") ]
            sales_framework_scores.append(futures[0].result().get("data").get("total_score"))
            total_sales_score = sales_framework_analysis.get("max_score") 

            if len(sales_framework_scores) > 0:
                average_sales_score = round(sum(sales_framework_scores) / len(sales_framework_scores), 1)
                is_lead_qualified = False  
                if average_sales_score >= lead_qualify_threshold:
                    is_lead_qualified = True
                PostCallService.update_sales_score(opportunity_id, average_sales_score, total_sales_score, is_lead_qualified)


        questions_with_id = []
        for question in questions_object_list:
            questions_with_id.append({
                "question_id": question.get("question_id"),
                "question": question.get("question"),
                "is_answered": question.get("is_answered"),
                "question_type": question.get("question_type", {})
            })
        questions_without_id = []
        for question in questions_object_list:
            questions_without_id.append(question.get("question"))

        if blockers is not None:
            blockers_list = blockers.get("blocker_list")
            for blocker in blockers_list:
                question_index = blocker.get("question_index")
                if question_index == -1:
                    continue
                question_id = questions_with_id[question_index].get("question_id")
                blocker.pop("question_index")
                PostCallService.update_blockers_to_question(transaction_id, question_id, blocker)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(PostCallService.update_sales_framework, opportunity_id, meeting_id, sales_framework_analysis, opportunity_details),
                executor.submit(PostCallService.update_actionable_items, opportunity_id, actionable_items),
                executor.submit(PostCallService.update_recap, opportunity_id, recap),
                executor.submit(PostCallService.update_unanswered_questions, transaction_id, questions_object_list)
            ]
            concurrent.futures.wait(futures)

        opportunity_details = PostCallService.fetch_opportunity_details_by_meeting_id(opportunity_id, meeting_id)
        return api_response(200, "Success", PostCallService.convert_objectid_to_str(opportunity_details.get("data")))

    @staticmethod
    def fetch_opportunity_details_async(opportunity_id):
        try:
            url = f"{LOCAL_BASE_URL}/api/opportunity/fetch-opportunity?opportunity_id={opportunity_id}"
            response = requests.get(url)
            return response.json()
        except Exception as e:
            logger.error("Error in fetching opportunity details", e)
            return None
        
    @staticmethod
    def fetch_transcript_async(opportunity_id, meeting_id):
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
            logger.error(f"Error fetching transcript: {e}")
            return None
        
    @staticmethod
    def fetch_company_configuration(seller_company_id):
        try: 
            company = mongo_util.find_one(COMPANY_COLLECTION, {"_id": ObjectId(seller_company_id)})
            configuration = company.get("configuration")
            return configuration
        except Exception as e:
            logger.error("Error in fetching company configuration", e)
            return None
    
    @staticmethod
    def framework_analysis_async(transcript, framework):
        try:
            ml_url = f"{ML_SERVICE_BASE_URL}/api/post-call/sales-framework-analysis"
            data = {
                "transcript": transcript,
                "framework": framework
            }
            response = requests.post(ml_url, json=data)
            return response.json()
        except Exception as e:
            logger.error("Error in framework analysis", e)
            return None
    
    @staticmethod
    def fetch_blockers_async(transcript, questions_without_id):
        try:
            data = {
                "transcript": transcript,
                "questions_list": questions_without_id
            }
            update_url = f"{ML_SERVICE_BASE_URL}/api/post-call/blockers"
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(update_url, headers=headers, json=data)
            return response.json()
        except Exception as e:
            logger.error("Error in fetching blockers", e)
            return None
    
    @staticmethod
    def fetch_actionable_items_async(transcript):
        try:
            actionable_items_url = f"{ML_SERVICE_BASE_URL}/api/post-call/action-items"
            data = {
                "transcript": transcript
            }
            response = requests.post(actionable_items_url, json=data)
            return response.json()
        except Exception as e:
            logger.error("Error in fetching actionable items", e)
            return None
        
    @staticmethod
    def fetch_recap_async(transcript):
        try:
            recap_url = f"{ML_SERVICE_BASE_URL}/api/post-call/summary"
            data = {
                "transcript": transcript
            }
            response = requests.post(recap_url, json=data)
            return response.json()
        except Exception as e:
            logger.error("Error in fetching recap", e)
            return None
    
    @staticmethod
    def update_sales_framework(opportunity_id, meeting_id, sales_framework_analysis, opportunity_details):
        if sales_framework_analysis is None:
            return

        data = {
            "meeting_details": {
                "sales_framework_analysis": sales_framework_analysis
            }
        }
        
        try:
            update_url = f"{LOCAL_BASE_URL}/api/opportunity/edit-meeting-details?opportunity_id={opportunity_id}&meeting_id={meeting_id}"
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(update_url, headers=headers, json=data)

            return response.json()
        except Exception as e:
            logger.error("Error in updating meeting details", e)
            return None
    
    @staticmethod
    def update_blockers_to_question(transaction_id, question_id, blockers):
        try:
            data = {
                "question_id": question_id,
                "blockers": blockers
            }
            update_url = f"{LOCAL_BASE_URL}/api/questions/update-question-data?transaction_id={transaction_id}"
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(update_url, headers=headers, json=data)
            return response.json()
        except Exception as e:
            logger.error("Error in updating blockers to question", e)
            return None
        
            
    @staticmethod
    def update_actionable_items(opportunity_id, actionable_items):
        data = {
            "opportunity_details": {
                "actionable_items": actionable_items
            }
        }
        try:
            update_url = f"{LOCAL_BASE_URL}/api/opportunity/edit-opportunity?opportunity_id={opportunity_id}"
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(update_url, headers=headers, json=data)
            return response.json()
        except Exception as e:
            logger.error("Error in updating actionable items to opportunity", e)
            return None
    
    @staticmethod
    def update_recap(opportunity_id, recap):
        data = {
            "opportunity_details": {
                "recap": recap
            }
        }
        try:
            update_url = f"{LOCAL_BASE_URL}/api/opportunity/edit-opportunity?opportunity_id={opportunity_id}"
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(update_url, headers=headers, json=data)
            return response.json()
        except Exception as e:
            logger.error("Error in updating recap to opportunity", e)
            return None
    
    @staticmethod
    def update_unanswered_questions(transaction_id, questions_object_list):
        for question in questions_object_list:
            if not question["is_answered"]:
                question_type = question.get("question_type", {})
                question_type["previous discussion"] = ""
                PostCallService.update_question_type(transaction_id, question["question_id"], question_type)
    
    @staticmethod
    def update_question_type(transaction_id, question_id, question_type):
        try:
            data = {
                "question_id": question_id,
                "question_type": question_type,
                "current_question_id":""
            }
            update_url = f"{LOCAL_BASE_URL}/api/questions/update-question-data?transaction_id={transaction_id}"
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(update_url, headers=headers, json=data)
            return response.json()
        except Exception as e:
            logger.error("Error in updating question type", e)
            return None
    
    @staticmethod
    def fetch_opportunity_details_by_meeting_id(opportunity_id, meeting_id):
        try:
            opportunity_details_url = f"{LOCAL_BASE_URL}/api/opportunity/fetch-opportunity-by-meeting-id?opportunity_id={opportunity_id}&meeting_id={meeting_id}"
            response = requests.get(opportunity_details_url)
            return response.json()
        except Exception as e:
            logger.error("Error in fetching opportunity details", e)
            return None
    
    @staticmethod
    def convert_objectid_to_str(document):
        if isinstance(document, dict):
            for key, value in document.items():
                if isinstance(value, ObjectId):
                    document[key] = str(value)
        return document

    @staticmethod
    def update_sales_score(opportunity_id, average_sales_score,total_sales_score, is_lead_qualified):
        try:
            update_url = f"{LOCAL_BASE_URL}/api/opportunity/edit-opportunity?opportunity_id={opportunity_id}"
            data = {
                "opportunity_details": {
                    "average_sales_score": average_sales_score,
                    "total_sales_score": total_sales_score,
                    "is_lead_qualified": is_lead_qualified
                }
            }
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(update_url, headers=headers, json=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error in updating average score: {str(e)}")
            return None
        
    @staticmethod
    def update_total_sales_score(opportunity_id, total_sales_score):
        try:
            update_url = f"{LOCAL_BASE_URL}/api/opportunity/edit-opportunity?opportunity_id={opportunity_id}"
            data = {
                "opportunity_details": {
                    "total_sales_score": total_sales_score
                }
            }
            headers = {
                "Content-Type": "application/json"
            }
            response = requests.post(update_url, headers=headers, json=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error in updating average score: {str(e)}")
            return None

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
            logger.error(f"Error fetching transcript: {e}")
            return None
         
    @staticmethod
    def update_lead_qualification(data):
        try:
            opportunity_id = data.get('opportunity_id')
            is_lead_qualified = data.get('is_lead_qualified')

            if opportunity_id is None or is_lead_qualified is None:
                return api_response(status_code=400, message="Missing required parameters")

            update_url = f"{LOCAL_BASE_URL}/api/opportunity/edit-opportunity?opportunity_id={opportunity_id}"
            update_data = {
                "opportunity_details": {
                    "is_lead_qualified": is_lead_qualified
                }
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(update_url, headers=headers, json=update_data)
            
            if response.status_code == 200:
                return api_response(status_code=200, message="Lead qualification updated successfully", data=response.json())
            else:
                return api_response(status_code=response.status_code, message="Failed to update lead qualification")

        except Exception as e:
            logger.error(f"Error in updating lead qualification: {str(e)}")
            return api_response(status_code=500, message="Internal server error")
