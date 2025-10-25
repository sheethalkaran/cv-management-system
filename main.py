"""
AI-Integrated CV Management Software
Main application entry point for processing WhatsApp resumes
"""

import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from whatsapp_handler import WhatsAppHandler
from extract import CVExtractor
from google_sheets import GoogleSheetsManager
from utils import validate_env_variables, setup_logging
import os
import base64
import json

# Handle base64 encoded credentials for deployment
if os.getenv('GOOGLE_CREDENTIALS_BASE64'):
    os.makedirs('credentials', exist_ok=True)
    creds_data = base64.b64decode(os.getenv('GOOGLE_CREDENTIALS_BASE64'))
    with open('credentials/google-service-account.json', 'wb') as f:
        f.write(creds_data)

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app for webhook
app = Flask(__name__)

# Validate required environment variables
REQUIRED_ENV_VARS = [
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_WHATSAPP_NUMBER',
    'OPENAI_API_KEY',
    'GOOGLE_SHEET_ID',
    'GOOGLE_CREDENTIALS_PATH'
]

validate_env_variables(REQUIRED_ENV_VARS)

# Initialize components
whatsapp_handler = WhatsAppHandler(
    account_sid=os.getenv('TWILIO_ACCOUNT_SID'),
    auth_token=os.getenv('TWILIO_AUTH_TOKEN'),
    whatsapp_number=os.getenv('TWILIO_WHATSAPP_NUMBER')
)

cv_extractor = CVExtractor(
    openai_api_key=os.getenv('OPENAI_API_KEY')
)

sheets_manager = GoogleSheetsManager(
    credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH'),
    sheet_id=os.getenv('GOOGLE_SHEET_ID')
)


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint to receive WhatsApp messages from Twilio
    """
    try:
        logger.info("Received webhook request")
        
        # Parse incoming message
        message_data = whatsapp_handler.parse_incoming_message(request.form)
        
        if not message_data:
            logger.warning("No valid message data received")
            return jsonify({"status": "no_data"}), 200
        
        logger.info(f"Processing message from {message_data['from']}")
        
        # Check if message contains media (resume file)
        if message_data.get('media_url'):
            logger.info(f"Media file detected: {message_data['media_content_type']}")
            
            # Download the file
            file_path = whatsapp_handler.download_media(
                media_url=message_data['media_url'],
                media_content_type=message_data['media_content_type']
            )
            
            if not file_path:
                logger.error("Failed to download media file")
                whatsapp_handler.send_message(
                    to_number=message_data['from'],
                    message="Sorry, I couldn't download your resume. Please try again."
                )
                return jsonify({"status": "download_failed"}), 200
            
            logger.info(f"File downloaded successfully: {file_path}")
            
            # Extract text from file
            extracted_text = cv_extractor.extract_text_from_file(file_path)
            
            if not extracted_text:
                logger.error("Failed to extract text from file")
                whatsapp_handler.send_message(
                    to_number=message_data['from'],
                    message="Sorry, I couldn't read your resume. Please ensure it's a PDF or DOCX file."
                )
                return jsonify({"status": "extraction_failed"}), 200
            
            logger.info(f"Text extracted, length: {len(extracted_text)} characters")
            
            # Extract structured data using AI
            cv_data = cv_extractor.extract_cv_data(extracted_text)
            
            if not cv_data:
                logger.error("Failed to extract structured data from CV")
                whatsapp_handler.send_message(
                    to_number=message_data['from'],
                    message="Sorry, I couldn't extract information from your resume. Please ensure it contains clear details."
                )
                return jsonify({"status": "parsing_failed"}), 200
            
            logger.info(f"CV data extracted: {cv_data.get('name', 'Unknown')}")
            
            # Add metadata
            cv_data['phone_number'] = message_data['from']
            cv_data['submission_timestamp'] = message_data['timestamp']
            
            # Save to Google Sheets
            row_number = sheets_manager.append_cv_data(cv_data)
            
            if row_number:
                logger.info(f"Data saved to Google Sheets at row {row_number}")
                
                # Send confirmation message
                confirmation_msg = f"""✅ Resume received successfully!
                
Name: {cv_data.get('name', 'N/A')}
Email: {cv_data.get('email', 'N/A')}
Experience: {cv_data.get('experience', 'N/A')}

Your application has been recorded. We'll contact you soon!"""
                
                whatsapp_handler.send_message(
                    to_number=message_data['from'],
                    message=confirmation_msg
                )
            else:
                logger.error("Failed to save data to Google Sheets")
                whatsapp_handler.send_message(
                    to_number=message_data['from'],
                    message="Your resume was processed but there was an issue saving it. Please contact support."
                )
            
            # Cleanup downloaded file
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        
        else:
            # Text-only message (no resume)
            logger.info("Text-only message received")
            whatsapp_handler.send_message(
                to_number=message_data['from'],
                message="👋 Welcome to CV Management System!\n\nPlease send your resume as a PDF or DOCX file to get started."
            )
        
        return jsonify({"status": "success"}), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "CV Management System",
        "version": "1.0.0"
    }), 200


if __name__ == '__main__':
    logger.info("Starting CV Management System")
    logger.info(f"Webhook will be available at: http://localhost:5000/webhook")
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )