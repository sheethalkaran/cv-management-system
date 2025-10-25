"""
Utility Functions Module
Common utilities and helper functions
"""

import os
import logging
import sys
from typing import List


def setup_logging(log_level=logging.INFO):
    """
    Configure logging for the application
    
    Args:
        log_level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Create formatters and handlers
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler(
        os.path.join(log_dir, 'cv_management.log'),
        mode='a'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    logging.info("Logging configured successfully")


def validate_env_variables(required_vars: List[str]):
    """
    Validate that all required environment variables are set
    
    Args:
        required_vars: List of required environment variable names
        
    Raises:
        EnvironmentError: If any required variable is missing
    """
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logging.error(error_msg)
        raise EnvironmentError(error_msg)
    
    logging.info("All required environment variables are set")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove unsafe characters
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    import re
    
    # Remove any characters that aren't alphanumeric, dash, underscore, or period
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    return sanitized


def format_phone_number(phone: str) -> str:
    """
    Format phone number to a standard format
    
    Args:
        phone: Raw phone number string
        
    Returns:
        str: Formatted phone number
    """
    import re
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Format based on length
    if len(digits) == 10:
        # Indian format: +91 XXXXX XXXXX
        return f"+91 {digits[:5]} {digits[5:]}"
    elif len(digits) == 12 and digits.startswith('91'):
        # Already has country code
        return f"+91 {digits[2:7]} {digits[7:]}"
    else:
        # Return as-is with + prefix if it starts with a digit
        return f"+{digits}" if digits else phone


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified length with ellipsis
    
    Args:
        text: Text to truncate
        max_length: Maximum length (default: 100)
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def is_valid_email(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def extract_skills_list(skills_str: str) -> List[str]:
    """
    Extract and clean list of skills from comma-separated string
    
    Args:
        skills_str: Comma-separated skills string
        
    Returns:
        list: List of individual skills
    """
    if not skills_str or skills_str == 'N/A':
        return []
    
    # Split by comma and clean each skill
    skills = [skill.strip() for skill in skills_str.split(',')]
    
    # Remove empty strings and duplicates
    skills = list(set([s for s in skills if s]))
    
    return skills


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to file
        
    Returns:
        float: File size in MB
    """
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)
    except Exception:
        return 0.0


def create_response_message(cv_data: dict) -> str:
    """
    Create a formatted response message for WhatsApp
    
    Args:
        cv_data: Dictionary containing CV data
        
    Returns:
        str: Formatted message
    """
    name = cv_data.get('name', 'N/A')
    email = cv_data.get('email', 'N/A')
    experience = cv_data.get('experience', 'N/A')
    skills = cv_data.get('skills', 'N/A')
    
    message = f"""✅ *Resume Received Successfully!*

📋 *Extracted Information:*
• Name: {name}
• Email: {email}
• Experience: {experience}
• Skills: {truncate_text(skills, 80)}

Your application has been recorded in our system. Our HR team will review your profile and contact you soon.

Thank you for your interest! 🎯"""
    
    return message


def cleanup_old_files(directory: str, days: int = 7):
    """
    Clean up files older than specified days
    
    Args:
        directory: Directory to clean
        days: Number of days to keep files (default: 7)
    """
    import time
    
    try:
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)
        
        if not os.path.exists(directory):
            return
        
        deleted_count = 0
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if os.path.isfile(file_path):
                file_modified = os.path.getmtime(file_path)
                
                if file_modified < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
        
        if deleted_count > 0:
            logging.info(f"Cleaned up {deleted_count} old files from {directory}")
    
    except Exception as e:
        logging.error(f"Error cleaning up old files: {str(e)}")