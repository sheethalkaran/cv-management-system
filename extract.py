"""
CV Extraction Module
Extracts text from files and uses AI to parse CV data with smart name validation
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


def extract_name_from_email(email: str) -> str:
    """
    Extract potential name from email address
    
    Examples:
        john.doe@gmail.com -> John Doe
        johndoe123@gmail.com -> Johndoe
        ravi.kumar@email.com -> Ravi Kumar
    
    Args:
        email: Email address
        
    Returns:
        str: Extracted name or empty string
    """
    if not email or email == 'N/A' or '@' not in email:
        return ""
    
    try:
        # Get the part before @
        local_part = email.split('@')[0]
        
        # Remove numbers and special characters except dot
        clean_part = re.sub(r'[0-9_\-]', '', local_part)
        
        # Split by dots: john.doe -> ['john', 'doe']
        if '.' in clean_part:
            parts = clean_part.split('.')
        # Handle camelCase: johnDoe -> ['john', 'Doe']
        else:
            parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', clean_part)
        
        # Filter out very short parts (likely initials or noise)
        meaningful_parts = [p for p in parts if len(p) >= 2]
        
        if meaningful_parts:
            # Title case each part and join
            name = ' '.join(p.title() for p in meaningful_parts)
            logger.info(f"✓ Extracted name from email: {name}")
            return name
        
        return ""
    
    except Exception as e:
        logger.error(f"Error extracting name from email: {str(e)}")
        return ""


def validate_name_with_email(extracted_name: str, email: str) -> tuple:
    """
    Validate extracted name against email and suggest corrections
    
    Args:
        extracted_name: Name extracted from CV
        email: Email address
        
    Returns:
        tuple: (is_valid, confidence_score, suggested_name, reason)
    """
    if not email or email == 'N/A' or '@' not in email:
        return True, 50, extracted_name, "No email to validate against"
    
    if not extracted_name or extracted_name == 'N/A':
        # Try to extract from email
        email_name = extract_name_from_email(email)
        if email_name:
            return False, 70, email_name, "Name extracted from email"
        return False, 0, "N/A", "No name found"
    
    try:
        # Clean extracted name for comparison
        name_parts = extracted_name.lower().split()
        email_local = email.split('@')[0].lower()
        
        # Remove numbers and special chars from email
        clean_email = re.sub(r'[0-9_\-.]', ' ', email_local).strip()
        email_parts = clean_email.split()
        
        # Check if name parts appear in email
        matches = 0
        for name_part in name_parts:
            for email_part in email_parts:
                # Check if name part is in email part or vice versa (min 3 chars)
                if len(name_part) >= 3 and len(email_part) >= 3:
                    if name_part in email_part or email_part in name_part:
                        matches += 1
                        break
        
        # Calculate confidence
        if len(name_parts) == 0:
            confidence = 0
        else:
            confidence = int((matches / len(name_parts)) * 100)
        
        if confidence >= 50:
            return True, confidence, extracted_name, f"Name matches email ({matches}/{len(name_parts)} parts)"
        else:
            # Try to extract better name from email
            email_name = extract_name_from_email(email)
            if email_name and email_name.lower() != extracted_name.lower():
                return False, confidence, email_name, f"Name doesn't match email. Suggested: {email_name}"
            else:
                return True, confidence, extracted_name, "Low confidence but no better alternative"
    
    except Exception as e:
        logger.error(f"Error validating name: {str(e)}")
        return True, 50, extracted_name, "Validation error"


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
        Extract structured CV data using OpenAI API with enhanced name validation
        
        Args:
            cv_text: Raw CV text
            
        Returns:
            dict: Structured CV data
        """
        try:
            # Create enhanced prompt with email-based name validation
            system_prompt = """You are an expert CV/Resume parser specializing in comprehensive skills extraction for the tech industry. Extract information ACCURATELY and return ONLY a valid JSON object.

CRITICAL EXTRACTION RULES:

1. NAME (MOST IMPORTANT - USE EMAIL TO HELP): 
   - Extract ONLY the candidate's full name (first + last name)
   - Format in Title Case (e.g., "John Smith" not "JOHN SMITH")
   - Usually at the TOP of the CV in large/bold text
   - DO NOT confuse with company names or locations
   
   **IMPORTANT: Use EMAIL to validate name**
   Examples:
   - If email is "john.doe@gmail.com" and you see "John Doe" → CORRECT
   - If email is "john.doe@gmail.com" and you see "ABC Company" → WRONG (that's company name)
   - If email is "ravi.kumar@email.com" and you see "Ravi" → probably incomplete, look for "Ravi Kumar"
   - If you can't find a clear name, extract it from email: "john.doe@gmail.com" → "John Doe"
   
   **Name Validation Checklist:**
   ✓ Does the name make sense with the email address?
   ✓ Is it 2-4 words (first + last name, possibly middle)?
   ✓ Is it at the top of the resume?
   ✓ Does it look like a person's name, not a company/location?

2. EMAIL: 
   - Extract email address exactly as written
   - Format: name@domain.com
   - This is CRITICAL for name validation

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

5. SKILLS (COMPREHENSIVE EXTRACTION - EXTRACT EVERYTHING):
   
   YOU MUST EXTRACT **EVERY SINGLE SKILL** MENTIONED ANYWHERE IN THE ENTIRE CV.
   
   Look for skills in ALL sections:
   - Dedicated "Skills" or "Technical Skills" section
   - Project descriptions and technologies used
   - Work experience bullet points
   - Education section (courses, specializations)
   - Certifications section
   - Summary/Objective section
   - ANY mention of tools, technologies, or competencies
   
   Categories (extract ALL you find):
   Programming Languages, Web Technologies, Frontend/Backend Frameworks, Mobile Development,
   Databases, Cloud Platforms, DevOps Tools, Version Control, Testing, Data Science & ML,
   Big Data, Development Tools, Project Management, Design Tools, Operating Systems,
   Methodologies, Soft Skills, Languages Spoken, Domain Knowledge, etc.
   
   EXTRACTION STRATEGY:
   - Read EVERY line carefully
   - Extract technical terms, tool names, framework names
   - Include skills from project descriptions
   - Include technologies in job responsibilities
   - Include certifications/courses
   - Remove only obvious duplicates
   - Format: Comma-separated list
   - NO LIMIT - extract ALL skills (aim for 30-50+ if present)
   
6. WORK EXPERIENCE - CRITICAL FORMAT:
   
   **EXTRACT ALL POSITIONS** and combine into ONE line separated by commas.
   
   **MANDATORY FORMAT:**
   "Company Name - Job Title (Month Year - Month Year), Company Name - Job Title (Month Year - Month Year)"
   
   **EXAMPLES:**
   - Single: "MobiCollector Solutions - Software Developer Intern (Jan 2025 - May 2025)"
   - Multiple: "MobiCollector Solutions - Software Developer Intern (Jan 2025 - May 2025), Sasken Technologies - Android Developer Intern (Jun 2025 - Jul 2025)"
   
   **DATE FORMAT RULES:**
   - ALWAYS put dates in parentheses: (Month Year - Month Year)
   - Use abbreviated months: Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
   - If currently working: use "Present" as end date
   
   **REMOVE:**
   - Company locations (", Bangalore", ", Mumbai")
   - Job descriptions
   - Bullet points
   - Use COMMA between positions, not "|"
   
   **SPECIAL CASES:**
   - If fresher: "Fresher (No work experience)"

7. EDUCATION:
   - Extract HIGHEST or LATEST degree
   - Format: "Degree, Major/Specialization, Institution Name, Year"
   - Example: "B.Tech in Computer Science, IIT Mumbai, 2021"
   - Include graduation year

OUTPUT FORMAT (JSON only, no markdown):
{
    "name": "Candidate Full Name",
    "email": "email@domain.com",
    "phone": "phone number",
    "location": "City, State, Country",
    "skills": "Python, JavaScript, React, Node.js, AWS, Docker, MongoDB, Machine Learning, TensorFlow, Git, JIRA, Agile",
    "experience": "Company - Position (Jan 2025 - May 2025), Company2 - Position2 (Jun 2025 - Present)",
    "education": "B.Tech in Computer Science, ABC Institute, 2019"
}

CRITICAL REMINDERS:
- Use EMAIL to validate and correct the NAME
- If name is unclear, extract from email (john.doe@gmail.com → John Doe)
- Extract ALL skills (30-50+ if present)
- Format experience with dates in parentheses
- If field not found: use "N/A"
- Return ONLY valid JSON"""

            user_prompt = f"""Extract ALL information from this CV. Pay special attention to:
1. Extracting the correct NAME (validate with email)
2. Extracting EVERY SINGLE SKILL mentioned anywhere
3. Extracting ALL work experience positions with dates properly formatted in brackets

CV Text:
{cv_text[:8000]}"""
            
            logger.info("Calling OpenAI API for comprehensive CV parsing")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content.strip()
            logger.info(f"OpenAI raw response (first 500 chars): {response_text[:500]}...")
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Try to parse JSON
            cv_data = json.loads(response_text)
            
            # Validate and clean the extracted data (includes smart name validation)
            cv_data = self._validate_and_clean_data(cv_data)
            
            logger.info(f"✓ Successfully extracted CV data for: {cv_data.get('name', 'Unknown')}")
            
            # Count skills for logging
            skills = cv_data.get('skills', 'N/A')
            if skills != 'N/A':
                skill_count = len([s.strip() for s in skills.split(',') if s.strip()])
                logger.info(f"✓ Skills extracted: {skill_count} skills")
                logger.info(f"✓ Skills preview: {skills[:200]}...")
            
            logger.info(f"✓ Location: {cv_data.get('location', 'N/A')}")
            logger.info(f"✓ Experience: {cv_data.get('experience', 'N/A')}")
            
            return cv_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from OpenAI response: {str(e)}")
            logger.error(f"Response was: {response_text[:500]}")
            return self._fallback_extraction(cv_text)
        
        except Exception as e:
            logger.error(f"Error extracting CV data with OpenAI: {str(e)}")
            return self._fallback_extraction(cv_text)
    
    def _normalize_experience_format(self, experience: str) -> str:
        """Normalize experience format - dates in brackets, comma separated"""
        if experience == 'N/A' or not experience:
            return experience
        
        # Split by | or comma
        positions = re.split(r'[|,]', experience)
        normalized = []
        
        for pos in positions:
            pos = pos.strip()
            if not pos:
                continue
            
            # Remove location after company name (e.g., ", Bangalore")
            pos = re.sub(r',\s*[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)?\s*(?=[-–])', '', pos)
            
            # Convert dates to (Mon Year - Mon Year) format if not already
            # Pattern: 07/01/2025-06/05/2025
            pos = re.sub(r'(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})',
                        lambda m: f"({['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(m.group(2))-1]} {m.group(3)} - {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(m.group(5))-1]} {m.group(6)})",
                        pos)
            
            # Pattern: June - July 2025
            pos = re.sub(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*-\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(\d{4})',
                        lambda m: f"({m.group(1)} {m.group(3)} - {m.group(2)} {m.group(3)})",
                        pos, flags=re.IGNORECASE)
            
            # Ensure dates without brackets get brackets
            pos = re.sub(r'(?<!\()(\d{4}\s*-\s*(?:\d{4}|Present))(?!\))', r'(\1)', pos)
            
            # Clean up spacing and symbols
            pos = re.sub(r'\s*[–|]\s*', ' - ', pos)
            pos = re.sub(r'\s+', ' ', pos).strip()
            
            normalized.append(pos)
        
        return ', '.join(normalized)
    
    def _validate_and_clean_data(self, cv_data: Dict) -> Dict:
        """
        Enhanced validation with smart name extraction using email
        
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
        
        # ENHANCED: Smart name validation and correction using email
        extracted_name = cv_data.get('name', 'N/A')
        email = cv_data.get('email', 'N/A')
        
        if email != 'N/A':
            if extracted_name == 'N/A':
                # No name found - try to extract from email
                email_name = extract_name_from_email(email)
                if email_name:
                    logger.info(f"✓ Name extracted from email: {email_name}")
                    cv_data['name'] = email_name
            else:
                # Validate existing name against email
                is_valid, confidence, suggested_name, reason = validate_name_with_email(extracted_name, email)
                
                logger.info(f"✓ Name validation: {reason} (confidence: {confidence}%)")
                
                # If confidence is low (< 40%), use suggested name from email
                if confidence < 40 and suggested_name and suggested_name != 'N/A':
                    logger.warning(f"⚠ Replacing '{extracted_name}' with '{suggested_name}' based on email")
                    cv_data['name'] = suggested_name
                # If confidence is medium (40-60%), check if email name is better
                elif 40 <= confidence < 60:
                    if suggested_name and suggested_name != extracted_name:
                        # Check if suggested name is longer/more complete
                        if len(suggested_name.split()) > len(extracted_name.split()):
                            logger.info(f"✓ Using more complete name from email: {suggested_name}")
                            cv_data['name'] = suggested_name
        
        # Clean name - convert to Title Case
        if cv_data['name'] != 'N/A':
            cv_data['name'] = cv_data['name'].title()
            logger.info(f"✓ Final name: {cv_data['name']}")
        
        # Clean phone - remove all special characters except + and digits
        if cv_data['phone'] != 'N/A':
            phone = cv_data['phone']
            phone = re.sub(r'[^\d+]', '', phone)
            cv_data['phone'] = phone
        
        # Clean location - ensure it's not the person's name
        location = cv_data.get('location', 'N/A')
        name = cv_data.get('name', '')
        
        if location != 'N/A' and name != 'N/A':
            if location.lower() in name.lower() or name.lower() in location.lower():
                logger.warning(f"Location '{location}' seems to be confused with name '{name}', marking as N/A")
                cv_data['location'] = "N/A"
            
            location_words = location.replace(',', ' ').split()
            if len(location_words) < 2 and not any(char.isdigit() for char in location):
                logger.warning(f"Location '{location}' seems incomplete, marking as N/A")
                cv_data['location'] = "N/A"
        
        # Clean skills - remove duplicates but preserve comprehensiveness
        skills = cv_data.get('skills', 'N/A')
        if skills != 'N/A':
            skill_list = [s.strip() for s in skills.split(',')]
            
            seen = set()
            unique_skills = []
            for skill in skill_list:
                skill_lower = skill.lower()
                if skill_lower and skill_lower not in seen and len(skill) > 1:
                    seen.add(skill_lower)
                    unique_skills.append(skill)
            
            cv_data['skills'] = ', '.join(unique_skills)
            logger.info(f"✓ Cleaned skills: {len(unique_skills)} unique skills retained")
        
        # Clean and normalize experience format
        experience = cv_data.get('experience', 'N/A')
        if experience != 'N/A':
            experience = self._normalize_experience_format(experience)
            cv_data['experience'] = experience
            logger.info(f"✓ Normalized experience: {experience}")
        
        return cv_data
    
    def _fallback_extraction(self, cv_text: str) -> Optional[Dict]:
        """
        Fallback extraction using regex patterns with comprehensive skills
        Includes smart name extraction from email
        
        Args:
            cv_text: Raw CV text
            
        Returns:
            dict: Extracted data using regex
        """
        logger.info("Using fallback regex extraction with comprehensive skills")
        
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
            
            # Extract email FIRST (needed for name validation)
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, cv_text)
            if email_match:
                cv_data['email'] = email_match.group(0)
            
            # Extract phone - clean format
            phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}'
            phone_match = re.search(phone_pattern, cv_text)
            if phone_match:
                phone = phone_match.group(0)
                phone = re.sub(r'[^\d+]', '', phone)
                cv_data['phone'] = phone
            
            # Extract name - look in first 15 lines
            for i, line in enumerate(lines[:15]):
                line = line.strip()
                if '@' in line or any(char.isdigit() for char in line) or len(line) < 5 or len(line) > 50:
                    continue
                if any(word.upper() in line.upper() for word in ['RESUME', 'CV', 'CURRICULUM', 'VITAE', 'PROFILE']):
                    continue
                words = line.split()
                if 2 <= len(words) <= 4 and (line.istitle() or line.isupper()):
                    cv_data['name'] = line.title()
                    break
            
            # SMART NAME VALIDATION: Use email to validate/correct name
            if cv_data['email'] != 'N/A':
                if cv_data['name'] == 'N/A':
                    # No name found - extract from email
                    email_name = extract_name_from_email(cv_data['email'])
                    if email_name:
                        logger.info(f"✓ Fallback: Name extracted from email: {email_name}")
                        cv_data['name'] = email_name
                else:
                    # Validate name against email
                    is_valid, confidence, suggested_name, reason = validate_name_with_email(
                        cv_data['name'], cv_data['email']
                    )
                    logger.info(f"✓ Fallback name validation: {reason} (confidence: {confidence}%)")
                    
                    if confidence < 40 and suggested_name and suggested_name != 'N/A':
                        logger.warning(f"⚠ Fallback: Replacing '{cv_data['name']}' with '{suggested_name}'")
                        cv_data['name'] = suggested_name
            
            # Extract location
            for i, line in enumerate(lines[:30]):
                if any(indicator in line.lower() for indicator in ['location:', 'address:', 'based in', 'current location']):
                    if i + 1 < len(lines):
                        potential_location = lines[i + 1].strip()
                        if ',' in potential_location and len(potential_location) < 100:
                            cv_data['location'] = potential_location
                            break
                
                location_match = re.search(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b', line)
                if location_match and '@' not in line and 'http' not in line.lower():
                    if i < 20:
                        potential_loc = f"{location_match.group(1)}, {location_match.group(2)}"
                        if cv_data['name'] == 'N/A' or potential_loc.lower() not in cv_data['name'].lower():
                            cv_data['location'] = potential_loc
                            break
            
            # Extract ALL skills comprehensively
            skills_set = set()
            in_skills_section = False
            
            tech_keywords = [
                'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
                'node', 'express', 'django', 'flask', 'spring', 'aws', 'azure', 'gcp',
                'docker', 'kubernetes', 'jenkins', 'git', 'mongodb', 'mysql', 'postgresql',
                'redis', 'elasticsearch', 'html', 'css', 'sass', 'bootstrap', 'tailwind',
                'api', 'rest', 'graphql', 'sql', 'nosql', 'agile', 'scrum', 'jira',
                'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit', 'opencv', 'nltk',
                'linux', 'ubuntu', 'bash', 'shell', 'powershell', 'ci/cd', 'devops'
            ]
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                
                if any(header in line_lower for header in ['skills', 'technical skills', 'core competencies', 'expertise', 'technologies', 'tools', 'proficiencies']):
                    if len(line_lower) < 50:
                        in_skills_section = True
                        continue
                
                if in_skills_section and any(header in line_lower for header in ['experience', 'education', 'projects', 'certifications', 'work history', 'employment']):
                    if len(line_lower) < 50:
                        in_skills_section = False
                
                if in_skills_section and line.strip():
                    cleaned_line = re.sub(r'[•▪▫◦●○✓■\-\*]', '', line)
                    for separator in [',', '|', ';', '/', ':']:
                        if separator in cleaned_line:
                            parts = cleaned_line.split(separator)
                            for part in parts:
                                skill = part.strip()
                                if skill and 1 < len(skill) < 50:
                                    skills_set.add(skill)
                            break
                    else:
                        skill = cleaned_line.strip()
                        if skill and 2 < len(skill) < 50:
                            skills_set.add(skill)
                
                for keyword in tech_keywords:
                    if keyword in line_lower:
                        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                        match = pattern.search(line)
                        if match:
                            skills_set.add(match.group())
            
            if skills_set:
                cv_data['skills'] = ', '.join(sorted(skills_set, key=str.lower))
                logger.info(f"✓ Fallback extracted {len(skills_set)} skills")
            
            # Extract experience - ALL headers with proper date formatting
            experience_headers = []
            in_exp_section = False
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                line_stripped = line.strip()
                
                if any(header in line_lower for header in ['experience', 'work experience', 'professional experience', 'employment history', 'internship']):
                    if len(line_lower) < 50:
                        in_exp_section = True
                        continue
                
                if in_exp_section:
                    if any(header in line_lower for header in ['education', 'projects', 'certifications', 'skills']):
                        if len(line_lower) < 50:
                            break
                    
                    # Look for lines that look like job headers
                    if line_stripped and 20 < len(line_stripped) < 200:
                        # Check for date patterns
                        has_date = bool(re.search(r'\b(19|20)\d{2}\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*-?\s*\d{0,4}|\bpresent\b|\d{1,2}/\d{1,2}/\d{4}', line_lower))
                        # Check for company indicators
                        has_company = any(indicator in line_lower for indicator in ['intern', 'developer', 'engineer', 'manager', 'analyst', 'designer', 'pvt', 'ltd', 'limited', 'inc', 'corp', 'technologies', 'solutions', 'systems'])
                        
                        if has_date and has_company:
                            # This looks like a job header - extract and format
                            experience_headers.append(line_stripped)
                            if len(experience_headers) >= 10:  # Max 10 positions
                                break
            
            if experience_headers:
                # Join with comma and normalize
                raw_experience = ', '.join(experience_headers)
                cv_data['experience'] = self._normalize_experience_format(raw_experience)
            elif any(word in cv_text.lower() for word in ['fresher', 'fresh graduate']):
                cv_data['experience'] = 'Fresher (No work experience)'
            
            # Extract education
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['b.tech', 'btech', 'm.tech', 'mtech', 'bachelor', 'master', 'mca', 'bca', 'mba', 'phd', 'b.e', 'b.sc', 'm.sc']):
                    if 15 < len(line.strip()) < 200:
                        cv_data['education'] = line.strip()
                        break
            
            logger.info("✓ Fallback extraction completed")
            return cv_data
        
        except Exception as e:
            logger.error(f"Error in fallback extraction: {str(e)}")
            return None