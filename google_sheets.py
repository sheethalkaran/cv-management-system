"""
Google Sheets Manager Module
Handles all Google Sheets API interactions with duplicate detection
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
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
    
    # Define column headers for the sheet
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
    
    def check_duplicate(self, email: str, phone: str) -> Tuple[bool, Optional[int], Optional[Dict]]:
        """
        Check if email or phone already exists in the sheet
        
        Args:
            email: Email address to check
            phone: Phone number to check
            
        Returns:
            tuple: (is_duplicate, row_number, existing_data)
                - is_duplicate: True if duplicate found
                - row_number: Row number of duplicate (None if not found)
                - existing_data: Dictionary of existing record (None if not found)
        """
        try:
            all_values = self.worksheet.get_all_values()
            
            # Skip header row (index 0)
            for idx, row in enumerate(all_values[1:], start=2):
                if len(row) < 4:  # Not enough columns
                    continue
                
                existing_email = row[2].strip().lower() if len(row) > 2 else ""
                existing_phone = row[3].strip() if len(row) > 3 else ""
                
                # Clean phone numbers for comparison (remove +, spaces, etc.)
                import re
                clean_existing_phone = re.sub(r'[^\d]', '', existing_phone)
                clean_input_phone = re.sub(r'[^\d]', '', phone)
                
                # Check for email match (if not N/A)
                email_match = (email.lower() != 'n/a' and 
                              existing_email != 'n/a' and 
                              existing_email == email.lower())
                
                # Check for phone match (if not N/A)
                phone_match = (clean_input_phone != '' and 
                              clean_input_phone != 'na' and 
                              clean_existing_phone != '' and 
                              clean_existing_phone != 'na' and 
                              clean_existing_phone == clean_input_phone)
                
                if email_match or phone_match:
                    # Found duplicate
                    existing_data = {
                        'Timestamp': row[0] if len(row) > 0 else 'N/A',
                        'Name': row[1] if len(row) > 1 else 'N/A',
                        'Email': row[2] if len(row) > 2 else 'N/A',
                        'Phone': row[3] if len(row) > 3 else 'N/A',
                        'Skills': row[4] if len(row) > 4 else 'N/A',
                        'Experience': row[5] if len(row) > 5 else 'N/A',
                        'Education': row[6] if len(row) > 6 else 'N/A',
                        'Location': row[7] if len(row) > 7 else 'N/A',
                        'WhatsApp Number': row[8] if len(row) > 8 else 'N/A',
                        'Status': row[9] if len(row) > 9 else 'N/A'
                    }
                    
                    match_type = "email" if email_match else "phone"
                    logger.info(f"Duplicate found at row {idx} (matched by {match_type})")
                    return True, idx, existing_data
            
            # No duplicate found
            logger.info("No duplicate found")
            return False, None, None
        
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            return False, None, None
    
    def delete_row(self, row_number: int) -> bool:
        """
        Delete a specific row from the sheet
        
        Args:
            row_number: Row number to delete (1-indexed)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.worksheet.delete_rows(row_number)
            logger.info(f"Deleted row {row_number}")
            return True
        except Exception as e:
            logger.error(f"Error deleting row {row_number}: {str(e)}")
            return False
    
    def append_cv_data(self, cv_data: Dict) -> Optional[int]:
        """
        Append CV data as a new row in the sheet
        Checks for duplicates and deletes old entry if found
        
        Args:
            cv_data: Dictionary containing CV information
            
        Returns:
            tuple: (row_number, is_update) where:
                - row_number: Row number where data was inserted
                - is_update: True if this was an update (duplicate removed)
                Or None if failed
        """
        try:
            # Clean and prepare data
            timestamp = cv_data.get('submission_timestamp', datetime.now().isoformat())
            timestamp = str(timestamp).strip().replace("'", "").replace('"', '')
            
            # Clean WhatsApp number
            whatsapp_number = cv_data.get('phone_number', 'N/A')
            whatsapp_number = str(whatsapp_number).strip()
            if whatsapp_number.startswith('whatsapp:'):
                whatsapp_number = whatsapp_number.replace('whatsapp:', '').strip()
            whatsapp_number = whatsapp_number.replace("'", "").replace('"', '')
            import re
            whatsapp_number = re.sub(r'[^\d+]', '', whatsapp_number)
            if '+' in whatsapp_number:
                whatsapp_number = '+' + whatsapp_number.replace('+', '')
            
            # Clean phone number
            phone = cv_data.get('phone', 'N/A')
            if phone != 'N/A':
                phone = str(phone).strip().replace("'", "").replace('"', '')
                phone = re.sub(r'[^\d+]', '', phone)
                if '+' in phone:
                    phone = '+' + phone.replace('+', '')
            
            email = str(cv_data.get('email', 'N/A'))
            
            # Check for duplicates
            is_duplicate, old_row_number, old_data = self.check_duplicate(email, phone)
            
            # Prepare row data
            row_data = [
                timestamp,
                str(cv_data.get('name', 'N/A')),
                email,
                phone,
                str(cv_data.get('skills', 'N/A')),
                str(cv_data.get('experience', 'N/A')),
                str(cv_data.get('education', 'N/A')),
                str(cv_data.get('location', 'N/A')),
                whatsapp_number,
                'Updated' if is_duplicate else 'New'
            ]
            
            # If duplicate found, delete old row
            if is_duplicate and old_row_number:
                logger.info(f"Duplicate detected. Deleting old entry at row {old_row_number}")
                self.delete_row(old_row_number)
            
            # Append the new row
            self.worksheet.append_row(row_data, value_input_option='USER_ENTERED')
            
            # Get the row number
            row_number = len(self.worksheet.get_all_values())
            
            logger.info(f"CV data {'updated' if is_duplicate else 'appended'} successfully at row {row_number}")
            
            # Return as tuple: (row_number, is_update)
            return (row_number, is_duplicate)
        
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