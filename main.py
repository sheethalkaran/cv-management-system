"""
AI-Integrated CV Management Software
Main application entry point with enhanced validation
"""

import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from whatsapp_handler import WhatsAppHandler
from extract import CVExtractor
from google_sheets import GoogleSheetsManager
from utils import validate_env_variables, setup_logging
import base64

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


def validate_cv_data(cv_data):
    """
    Validates if CV data meets minimum requirements
    
    MINIMUM REQUIREMENTS:
    - Name is mandatory
    - At least ONE of: Email OR Phone must be present
    
    Args:
        cv_data: Extracted CV information dictionary
    
    Returns:
        tuple: (is_valid: bool, missing_fields: list, has_optional_missing: bool)
    """
    # Check mandatory fields
    has_name = cv_data.get('name') and cv_data['name'] != 'N/A' and len(cv_data['name'].strip()) > 0
    has_email = cv_data.get('email') and cv_data['email'] != 'N/A' and '@' in cv_data['email']
    has_phone = cv_data.get('phone') and cv_data['phone'] != 'N/A' and len(cv_data['phone'].strip()) >= 10
    
    # Check optional fields
    optional_fields = ['skills', 'experience', 'education', 'location']
    missing_optional = [field for field in optional_fields 
                       if not cv_data.get(field) or cv_data[field] == 'N/A']
    
    # Determine validity
    if not has_name:
        return False, ['name'], False
    
    if not has_email and not has_phone:
        return False, ['email or phone'], False
    
    # Valid but check if optional fields are missing
    has_optional_missing = len(missing_optional) > 0
    
    return True, [], has_optional_missing


def process_cv_data(cv_data, message_data):
    """
    Common function to process and store CV data with enhanced validation
    and duplicate detection
    
    Args:
        cv_data: Extracted CV information
        message_data: WhatsApp message metadata
    
    Returns:
        bool: Success status
    """
    try:
        # Validate CV data
        is_valid, missing_fields, has_optional_missing = validate_cv_data(cv_data)
        
        if not is_valid:
            logger.warning(f"CV data validation failed. Missing: {missing_fields}")
            return False
        
        # Add metadata
        cv_data['phone_number'] = message_data['from']
        cv_data['submission_timestamp'] = message_data['timestamp']
        
        # Save to Google Sheets (returns tuple: (row_number, is_update))
        result = sheets_manager.append_cv_data(cv_data)
        
        if result:
            row_number, is_update = result
            logger.info(f"Data {'updated' if is_update else 'saved'} to Google Sheets at row {row_number}")
            
            # Build confirmation message based on update status
            if is_update:
                # This is an update - show "Updated" message
                if has_optional_missing:
                    confirmation_msg = f"""🔄 *Resume Updated Successfully!*

Your previous information has been replaced with:

Name: {cv_data.get('name', 'N/A')}
Email: {cv_data.get('email', 'N/A')}
Phone: {cv_data.get('phone', 'N/A')}"""
                    
                    # Add present optional fields
                    if cv_data.get('skills') and cv_data['skills'] != 'N/A':
                        confirmation_msg += f"\nSkills: {cv_data.get('skills')}"
                    if cv_data.get('experience') and cv_data['experience'] != 'N/A':
                        confirmation_msg += f"\nExperience: {cv_data.get('experience')}"
                    if cv_data.get('education') and cv_data['education'] != 'N/A':
                        confirmation_msg += f"\nEducation: {cv_data.get('education')}"
                    
                    confirmation_msg += """\n\n📝 For a complete profile, please provide your remaining details or send your full resume as a PDF/DOCX file.

We'll contact you soon!"""
                else:
                    # Complete data received - update
                    confirmation_msg = f"""🔄 *Resume Updated Successfully!*

Your previous information has been replaced with:

Name: {cv_data.get('name', 'N/A')}
Email: {cv_data.get('email', 'N/A')}
Phone: {cv_data.get('phone', 'N/A')}
Skills: {cv_data.get('skills', 'N/A')}
Experience: {cv_data.get('experience', 'N/A')}
Education: {cv_data.get('education', 'N/A')}

Your updated application has been recorded. We'll contact you soon!"""
            else:
                # This is a new submission
                if has_optional_missing:
                    # Partial data received - ask for remaining details
                    confirmation_msg = f"""✅ *Resume Received Successfully!*

Name: {cv_data.get('name', 'N/A')}
Email: {cv_data.get('email', 'N/A')}
Phone: {cv_data.get('phone', 'N/A')}"""
                    
                    # Add present optional fields
                    if cv_data.get('skills') and cv_data['skills'] != 'N/A':
                        confirmation_msg += f"\nSkills: {cv_data.get('skills')}"
                    if cv_data.get('experience') and cv_data['experience'] != 'N/A':
                        confirmation_msg += f"\nExperience: {cv_data.get('experience')}"
                    if cv_data.get('education') and cv_data['education'] != 'N/A':
                        confirmation_msg += f"\nEducation: {cv_data.get('education')}"
                    
                    confirmation_msg += """\n\n📝 For a complete profile, please provide your remaining details or send your full resume as a PDF/DOCX file.

We'll contact you soon!"""
                else:
                    # Complete data received
                    confirmation_msg = f"""✅ *Resume Received Successfully!*

Name: {cv_data.get('name', 'N/A')}
Email: {cv_data.get('email', 'N/A')}
Phone: {cv_data.get('phone', 'N/A')}
Skills: {cv_data.get('skills', 'N/A')}
Experience: {cv_data.get('experience', 'N/A')}
Education: {cv_data.get('education', 'N/A')}

Your application has been recorded. We'll contact you soon!"""
            
            whatsapp_handler.send_message(
                to_number=message_data['from'],
                message=confirmation_msg
            )
            return True
        else:
            logger.error("Failed to save data to Google Sheets")
            whatsapp_handler.send_message(
                to_number=message_data['from'],
                message="Your resume was processed but there was an issue saving it. Please contact support."
            )
            return False
            
    except Exception as e:
        logger.error(f"Error processing CV data: {str(e)}")
        return False

