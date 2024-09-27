# base urls
ML_SERVICE_BASE_URL="http://13.60.53.44/ml-copilot"
LOCAL_BASE_URL="http://localhost:8000"

# bot routes constants
START_BOT = "/start-bot"
REMOVE_BOT = "/remove-bot"
GET_TRANSCRIPT = "/get-transcript"
UPLOAD_TRANSCRIPT = "/upload-transcript"
BOT_STATUS = "/bot-status"

# question routes constants
FETCH_QUESTIONS = "/fetch-questions"
UPDATE_QUESTIONS = "/update-question-data"
SHUFFLE_QUESTIONS = "/shuffle-questions"
ADD_QUESTION = "/add-question"
MASTER_FETCH_QUESTIONS = "/master/fetch-questions"
MASTER_UPDATE_QUESTIONS = "/master/update-questions"

# opportunities constants
FETCH_OPPORTUNITY_BY_MEETING_ID = "/fetch-opportunity-by-meeting-id"
# for fetching details of a single opportunity - pre-call
FETCH_OPPORTUNITY = "/fetch-opportunity"
# for scheduling a meeting for an opportunity - home - form
SCHEDULE_MEETING = "/schedule-meeting"
# for creating a new opportunity - home - form
CREATE_OPPORTUNITY = "/create-opportunity"
# for fetching opportunities by user id - home - form
FETCH_OPPORTUNITIES_BY_USER_ID = "/fetch-opportunities-by-user-id"
# for editing meeting details in an opportunity - pre-call
EDIT_MEETING_DETAILS = "/edit-meeting-details"
# for searching opportunities by name snippet
SEARCH_OPPORTUNITIES = "/search-opportunities"
# opportunity list for a user - home
DISCOVERY_DETAILS = "/discovery-details"
# for editing opportunity details
EDIT_OPPORTUNITY = "/edit-opportunity"
# add trasnscript to a particular meeting
ADD_TRANSCRIPT_TO_MEETING = "/add-transcript-to-meeting"

