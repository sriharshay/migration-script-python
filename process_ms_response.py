from bs4 import BeautifulSoup
from typing import List, Dict, Any
from html_transformer import HTMLComponentTransformer
import json

class JsonResponse:
    """Class to process and transform JSON response data"""
    
    def __init__(self, data: Dict[str, Any]):
        self.raw_data = data
        self.processed_data = {}
        self._create_generic_methods()
        self._process_special_properties()
        
    def _create_generic_methods(self):
        """Create methods for generic properties"""
        for key in self.raw_data.keys():
            if key not in ['body', 'suggestedQuestionsList', 'title']:
                self._process_generic_property(key)
                
    def _process_generic_property(self, key: str):
        """Process generic properties with truncation"""
        value = str(self.raw_data.get(key, ''))
        self.processed_data[key] = value[:20] + '...' if len(value) > 20 else value
        
    def _process_special_properties(self):
        """Handle special properties with custom processing"""
        self._process_title()
        self._process_body()
        self._process_questions()
        
    def _process_title(self):
        """Special handling for title property"""
        title = self.raw_data.get('title')
        if not title:
            title = "Untitled Article"
        self.processed_data['title'] = str(title)
        
    def _process_body(self):
        """HTML body processing with BeautifulSoup"""
        body = self.raw_data.get('body', '')
        self.processed_data['body'] = body
        """
        soup = BeautifulSoup(body, 'html.parser')
        self.processed_data['body'] = {
            'element_count': len(soup.find_all()),
            'main_tag': soup.find().name if soup.find() else None
        }
        """
        # TODO: Identify the component
        transformer = HTMLComponentTransformer(body)

        # Optional HTML manipulations
        transformer.manipulate([
            {'action': 'remove_element', 'selector': 'div.old-component'},
            {'action': 'add_attribute', 'selector': 'img', 'params': {'name': 'data-src', 'value': 'image.jpg'}}
        ])

        # Generate component JSON
        component_json = transformer.to_component_json()
        print(json.dumps(component_json, indent=2))
        
    def _process_questions(self):
        """Suggested questions processing"""
        questions = self.raw_data.get('suggestedQuestionsList', [])
        if not isinstance(questions, list):
            self.processed_data['suggestedQuestionsList'] = {'error': 'Invalid format'}
            return
            
        self.processed_data['suggestedQuestionsList'] = [
            q for q in questions[:1]  # Limit to first 3 questions
            if isinstance(q, dict) # If the object is a key, value pair
        ]
        
    def to_dict(self) -> Dict[str, Any]:
        """Return processed data as dictionary"""
        return self.processed_data

class MSResponseHandler:
    """Main class to handle JSON response processing"""
    
    def __init__(self, response_json: Dict[str, Any]):
        self.response_json = response_json
        self.processed_articles: List[Dict[str, Any]] = []
        self._validate_and_process()
        
    def _validate_and_process(self):
        """Validate response structure and process data"""
        if not self._validate_json_structure():
            return
            
        status_code = self.response_json['statusCode']
        if status_code != 200:
            print(f"Error {status_code}: {self.response_json.get('result', 'Unknown error')}")
            return
            
        result = self.response_json['result']
        if not isinstance(result, list):
            print("Error: Result is not an array")
            return
            
        for item in result:
            if not isinstance(item, dict):
                continue
            processor = JsonResponse(item)
            self.processed_articles.append(processor.to_dict())
            
    def _validate_json_structure(self) -> bool:
        """Validate basic JSON structure"""
        required_keys = {'statusCode', 'result'}
        if not required_keys.issubset(self.response_json.keys()):
            print("Error: Invalid JSON structure")
            return False
        return True
        
    def get_processed_json(self) -> str:
        """Return processed data"""
        return self.processed_articles