def extract_simple_cv_data(text):
    """
    Rule-based extraction for simple text messages
    
    Logic:
    - Look for "Label: Value" format (e.g., "Name: John Doe")
    - Line with @ = Email
    - Line with Phone: or digits = Phone
    - Line with multiple commas = Skills
    - Other lines = Experience/Education
    
    Args:
        text: Raw text message
        
    Returns:
        dict: Extracted CV data or None
    """
    import re
    
    try:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        cv_data = {
            'name': 'N/A',
            'email': 'N/A',
            'phone': 'N/A',
            'skills': 'N/A',
            'experience': 'N/A',
            'education': 'N/A',
            'location': 'N/A'
        }
        
        used_lines = set()
        
        # Process each line looking for "Label: Value" format
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check for "Name:" pattern
            if line_lower.startswith('name:'):
                cv_data['name'] = line.split(':', 1)[1].strip().title()
                used_lines.add(i)
                logger.info(f"Extracted name: {cv_data['name']}")
                continue
            
            # Check for "Email:" pattern OR line with @
            if line_lower.startswith('email:'):
                email_value = line.split(':', 1)[1].strip()
                if '@' in email_value:
                    cv_data['email'] = email_value
                    used_lines.add(i)
                    logger.info(f"Extracted email: {cv_data['email']}")
                continue
            elif '@' in line and cv_data['email'] == 'N/A':
                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
                if email_match:
                    cv_data['email'] = email_match.group(0)
                    used_lines.add(i)
                    logger.info(f"Extracted email: {cv_data['email']}")
                continue
            
            # Check for "Phone:" pattern OR line with digits
            if line_lower.startswith('phone:'):
                phone_value = line.split(':', 1)[1].strip()
                digits = re.sub(r'\D', '', phone_value)
                if len(digits) >= 10 and len(digits) <= 15:
                    cv_data['phone'] = digits
                    used_lines.add(i)
                    logger.info(f"Extracted phone: {cv_data['phone']}")
                continue
            elif cv_data['phone'] == 'N/A':
                digits = re.sub(r'\D', '', line)
                if len(digits) >= 10 and len(digits) <= 15 and len(line) < 30:
                    cv_data['phone'] = digits
                    used_lines.add(i)
                    logger.info(f"Extracted phone: {cv_data['phone']}")
                continue
            
            # Check for "Skills:" pattern OR line with 2+ commas
            if line_lower.startswith('skills:'):
                cv_data['skills'] = line.split(':', 1)[1].strip()
                used_lines.add(i)
                logger.info(f"Extracted skills: {cv_data['skills']}")
                continue
            elif cv_data['skills'] == 'N/A' and line.count(',') >= 2:
                cv_data['skills'] = line
                used_lines.add(i)
                logger.info(f"Extracted skills: {cv_data['skills']}")
                continue
            
            # Check for "Experience:" pattern
            if line_lower.startswith('experience:'):
                cv_data['experience'] = line.split(':', 1)[1].strip()
                used_lines.add(i)
                logger.info(f"Extracted experience: {cv_data['experience']}")
                continue
            
            # Check for "Education:" pattern
            if line_lower.startswith('education:'):
                cv_data['education'] = line.split(':', 1)[1].strip()
                used_lines.add(i)
                logger.info(f"Extracted education: {cv_data['education']}")
                continue
            
            # Check for "Location:" pattern
            if line_lower.startswith('location:'):
                cv_data['location'] = line.split(':', 1)[1].strip()
                used_lines.add(i)
                logger.info(f"Extracted location: {cv_data['location']}")
                continue
        
        # Fallback: If name still not found, use first unused line
        if cv_data['name'] == 'N/A':
            for i, line in enumerate(lines):
                if i in used_lines:
                    continue
                words = line.split()
                if (2 <= len(words) <= 4 and 
                    all(word.replace('.', '').isalpha() for word in words) and
                    len(line) < 50):
                    cv_data['name'] = line.title()
                    used_lines.add(i)
                    logger.info(f"Extracted name (fallback): {cv_data['name']}")
                    break
        
        # Fallback: If skills still not found, look for lines with commas
        if cv_data['skills'] == 'N/A':
            for i, line in enumerate(lines):
                if i in used_lines:
                    continue
                if ',' in line and len(line) > 10:
                    cv_data['skills'] = line
                    used_lines.add(i)
                    logger.info(f"Extracted skills (fallback): {cv_data['skills']}")
                    break
        
        # Fallback: Extract experience (line with "-" or company indicators)
        if cv_data['experience'] == 'N/A':
            for i, line in enumerate(lines):
                if i in used_lines:
                    continue
                if (' - ' in line and len(line) > 15) or any(word in line.lower() for word in ['intern', 'developer', 'engineer', 'manager']):
                    cv_data['experience'] = line
                    used_lines.add(i)
                    logger.info(f"Extracted experience (fallback): {cv_data['experience']}")
                    break
        
        # Fallback: Extract education (degree keywords)
        if cv_data['education'] == 'N/A':
            degree_keywords = ['b.tech', 'btech', 'm.tech', 'mtech', 'bachelor', 'master', 'mba', 'degree', 'university', 'college']
            for i, line in enumerate(lines):
                if i in used_lines:
                    continue
                if any(keyword in line.lower() for keyword in degree_keywords):
                    cv_data['education'] = line
                    used_lines.add(i)
                    logger.info(f"Extracted education (fallback): {cv_data['education']}")
                    break
        
        # Log summary
        logger.info(f"Rule-based extraction result: Name={cv_data['name']}, Email={cv_data['email']}, Phone={cv_data['phone']}")
        
        return cv_data
        
    except Exception as e:
        logger.error(f"Error in rule-based extraction: {str(e)}")
        return None
    
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint to receive WhatsApp messages from Twilio
    Handles BOTH file uploads and text messages with enhanced validation
    """
    try:
        logger.info("Received webhook request")
        
        # Parse incoming message
        message_data = whatsapp_handler.parse_incoming_message(request.form)
        
        if not message_data:
            logger.warning("No valid message data received")
            return jsonify({"status": "no_data"}), 200
        
        logger.info(f"Processing message from {message_data['from']}")
        
        # CASE 1: Message contains media (resume file)
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
            
            # Process and store data
            process_cv_data(cv_data, message_data)
            
            # Cleanup downloaded file
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        
        # CASE 2: Text message - process as resume with validation
        elif message_data.get('body') and message_data['body'].strip():
            logger.info("Text message detected - processing as resume")
            
            resume_text = message_data['body'].strip()
            logger.info(f"Resume text length: {len(resume_text)} characters")
            
            # Try rule-based extraction first for simple messages
            cv_data = extract_simple_cv_data(resume_text)
            
            # If rule-based extraction didn't work well, try AI
            if not cv_data:
                logger.info("Rule-based extraction failed, trying AI extraction")
                cv_data = cv_extractor.extract_cv_data(resume_text)
            
            # Validate the extracted data
            if cv_data:
                is_valid, missing_fields, has_optional_missing = validate_cv_data(cv_data)
                
                if is_valid:
                    # Data is valid - process it
                    logger.info(f"Valid CV data extracted: {cv_data.get('name', 'Unknown')}")
                    process_cv_data(cv_data, message_data)
                else:
                    # Data doesn't meet minimum requirements
                    logger.warning(f"CV data validation failed. Missing: {missing_fields}")
                    whatsapp_handler.send_message(
                        to_number=message_data['from'],
                        message="""❌ I couldn't extract your information. Please use this format:

