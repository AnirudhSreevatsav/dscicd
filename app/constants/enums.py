from enum import Enum

class RequestField(Enum):
    BODY = "body"
    PARAMS = "params"
    URL = "url"
    HEADERS = "headers"
