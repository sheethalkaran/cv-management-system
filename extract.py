"""
CV Extraction Module
Extracts text from files and uses AI to parse CV data
"""

import os
import re
import logging
import json
from typing import Dict, Optional
import PyPDF2
import pdfplumber
import docx
from openai import OpenAI

logger = logging.getLogger(__name__)


class CVExtractor:
    """
    Handles CV text extraction and AI-powered data parsing
    """
    
    def __init__(self, openai_api_key):
        """
        Initialize CV Extractor with OpenAI client
        
        Args:
            openai_api_key: OpenAI API key
        """
        self.openai_client = OpenAI(api_key=openai_api_key)
        logger.info("CV Extractor initialized successfully")
    
    def extract_text_from_file(self, file_path: str) -> Optional[str]:
        """
        Extract text from PDF or DOCX file
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Extracted text or None if failed
        """
        try:
            extension = os.path.splitext(file_path)[1].lower()
            
            if extension == '.pdf':
                return self._extract_from_pdf(file_path)
            elif extension in ['.docx', '.doc']:
                return self._extract_from_docx(file_path)
            else:
                logger.warning(f"Unsupported file format: {extension}")
                return None
        
        except Exception as e:
            logger.error(f"Error extracting text from file: {str(e)}")
            return None
    
    def _extract_from_pdf(self, file_path: str) -> Optional[str]:
        """
        Extract text from PDF using pdfplumber (fallback to PyPDF2)
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            str: Extracted text
        """
        try:
            # Try pdfplumber first (better text extraction)
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if text.strip():
                logger.info(f"Extracted {len(text)} characters from PDF using pdfplumber")
                return text.strip()
            
            # Fallback to PyPDF2
            logger.info("Trying PyPDF2 as fallback")
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            logger.info(f"Extracted {len(text)} characters from PDF using PyPDF2")
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error extracting from PDF: {str(e)}")
            return None
    
    def _extract_from_docx(self, file_path: str) -> Optional[str]:
        """
        Extract text from DOCX file
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            str: Extracted text
        """
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            logger.info(f"Extracted {len(text)} characters from DOCX")
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error extracting from DOCX: {str(e)}")
            return None
    
    def extract_cv_data(self, cv_text: str) -> Optional[Dict]:
        """
        Extract structured CV data using OpenAI API
        
        Args:
            cv_text: Raw CV text
            
        Returns:
            dict: Structured CV data
        """
        try:
            # Create enhanced prompt for GPT with very specific instructions
            system_prompt = """You are an expert CV/Resume parser. Extract information ACCURATELY from the CV and return ONLY a valid JSON object.

CRITICAL EXTRACTION RULES:

1. NAME: 
   - Extract ONLY the candidate's full name (first + last name)
   - Format in Title Case (e.g., "John Smith" not "JOHN SMITH")
   - Usually at the TOP of the CV in large/bold text
   - DO NOT confuse with company names or locations

2. EMAIL: 
   - Extract email address exactly as written
   - Format: name@domain.com

3. PHONE: 
   - Extract phone number from CV (not from WhatsApp)
   - Remove any special characters except + and digits
   - Format: Clean number with country code if present
   - Example: +919876543210 or 9876543210

4. LOCATION (Candidate's Current Location - NOT Company Location):
   - Format: "City, State" or "City, State, Country" 
   - Extract from CONTACT section or ADDRESS at top of CV
   - Examples: "Bangalore, Karnataka", "Mumbai, Maharashtra, India"
   - DO NOT extract company office locations
   - DO NOT extract candidate's name as location
   - Look for address/location near contact details

5. SKILLS (Extract EVERY single skill mentioned):
   - Programming Languages: Python, Java, JavaScript, C++, etc.
   - Frameworks/Libraries: React, Django, Flask, Node.js, Angular, etc.
   - Databases: MySQL, PostgreSQL, MongoDB, Redis, etc.
   - Cloud/DevOps: AWS, Azure, GCP, Docker, Kubernetes, Jenkins, etc.
   - Tools: Git, JIRA, Postman, VS Code, etc.
   - Soft Skills: Leadership, Communication, Team Management, etc.
   - Languages Spoken: English, Hindi, etc.
   - Domain Knowledge: Machine Learning, AI, Data Analysis, etc.
   - Format: Comma-separated list
   - Be COMPREHENSIVE - extract ALL skills from entire CV

6. WORK EXPERIENCE (Company Details and Duration):
   - For EACH job, extract in format: "Job Title at Company Name (Duration)"
   - Example: "Senior Developer at Tech Corp (2021-2023)"
   - Example: "Software Engineer at Infosys, Bangalore (2019-2021)"
   - Separate multiple jobs with " | "
   - Full format: "Role at Company (Duration) | Role at Company (Duration)"
   - If fresher: "Fresher (No work experience)"
   - If only internship: "Internship at Company Name (Duration)"

7. EDUCATION:
   - Extract HIGHEST or LATEST degree
   - Format: "Degree, Major/Specialization, Institution Name, Year"
   - Example: "B.Tech in Computer Science, IIT Mumbai, 2021"
   - Example: "Master of Science in Data Science, XYZ University, 2023"
   - Include graduation year

EXTRACTION TIPS:
- Read the ENTIRE CV carefully
- Location is at TOP in contact section (NOT in experience section)
- Skills can be in: Skills section, Technical Skills, Core Competencies, Tools & Technologies
- Experience section lists previous jobs with company names
- Don't miss skills mentioned in project descriptions
- Extract ALL technical terms as potential skills

OUTPUT FORMAT (JSON only, no markdown):
{
    "name": "Candidate Full Name",
    "email": "email@domain.com",
    "phone": "phone number",
    "location": "City, State, Country",
    "skills": "Python, JavaScript, React, Node.js, AWS, Docker, MongoDB, Machine Learning, Communication, Leadership, English, Hindi",
    "experience": "Senior Developer at ABC Corp (2021-2023) | Software Engineer at XYZ Ltd (2019-2021)",
    "education": "B.Tech in Computer Science, ABC Institute, 2019"
}

If field not found: use "N/A"
Return ONLY valid JSON, no extra text."""

            user_prompt = f"""Extract ALL information from this CV. Read carefully and be thorough:\n\n{cv_text[:6000]}"""
            
            logger.info("Calling OpenAI API for CV parsing")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content.strip()
            logger.info(f"OpenAI raw response (first 300 chars): {response_text[:300]}...")
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Try to parse JSON
            cv_data = json.loads(response_text)
            
            # Validate and clean the extracted data
            cv_data = self._validate_and_clean_data(cv_data)
            
            logger.info(f"Successfully extracted CV data for: {cv_data.get('name', 'Unknown')}")
            logger.info(f"Skills extracted: {len(cv_data.get('skills', '').split(','))} items")
            logger.info(f"Location: {cv_data.get('location', 'N/A')}")
            logger.info(f"Experience: {cv_data.get('experience', 'N/A')[:100]}...")
            
            return cv_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from OpenAI response: {str(e)}")
            return self._fallback_extraction(cv_text)
        
        except Exception as e:
            logger.error(f"Error extracting CV data with OpenAI: {str(e)}")
            return self._fallback_extraction(cv_text)
    
    def _validate_and_clean_data(self, cv_data: Dict) -> Dict:
        """
        Validate and clean extracted CV data
        
        Args:
            cv_data: Raw extracted data
            
        Returns:
            dict: Cleaned and validated data
        """
        # Ensure all required fields exist
        required_fields = ['name', 'email', 'phone', 'skills', 'experience', 'education', 'location']
        for field in required_fields:
            if field not in cv_data or not cv_data[field]:
                cv_data[field] = "N/A"
        
        # Clean name - convert to Title Case
        if cv_data['name'] != 'N/A':
            cv_data['name'] = cv_data['name'].title()
        
        # Clean phone - remove all special characters except + and digits
        if cv_data['phone'] != 'N/A':
            phone = cv_data['phone']
            # Remove all characters except digits and +
            phone = re.sub(r'[^\d+]', '', phone)
            cv_data['phone'] = phone
        
        # Clean location - ensure it's not the person's name
        location = cv_data.get('location', 'N/A')
        name = cv_data.get('name', '')
        
        if location != 'N/A' and name != 'N/A':
            # Check if location is suspiciously similar to name
            if location.lower() in name.lower() or name.lower() in location.lower():
                logger.warning(f"Location '{location}' seems to be confused with name '{name}', marking as N/A")
                cv_data['location'] = "N/A"
            
            # Check if location has fewer than 2 words (likely not a proper location)
            location_words = location.replace(',', ' ').split()
            if len(location_words) < 2 and not any(char.isdigit() for char in location):
                logger.warning(f"Location '{location}' seems incomplete, marking as N/A")
                cv_data['location'] = "N/A"
        
        # Clean skills - remove duplicates and extra spaces
        skills = cv_data.get('skills', 'N/A')
        if skills != 'N/A':
            skill_list = [s.strip() for s in skills.split(',')]
            skill_list = list(dict.fromkeys(skill_list))
            skill_list = [s for s in skill_list if s]
            cv_data['skills'] = ', '.join(skill_list)
        
        # Clean experience - ensure proper formatting
        experience = cv_data.get('experience', 'N/A')
        if experience != 'N/A' and len(experience) > 500:
            cv_data['experience'] = experience[:500] + "..."
        
        return cv_data
    
    def _fallback_extraction(self, cv_text: str) -> Optional[Dict]:
        """
        Fallback extraction using regex patterns
        
        Args:
            cv_text: Raw CV text
            
        Returns:
            dict: Extracted data using regex
        """
        logger.info("Using fallback regex extraction")
        
        try:
            cv_data = {
                'name': 'N/A',
                'email': 'N/A',
                'phone': 'N/A',
                'skills': 'N/A',
                'experience': 'N/A',
                'education': 'N/A',
                'location': 'N/A'
            }
            
            lines = cv_text.split('\n')
            
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, cv_text)
            if email_match:
                cv_data['email'] = email_match.group(0)
            
            # Extract phone - clean format
            phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}'
            phone_match = re.search(phone_pattern, cv_text)
            if phone_match:
                phone = phone_match.group(0)
                # Clean phone - keep only digits and +
                phone = re.sub(r'[^\d+]', '', phone)
                cv_data['phone'] = phone
            
            # Extract name - look in first 15 lines for title case or all caps name
            for i, line in enumerate(lines[:15]):
                line = line.strip()
                if '@' in line or any(char.isdigit() for char in line) or len(line) < 5 or len(line) > 50:
                    continue
                if any(word.upper() in line.upper() for word in ['RESUME', 'CV', 'CURRICULUM', 'VITAE', 'PROFILE']):
                    continue
                words = line.split()
                if 2 <= len(words) <= 4 and (line.istitle() or line.isupper()):
                    cv_data['name'] = line.title()  # Convert to Title Case
                    break
            
            # Extract location - look near top, near contact info
            for i, line in enumerate(lines[:30]):
                if any(indicator in line.lower() for indicator in ['location:', 'address:', 'based in', 'current location']):
                    if i + 1 < len(lines):
                        potential_location = lines[i + 1].strip()
                        if ',' in potential_location and len(potential_location) < 100:
                            cv_data['location'] = potential_location
                            break
                
                location_match = re.search(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b', line)
                if location_match and '@' not in line and 'http' not in line.lower():
                    if i < 20 or 'experience' not in lines[max(0, i-5):i][0].lower() if i >= 5 else True:
                        potential_loc = f"{location_match.group(1)}, {location_match.group(2)}"
                        if cv_data['name'] == 'N/A' or potential_loc.lower() not in cv_data['name'].lower():
                            cv_data['location'] = potential_loc
                            break
            
            # Extract skills
            skills_list = []
            in_skills_section = False
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                
                if any(header in line_lower for header in ['skills', 'technical skills', 'core competencies', 'expertise', 'technologies', 'tools']):
                    if len(line_lower) < 50:
                        in_skills_section = True
                        continue
                
                if in_skills_section and len(line_lower) > 0:
                    if any(header in line_lower for header in ['experience', 'education', 'projects', 'certifications', 'work history']):
                        if len(line_lower) < 50:
                            break
                
                if in_skills_section and line.strip():
                    cleaned_line = re.sub(r'[•▪▫◦●○✓■]', '', line)
                    for separator in [',', '|', ';', '/', ':']:
                        if separator in cleaned_line:
                            parts = cleaned_line.split(separator)
                            for part in parts:
                                skill = part.strip()
                                if skill and len(skill) > 1 and len(skill) < 50:
                                    skills_list.append(skill)
                            break
                    else:
                        skill = cleaned_line.strip()
                        if skill and len(skill) > 2 and len(skill) < 50:
                            skills_list.append(skill)
            
            if skills_list:
                skills_list = list(dict.fromkeys(skills_list))
                cv_data['skills'] = ', '.join(skills_list)
            
            # Extract experience
            experience_parts = []
            in_exp_section = False
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                
                if any(header in line_lower for header in ['experience', 'work experience', 'professional experience', 'employment history']):
                    if len(line_lower) < 50:
                        in_exp_section = True
                        continue
                
                if in_exp_section:
                    if any(header in line_lower for header in ['education', 'projects', 'certifications', 'skills']):
                        if len(line_lower) < 50:
                            break
                
                if in_exp_section and line.strip() and len(line.strip()) > 10:
                    if any(indicator in line.lower() for indicator in [' at ', 'pvt', 'ltd', 'inc', 'corp', 'technologies', 'solutions']):
                        experience_parts.append(line.strip())
                        if len(experience_parts) >= 3:
                            break
            
            if experience_parts:
                cv_data['experience'] = ' | '.join(experience_parts[:3])
            elif any(word in cv_text.lower() for word in ['fresher', 'fresh graduate']):
                cv_data['experience'] = 'Fresher'
            
            # Extract education
            education_found = False
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['b.tech', 'btech', 'm.tech', 'mtech', 'bachelor', 'master', 'mca', 'bca', 'mba', 'phd', 'b.e', 'b.sc', 'm.sc']):
                    if len(line.strip()) > 15 and len(line.strip()) < 200:
                        cv_data['education'] = line.strip()
                        education_found = True
                        break
            
            if not education_found:
                in_edu_section = False
                for i, line in enumerate(lines):
                    if 'education' in line.lower() and len(line.strip()) < 50:
                        in_edu_section = True
                        continue
                    
                    if in_edu_section and line.strip() and len(line.strip()) > 15:
                        cv_data['education'] = line.strip()
                        break
            
            logger.info("Fallback extraction completed")
            return cv_data
        
        except Exception as e:
            logger.error(f"Error in fallback extraction: {str(e)}")
            return None