Name: Your Full Name
Email: your.email@example.com
Phone: 1234567890
Skills: skill1, skill2, skill3
Experience: Company Name - Position (Year - Year)
Education: Degree, University, Year

*Note: Name and at least one of (Email OR Phone) are mandatory.*

Or send your resume as a PDF/DOCX file."""
                    )
            else:
                # Extraction completely failed
                logger.error("Failed to extract any data from text")
                whatsapp_handler.send_message(
                    to_number=message_data['from'],
                    message="""❌ I couldn't extract your information. Please use this format:

Name: Your Full Name
Email: your.email@example.com
Phone: 1234567890
Skills: skill1, skill2, skill3
Experience: Company Name - Position (Year - Year)
Education: Degree, University, Year

*Note: Name and at least one of (Email OR Phone) are mandatory.*

Or send your resume as a PDF/DOCX file."""
                )
            
            return jsonify({"status": "success"}), 200
        
        # CASE 3: Empty message
        else:
            logger.info("Empty message - sending welcome")
            whatsapp_handler.send_message(
                to_number=message_data['from'],
                message="""👋 Welcome to our CV Management System!

You can submit your resume in two ways:

1️⃣ Upload your resume as a PDF or DOCX file
2️⃣ Type your details directly in this format:

Name: Your Full Name
Email: your.email@example.com
Phone: 1234567890
Skills: skill1, skill2, skill3
Experience: Company Name - Position
Education: Degree, University

*Minimum required: Name + (Email OR Phone)*

Please send your information to proceed with your application."""
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
        "version": "2.0.0",
        "features": ["file_upload", "text_message", "enhanced_validation"]
    }), 200


if __name__ == '__main__':
    logger.info("Starting CV Management System v2.0")
    logger.info("Supported inputs: PDF/DOCX files AND text messages")
    logger.info("Validation: Name + (Email OR Phone) required")
    logger.info(f"Webhook will be available at: http://localhost:5000/webhook")
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )