from app.utils.s3_client import get_s3_client
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from app.constants.config import AWS_S3_BUCKET_NAME, AWS_REGION_NAME
import os

class S3Service:
    def upload_pdf_to_s3(pdf_path, company_id):
        """Uploads the PDF to the S3 bucket."""
        s3 = get_s3_client()
        bucket_name = AWS_S3_BUCKET_NAME
        file_name = os.path.basename(pdf_path)
        s3_key = f"{company_id}/{file_name}"

        try:
            # Upload the file to S3
            s3.upload_file(pdf_path, bucket_name, s3_key)
            s3_url = f"https://{bucket_name}.s3.{AWS_REGION_NAME}.amazonaws.com/{s3_key}"
            return s3_url
        except (NoCredentialsError, PartialCredentialsError) as e:
            print(f"Credentials error: {e}")
            return {'error': 'S3 credentials error'}
        except Exception as e:
            print(f"Failed to upload PDF to S3: {e}")
            return {'error': str(e)}
