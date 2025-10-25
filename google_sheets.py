"""
Google Sheets Manager Module
Handles all Google Sheets API interactions
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    """
    Manages Google Sheets operations for CV data storage
    """
    
    # Define Google Sheets API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Define column headers for the sheet (removed Current Role)
    HEADERS = [
        'Timestamp',
        'Name',
        'Email',
        'Phone',
        'Skills',
        'Experience',
        'Education',
        'Location',
        'WhatsApp Number',
        'Status'
    ]
    
    def __init__(self, credentials_path: str, sheet_id: str):
        """
        Initialize Google Sheets Manager
        
        Args:
            credentials_path: Path to Google service account credentials JSON
            sheet_id: Google Sheet ID
        """
        self.credentials_path = credentials_path
        self.sheet_id = sheet_id
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        
        self._authenticate()
        self._initialize_sheet()
        
        logger.info("Google Sheets Manager initialized successfully")
    
    def _authenticate(self):
        """
        Authenticate with Google Sheets API using service account
        """
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES
            )
            
            self.client = gspread.authorize(credentials)
            logger.info("Google Sheets authentication successful")
        
        except Exception as e:
            logger.error(f"Error authenticating with Google Sheets: {str(e)}")
            raise
    
    def _initialize_sheet(self):
        """
        Open spreadsheet and initialize headers if needed
        """
        try:
            # Open the spreadsheet
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            
            # Get or create the first worksheet
            try:
                self.worksheet = self.spreadsheet.sheet1
            except Exception:
                logger.info("Creating new worksheet")
                self.worksheet = self.spreadsheet.add_worksheet(
                    title="CV Data",
                    rows="1000",
                    cols="20"
                )
            
            # Check if headers exist, if not add them
            existing_headers = self.worksheet.row_values(1)
            
            if not existing_headers or existing_headers[0] == '':
                logger.info("Adding headers to worksheet")
                self.worksheet.insert_row(self.HEADERS, 1)
                
                # Format header row (bold, background color)
                self.worksheet.format('A1:J1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
                })
            
            logger.info(f"Worksheet initialized: {self.worksheet.title}")
        
        except Exception as e:
            logger.error(f"Error initializing worksheet: {str(e)}")
            raise
    
    def append_cv_data(self, cv_data: Dict) -> Optional[int]:
        """
        Append CV data as a new row in the sheet
        
        Args:
            cv_data: Dictionary containing CV information
            
        Returns:
            int: Row number where data was inserted, or None if failed
        """
        try:
            # Clean timestamp - convert to string and remove all quotes
            timestamp = cv_data.get('submission_timestamp', datetime.now().isoformat())
            timestamp = str(timestamp).strip().replace("'", "").replace('"', '')
            
            # Clean WhatsApp number - remove "whatsapp:" prefix, preserve + and digits
            whatsapp_number = cv_data.get('phone_number', 'N/A')
            whatsapp_number = str(whatsapp_number).strip()
            if whatsapp_number.startswith('whatsapp:'):
                whatsapp_number = whatsapp_number.replace('whatsapp:', '').strip()
            whatsapp_number = whatsapp_number.replace("'", "").replace('"', '')
            # Keep only + (at start) and digits
            import re
            whatsapp_number = re.sub(r'[^\d+]', '', whatsapp_number)
            # Ensure + is only at the start
            if '+' in whatsapp_number:
                whatsapp_number = '+' + whatsapp_number.replace('+', '')
            
            # Clean phone number - preserve + and digits only, remove quotes
            phone = cv_data.get('phone', 'N/A')
            if phone != 'N/A':
                phone = str(phone).strip().replace("'", "").replace('"', '')
                # Keep only + (at start) and digits
                import re
                phone = re.sub(r'[^\d+]', '', phone)
                # Ensure + is only at the start
                if '+' in phone:
                    phone = '+' + phone.replace('+', '')
            else:
                phone = 'N/A'
            
            # Prepare row data in correct order (removed Current Role)
            row_data = [
                timestamp,
                str(cv_data.get('name', 'N/A')),
                str(cv_data.get('email', 'N/A')),
                phone,
                str(cv_data.get('skills', 'N/A')),
                str(cv_data.get('experience', 'N/A')),
                str(cv_data.get('education', 'N/A')),
                str(cv_data.get('location', 'N/A')),
                whatsapp_number,
                'New'  # Status
            ]
            
            # Append the row
            self.worksheet.append_row(row_data, value_input_option='USER_ENTERED')
            
            # Get the row number
            row_number = len(self.worksheet.get_all_values())
            
            logger.info(f"CV data appended successfully at row {row_number}")
            return row_number
        
        except Exception as e:
            logger.error(f"Error appending CV data to sheet: {str(e)}")
            return None
    
    def get_all_cvs(self) -> Optional[List[Dict]]:
        """
        Retrieve all CV records from the sheet
        
        Returns:
            list: List of CV data dictionaries
        """
        try:
            all_records = self.worksheet.get_all_records()
            logger.info(f"Retrieved {len(all_records)} CV records")
            return all_records
        
        except Exception as e:
            logger.error(f"Error retrieving CV records: {str(e)}")
            return None
    
    def update_status(self, row_number: int, status: str) -> bool:
        """
        Update the status of a CV entry
        
        Args:
            row_number: Row number in the sheet
            status: New status value (e.g., 'Reviewed', 'Contacted', 'Rejected')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Status is in column J (10th column)
            self.worksheet.update_cell(row_number, 10, status)
            logger.info(f"Updated status for row {row_number} to '{status}'")
            return True
        
        except Exception as e:
            logger.error(f"Error updating status: {str(e)}")
            return False
    
    def search_by_email(self, email: str) -> Optional[Dict]:
        """
        Search for a CV by email address
        
        Args:
            email: Email address to search for
            
        Returns:
            dict: CV data if found, None otherwise
        """
        try:
            all_records = self.get_all_cvs()
            
            if not all_records:
                return None
            
            for record in all_records:
                if record.get('Email', '').lower() == email.lower():
                    logger.info(f"Found CV for email: {email}")
                    return record
            
            logger.info(f"No CV found for email: {email}")
            return None
        
        except Exception as e:
            logger.error(f"Error searching by email: {str(e)}")
            return None
    
    def get_stats(self) -> Optional[Dict]:
        """
        Get statistics about CV submissions
        
        Returns:
            dict: Statistics including total CVs, status breakdown, etc.
        """
        try:
            all_records = self.get_all_cvs()
            
            if not all_records:
                return {
                    'total_cvs': 0,
                    'status_breakdown': {},
                    'recent_submissions': 0
                }
            
            stats = {
                'total_cvs': len(all_records),
                'status_breakdown': {},
                'recent_submissions': 0
            }
            
            # Count by status
            for record in all_records:
                status = record.get('Status', 'Unknown')
                stats['status_breakdown'][status] = stats['status_breakdown'].get(status, 0) + 1
            
            logger.info(f"Retrieved stats: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return None