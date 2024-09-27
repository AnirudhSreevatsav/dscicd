from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Sensitive constants
RECALL_API_KEY = os.getenv('RECALL_API_KEY')
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

#AWS credentials
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
AWS_REGION_NAME = os.getenv('AWS_REGION_NAME')

# Socket constants
SOCKET_SECRET_KEY = os.getenv('SOCKET_SECRET_KEY')