from flask import Blueprint, request, jsonify
from app.services.s3_service import S3Service
import os

s3_controller = Blueprint("s3_controller", __name__)

"""API endpoint to handle PDF uploads to S3."""


@s3_controller.route("/upload-pdfs", methods=["POST"])
def upload_pdfs_endpoint():
    company_id = request.form.get("company_id")
    pdf_files = request.files.getlist("pdf_files")  # Get a list of files

    if not company_id or not pdf_files:
        return jsonify({"error": "Missing required parameters"}), 400
    s3_urls = []
    for pdf_file in pdf_files:
        # Save each file temporarily
        pdf_path = f"{pdf_file.filename}"
        pdf_file.save(pdf_path)

        # Upload the file to S3
        s3_url = S3Service.upload_pdf_to_s3(pdf_path, company_id)
        s3_urls.append(s3_url)

        # Clean up the temporary file
        os.remove(pdf_path)

    return jsonify({"s3_urls": s3_urls}), 200
