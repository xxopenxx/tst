from typing import List, Dict, Any
import json
import io
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
import PyPDF2
import csv
class ContentExtractor:
    """
    Class to extract content from various file types given their URLs.
    """
    def __init__(self):
        pass
    async def extract_content_from_url(self, url: str, session: AsyncSession) -> tuple[str, str]:
        """Extract content from URL based on file type"""
        response = await session.get(url, impersonate="chrome107", timeout=10)
        response.raise_for_status()
        file_type = url.lower().split('.')[-1]
        content = response.content
        filename = url.split('/')[-1]
        if file_type == 'pdf':
            return filename, await self._extract_from_pdf(content)
        elif file_type == 'txt':
            return filename, content.decode('utf-8', errors='ignore')
        elif file_type == 'csv':
            return filename, await self._extract_from_csv(content)
        elif file_type == 'json':
            return filename, await self._extract_from_json(content)
        elif file_type in ['md', 'markdown']:
            return filename, await self._extract_from_markdown(content)
        elif file_type in ['html', 'htm']:
            return filename, await self._extract_from_html(content)
        elif file_type in ['rtf']:
            return filename, "Warning: RTF files are not directly supported. Please convert to PDF or DOCX"
        else:
            return filename, response.text
    async def _extract_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF content"""
        pdf_file = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = []
        for page in pdf_reader.pages:
            text.append(page.extract_text())
        return "\n".join(text)
    async def _extract_from_csv(self, content: bytes) -> str:
        """Extract text from CSV content"""
        csv_file = io.StringIO(content.decode('utf-8'))
        reader = csv.reader(csv_file)
        rows = list(reader)
        if not rows:
            return "Empty CSV file"
        header = "| " + " | ".join(str(cell) for cell in rows[0]) + " |"
        separator = "|---" * len(rows[0]) + "|"
        data_rows = [
            "| " + " | ".join(str(cell) for cell in row) + " |"
            for row in rows[1:]
        ]
        return "\n".join([header, separator] + data_rows)
    async def _extract_from_json(self, content: bytes) -> str:
        """Extract text from JSON content"""
        json_data = json.loads(content)
        return json.dumps(json_data, indent=2)
    async def _extract_from_markdown(self, content: bytes) -> str:
        """Extract text from Markdown content"""
        md_text = content.decode('utf-8')
        return md_text
    async def _extract_from_html(self, content: bytes) -> str:
        """Extract text from HTML content"""
        soup = BeautifulSoup(content, 'html.parser')
        return soup.get_text(separator='\n')
            
class MessageProcessor:
    """Process OpenAI-style messages and extract content from URLs"""
    def __init__(self):
        self.content_extractor = ContentExtractor()
    async def process_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Process messages and extract content from URLs"""
        session = AsyncSession(impersonate="chrome107")
        processed_messages = []
        
        for message in messages:
            if message["role"] == "user" and isinstance(message["content"], list):
                extracted_data = []
                text_parts = []
                for item in message["content"]:
                    if item.get("type") == "text":
                        text_parts.append(item["text"])
                    elif item.get("type") == "image_url":
                        url = item["image_url"]["url"]
                        try:
                            filename, content = await self.content_extractor.extract_content_from_url(url, session)
                            extracted_data.append({"file": filename, "content_extracted": content})
                        except:
                            extracted_data.append({"file": url, "content_extracted": "Error extracting content"})
                processed_content = ""
                if extracted_data:
                  processed_content += json.dumps(extracted_data, indent=2) + "\n"
                
                if text_parts:
                  processed_content += "\n".join(text_parts)
                processed_messages.append({
                    "role": message["role"],
                    "content": processed_content
                })
            else:
                processed_messages.append(message)
        await session.close()
        return processed_messages
    
rag_system = MessageProcessor()