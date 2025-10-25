"""
WhatsApp Handler Module
Manages Twilio WhatsApp API interactions
"""

import os
import logging
import requests
from datetime import datetime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class WhatsAppHandler:
    """
    Handles all WhatsApp-related operations using Twilio API
    """
    
    def __init__(self, account_sid, auth_token, whatsapp_number):
        """
        Initialize Twilio client
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            whatsapp_number: Twilio WhatsApp number (format: whatsapp:+1234567890)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.whatsapp_number = whatsapp_number
        self.client = Client(account_sid, auth_token)
        self.download_dir = os.path.join(os.getcwd(), 'downloads')
        
        # Create downloads directory if it doesn't exist
        os.makedirs(self.download_dir, exist_ok=True)
        
        logger.info("WhatsApp Handler initialized successfully")
    
    def parse_incoming_message(self, form_data):
        """
        Parse incoming webhook data from Twilio
        
        Args:
            form_data: Flask request.form object
            
        Returns:
            dict: Parsed message data
        """
        try:
            message_data = {
                'from': form_data.get('From', ''),
                'to': form_data.get('To', ''),
                'body': form_data.get('Body', ''),
                'num_media': int(form_data.get('NumMedia', 0)),
                'timestamp': datetime.now().isoformat()
            }
            
            # Check for media attachments
            if message_data['num_media'] > 0:
                message_data['media_url'] = form_data.get('MediaUrl0', '')
                message_data['media_content_type'] = form_data.get('MediaContentType0', '')
                logger.info(f"Media detected: {message_data['media_content_type']}")
            else:
                message_data['media_url'] = None
                message_data['media_content_type'] = None
            
            return message_data
        
        except Exception as e:
            logger.error(f"Error parsing incoming message: {str(e)}")
            return None
    
    def download_media(self, media_url, media_content_type):
        """
        Download media file from Twilio
        
        Args:
            media_url: URL of the media file
            media_content_type: MIME type of the file
            
        Returns:
            str: Path to downloaded file or None if failed
        """
        try:
            # Determine file extension
            extension_map = {
                'application/pdf': '.pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                'application/msword': '.doc',
                'text/plain': '.txt'
            }
            
            extension = extension_map.get(media_content_type, '.bin')
            
            if extension not in ['.pdf', '.docx', '.doc']:
                logger.warning(f"Unsupported file type: {media_content_type}")
                return None
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"resume_{timestamp}{extension}"
            file_path = os.path.join(self.download_dir, filename)
            
            # Download file with authentication
            logger.info(f"Downloading media from: {media_url}")
            response = requests.get(
                media_url,
                auth=(self.account_sid, self.auth_token),
                timeout=30
            )
            
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"File downloaded successfully: {file_path}")
                return file_path
            else:
                logger.error(f"Failed to download media: HTTP {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return None
    
    def send_message(self, to_number, message):
        """
        Send WhatsApp message to user
        
        Args:
            to_number: Recipient number (format: whatsapp:+1234567890)
            message: Message text to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=to_number
            )
            
            logger.info(f"Message sent successfully. SID: {message_obj.sid}")
            return True
        
        except TwilioRestException as e:
            logger.error(f"Twilio error sending message: {str(e)}")
            return False
        
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False
    
    def send_media_message(self, to_number, message, media_url):
        """
        Send WhatsApp message with media attachment
        
        Args:
            to_number: Recipient number
            message: Message text
            media_url: URL of media to attach
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=to_number,
                media_url=[media_url]
            )
            
            logger.info(f"Media message sent successfully. SID: {message_obj.sid}")
            return True
        
        except TwilioRestException as e:
            logger.error(f"Twilio error sending media message: {str(e)}")
            return False
        
        except Exception as e:
            logger.error(f"Error sending media message: {str(e)}")
            return False