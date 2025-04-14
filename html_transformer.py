"""
Enhanced AEM Component Transformer Module

Features:
1. HTML sanitization with allowed attributes
2. Component blacklisting via exclude_selectors
3. Depth limiting for component processing
"""

import re
import requests
import logging
import time
import os
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag, Comment
from config_loader import ConfigLoader
from aem_uploader import AEMUploader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HTMLComponentTransformer:
    """
    Transforms HTML markup into nested AEM components with safety features.
    
    Attributes:
        config (dict): Configuration from ConfigLoader
        soup (BeautifulSoup): Parsed and sanitized HTML structure
        component_definitions (dict): Component definitions from config
        processing_rules (dict): Sanitization and processing rules
    """
    
    def __init__(self, html_markup: str):
        """
        Initialize transformer with HTML content and configuration
        
        Args:
            html_markup: HTML content to process (string)
        """
        self.config = ConfigLoader()
        self.aem_config = self.config.get('aem', {})
        self.processing_rules = self.config.get('processing_rules', {})
        self.soup = BeautifulSoup(html_markup, 'html.parser')
        self._aem_uploader = self._init_aem_uploader()
        self._image_config = self.config.get('aem_images', {})
        self.component_definitions = self.config.get('components', {})
        self._current_depth = 0
        # Parse and sanitize HTML upfront and Process images during sanitization
        self._sanitize_html(self.soup)

    def _init_aem_uploader(self):
        """Initialize AEM upload helper if configured"""
        if self.aem_config.get('enabled', False):
            return AEMUploader()
        return None

    def _sanitize_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Clean HTML elements by:
        - Removing blacklisted elements
        - Stripping unwanted attributes
        - Removing comments and scripts
        """
        # Remove blacklisted elements first
        for selector in self.processing_rules.get('exclude_selectors', []):
            for element in soup.select(selector):
                element.decompose()

        # Remove comments and scripts
        for element in soup.find_all(string=lambda text: isinstance(text, Comment)):
            element.extract()

        for element in soup.find_all('script'):
            element.decompose()

        # Clean attributes
        allowed_attrs = self.processing_rules.get(
            'allowed_attributes', 
            {'class', 'id', 'src', 'alt', 'href', 'title'}
        )
        
        for tag in soup.find_all(True):
            tag.attrs = {
                k: v for k, v in tag.attrs.items() 
                if k in allowed_attrs
            }

        # Add image processing after basic sanitization
        if self._aem_uploader:
            self._process_and_replace_images(soup)
            
        return soup

    def _process_and_replace_images(self, soup: BeautifulSoup):
        """Process all images and update their sources"""
        for img in soup.find_all('img'):
            original_src = img.get('src')
            if not original_src:
                continue

            try:
                # Download original image
                img_content, content_type = self._download_image(original_src)
                if not img_content:
                    continue

                # Generate AEM DAM path
                dam_path = self._generate_dam_path(img)
                
                # Upload to AEM and update src
                if self._aem_uploader.upload_asset(dam_path, img_content, content_type):
                    img['src'] = dam_path
                    logger.info(f"Replaced the old image {original_src} source with new image {dam_path}")

            except Exception as e:
                logger.error(f"Image processing failed: {str(e)}")
                continue
    
    def _generate_dam_path(self, img: Tag) -> str:
        """
        Generate AEM DAM path from image metadata
        Example Input: <img src="image.png" alt="Sample Image">
        Example Output: /content/dam/project/sample-image.png
        """
        # Get configuration values
        base_path = self._image_config.get('base_path', '/content/dam/project')
        # intermediate_folders = self._image_config.get('intermediate_folders', [])
        intermediate_folders = []
        
        # Extract source filename components
        original_src = img.get('src', '')
        src_basename = os.path.basename(original_src)
        src_name, src_ext = os.path.splitext(src_basename)
        
        # Determine base name from alt text or source filename
        alt_text = img.get('alt', '')
        base_name = self._sanitize_filename(alt_text) if alt_text \
                    else self._sanitize_filename(src_name)
        
        # Construct full filename with original extension
        filename = f"{base_name}{src_ext.lower()}"
        
        # Build full DAM path
        path_components = [base_path.strip('/')] + intermediate_folders + [filename]
        return '/' + '/'.join(path_components)

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Convert to kebab-case filename with extension"""
        name = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
        name = re.sub(r'[\s_]+', '-', name).lower()
        return f"{name[:150]}"  # Truncate long filenames

    def _download_image(self, url: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Download image with retry logic"""
        retries = self._image_config.get('retries', 3)
        timeout = self._image_config.get('timeout', 15)
        retry_delay = self._image_config.get('retry_delay', 3)
        for attempt in range(retries + 1):
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response.content, response.headers.get('Content-Type')
            except Exception as e:
                logger.warning(f"Retry {attempt+1}/{retries} for {url}: error {str(e)}")
                time.sleep(retry_delay)
        return None, None

    def manipulate(self, actions: List[Dict]) -> None:
        """
        Modify HTML structure before processing.
        
        Args:
            actions: List of manipulation instructions
                Example: [{
                    'action': 'remove_attribute',
                    'selector': 'div.accordion',
                    'params': {'attributes': ['data-old']}
                }]
        """
        action_map = {
            'add_before': self._add_before,
            'add_after': self._add_after,
            'update_element': self._update_element,
            'replace_element': self._replace_element,
            'remove_element': self._remove_element,
            'clear_content': self._clear_content,
            'add_attribute': self._add_attribute,
            'remove_attributes': self._remove_attributes,
            'remove_attributes_with_values': self._remove_attributes_with_values
        }
        
        for action in actions:
            elements = self.soup.select(action['selector'])
            for element in elements:
                action_map[action['action']](element, **action.get('params', {}))

    # HTML manipulation methods
    def _add_before(self, element: Tag, content: str) -> None:
        """Insert HTML content before element"""
        element.insert_before(BeautifulSoup(content, 'html.parser'))

    def _add_after(self, element: Tag, content: str) -> None:
        """Insert HTML content after element"""
        element.insert_after(BeautifulSoup(content, 'html.parser'))

    def _update_element(self, element: Tag, content: str) -> None:
        """Replace element's inner HTML"""
        element.clear()
        element.append(BeautifulSoup(content, 'html.parser'))

    def _replace_element(self, element: Tag, new_tag: str) -> None:
        """Replace element with new tag"""
        new_element = self.soup.new_tag(new_tag)
        element.replace_with(new_element)

    def _remove_element(self, element: Tag) -> None:
        """Remove element from DOM"""
        element.decompose()

    def _clear_content(self, element: Tag) -> None:
        """Clear element's content"""
        element.clear()

    def _add_attribute(self, element: Tag, name: str, value: str) -> None:
        """Add/update element attribute"""
        element[name] = value

    def _remove_attributes(self, element: Tag, attributes: List[str]) -> None:
        """Remove specified attributes"""
        for attr in attributes:
            if attr in element.attrs:
                del element[attr]

    def _remove_attributes_with_values(self, element: Tag, attributes: Dict[str, str]) -> None:
        """Remove attributes matching specific values"""
        for attr, value in attributes.items():
            if element.get(attr) == value:
                del element[attr]

 
    def to_component_json(self) -> Dict[str, Any]:
        """
        Convert HTML to AEM component JSON with safety constraints
        
        Returns:
            dict: Component hierarchy in AEM JSON format
        """
        # return self._process_element(self.soup, depth=0)
        return self.soup

    def _process_element(
        self, 
        element: Tag, 
        depth: int
    ) -> Optional[Dict[str, Any]]:
        """
        Recursively process HTML element with depth limiting
        
        Args:
            element: BeautifulSoup element to process
            depth: Current recursion depth
            
        Returns:
            Component JSON structure or None if excluded/over depth
        """
        # Depth check
        max_depth = self.processing_rules.get('max_depth', 5)
        if depth > max_depth:
            return None

        # Check if element should be excluded
        if self._is_element_excluded(element):
            return None

        # Identify component
        component = self._identify_component(element)
        if not component:
            return None

        # Build component JSON
        component_json = {
            'componentType': component['name'],
            'resourceType': self.config.get('resource_types', {}).get(component['name']),
            'properties': self._extract_properties(element, component),
            'children': []
        }

        # Process children with depth tracking
        for child in element.children:
            if isinstance(child, Tag):
                child_component = self._process_element(child, depth + 1)
                if child_component:
                    component_json['children'].append(child_component)

        return component_json

    def _is_element_excluded(self, element: Tag) -> bool:
        """Check if element matches any exclusion selector"""
        exclude_selectors = self.processing_rules.get('exclude_selectors', [])
        return any(element.select(s) for s in exclude_selectors)

    def _identify_component(self, element: Tag) -> Optional[Dict]:
        """
        Identify component type for element using config rules
        
        Args:
            element: Element to identify
            
        Returns:
            Matched component definition or None
        """
        for name, definition in self.component_definitions.items():
            if any(element.select(s) for s in definition['selectors']):
                return {'name': name, **definition}
        return None

    def _extract_properties(self, element: Tag, component: Dict) -> Dict[str, Any]:
        """
        Extract component properties based on config mapping
        
        Args:
            element: Source HTML element
            component: Component definition
            
        Returns:
            Dictionary of component properties
        """
        properties = {}
        for prop, selector in component.get('property_map', {}).items():
            target = element.select_one(selector)
            if target:
                if '[' in selector:  # Attribute selector
                    attr = selector.split('[')[1].split(']')[0].split('=')[0]
                    properties[prop] = target.get(attr, '')
                elif target.name in ['img', 'iframe']:  # Media elements
                    properties[prop] = target.get('src', '')
                else:  # Text content
                    properties[prop] = target.get_text(separator=' ', strip=True)
        return properties

# Example usage
# if __name__ == "__main__":
#     html = '''
#     <div class="accordionparagraph">
#         <div class="accordion-header">Main Title</div>
#         <div class="accordion-body">
#             <div class="type_paragraph">
#                 <p>Sample text with <img src="image.jpg" alt="Example"> and
#                 <iframe src="https://youtube.com/embed/123"></iframe></p>
#             </div>
#             <table><tr><td>Data</td></tr></table>
#         </div>
#     </div>
#     '''
    
#     transformer = HTMLComponentTransformer(html)
    
#     # Optional HTML manipulations
#     transformer.manipulate([
#         {
#             'action': 'remove_attributes',
#             'selector': 'div.accordion-header',
#             'params': {'attributes': ['data-old-attr']}
#         }
#     ])
    
#     # Generate component JSON
#     component_json = transformer.to_component_json()
#     print(json.dumps(component_json, indent=2))