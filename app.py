"""
Newsletter Builder - Streamlit Application
A web application for generating responsive HTML newsletters with dynamic content layers.
"""

import base64
import io
import time
from typing import Dict, List, Optional

import streamlit as st
from PIL import Image
from streamlit_quill import st_quill
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError


class MongoManager:
    """Manages MongoDB connection and operations for newsletter templates."""
    
    def __init__(self, connection_string: str = "mongodb://mongo:27017/", 
                 database_name: str = "newsletter_db", 
                 collection_name: str = "templates"):
        """
        Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database
            collection_name: Name of the collection
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
    
    def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.server_info()
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            # Create unique index on 'name' field
            self.collection.create_index("name", unique=True)
            return True
        except ConnectionFailure:
            return False
        except Exception as e:
            st.error(f"Error connecting to MongoDB: {str(e)}")
            return False
    
    def save_template(self, name: str, config: dict, header_config: dict, 
                     layers: list, footer_config: dict, 
                     subscription_config: Optional[dict] = None) -> bool:
        """
        Save or update a newsletter template.
        
        Args:
            name: Unique template name
            config: Basic configuration (subject, colors, etc.)
            header_config: Header configuration
            layers: List of layer dictionaries
            footer_config: Footer configuration
            subscription_config: Subscription configuration (optional)
            
        Returns:
            True if save successful, False otherwise
        """
        if self.collection is None:
            if not self.connect():
                return False
        
        try:
            template_data = {
                'name': name,
                'config': config,
                'header_config': header_config,
                'layers': layers,
                'footer_config': footer_config,
                'subscription_config': subscription_config
            }
            
            # Use upsert to update if exists, insert if not
            self.collection.update_one(
                {'name': name},
                {'$set': template_data},
                upsert=True
            )
            return True
        except DuplicateKeyError:
            st.error(f"Template name '{name}' already exists. Please use a different name.")
            return False
        except Exception as e:
            st.error(f"Error saving template: {str(e)}")
            return False
    
    def load_templates(self) -> List[str]:
        """
        Get list of all saved template names.
        
        Returns:
            List of template names
        """
        if self.collection is None:
            if not self.connect():
                return []
        
        try:
            templates = self.collection.find({}, {'name': 1, '_id': 0})
            return [template['name'] for template in templates]
        except Exception as e:
            st.error(f"Error loading templates: {str(e)}")
            return []
    
    def load_template_data(self, name: str) -> Optional[dict]:
        """
        Load template data by name.
        
        Args:
            name: Template name to load
            
        Returns:
            Dictionary with template data or None if not found
        """
        if self.collection is None:
            if not self.connect():
                return None
        
        try:
            template = self.collection.find_one({'name': name})
            if template:
                # Remove MongoDB _id from result
                template.pop('_id', None)
                return template
            return None
        except Exception as e:
            st.error(f"Error loading template: {str(e)}")
            return None
    
    def delete_template(self, name: str) -> bool:
        """
        Delete a template by name.
        
        Args:
            name: Template name to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        if self.collection is None:
            if not self.connect():
                return False
        
        try:
            result = self.collection.delete_one({'name': name})
            return result.deleted_count > 0
        except Exception as e:
            st.error(f"Error deleting template: {str(e)}")
            return False
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()


# Global MongoDB manager instance
_mongo_manager = None


def get_mongo_manager() -> MongoManager:
    """Get or create global MongoDB manager instance."""
    global _mongo_manager
    if _mongo_manager is None:
        _mongo_manager = MongoManager()
    return _mongo_manager


class ImageProcessor:
    """Handles image processing and Base64 encoding for newsletter embedding."""

    @staticmethod
    def convert_to_base64(image_file) -> Optional[str]:
        """
        Convert uploaded image file to Base64 string.
        
        Args:
            image_file: Streamlit UploadedFile object
            
        Returns:
            Base64 encoded string with data URI prefix, or None if conversion fails
        """
        if image_file is None:
            return None
        
        try:
            # Open image with Pillow
            img = Image.open(image_file)
            
            # Determine if original is PNG to preserve transparency
            is_png = image_file.type in ['image/png', 'image/PNG'] or img.format == 'PNG'
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            
            if is_png:
                # Preserve PNG format and transparency (RGBA mode)
                if img.mode not in ('RGBA', 'LA', 'P'):
                    # Convert to RGBA if not already, preserving transparency
                    if img.mode == 'RGB':
                        img = img.convert('RGBA')
                    else:
                        img = img.convert('RGBA')
                img.save(buffer, format='PNG', optimize=True)
                mime_type = 'image/png'
            else:
                # Convert to RGB for JPEG (no transparency support)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(buffer, format='JPEG', quality=95)
                mime_type = 'image/jpeg'
            
            buffer.seek(0)
            
            # Encode to Base64
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            return f"data:{mime_type};base64,{img_base64}"
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
            return None


class NewsletterGenerator:
    """Generates HTML newsletter structure with inline CSS for email compatibility."""
    
    @staticmethod
    def generate_html(
        subject: str,
        background_color: str,
        text_color: str,
        header_config: Dict,
        layers: List[Dict],
        footer_config: Dict,
        subscription_config: Dict = None,
        max_width: int = 1000,
        font_family: str = "Oswald, sans-serif"
    ) -> str:
        """
        Generate complete HTML newsletter with inline CSS.
        
        Args:
            subject: Email subject line
            background_color: Background color hex code
            text_color: Primary text color hex code
            header_config: Dictionary with header configuration
            layers: List of layer dictionaries containing content data
            footer_config: Dictionary with footer configuration
            subscription_config: Dictionary with subscription configuration (optional)
            max_width: Maximum width of the newsletter in pixels
            font_family: Font family for the newsletter text
            
        Returns:
            Complete HTML string ready for email
        """
        # Check if Oswald font is selected and add Google Fonts link
        include_google_fonts = 'Oswald' in font_family
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            f'<meta charset="UTF-8">',
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'<title>{subject}</title>',
        ]
        
        # Add Google Fonts link if Oswald is selected
        if include_google_fonts:
            html_parts.append('<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@200;300;400;500;600;700&display=swap" rel="stylesheet">')
        
        html_parts.extend([
            '</head>',
            f'<body style="margin: 0; padding: 0; font-family: {font_family}; background-color: #FFFFFF;">',
            '<table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #FFFFFF;">',
            '<tr>',
            '<td align="center" style="padding: 20px 0;">',
            f'<table role="presentation" style="width: {max_width}px; max-width: 100%; border-collapse: collapse; '
            f'background-color: {background_color}; margin: 0 auto;">',
        ])

        html_parts.extend(NewsletterGenerator._generate_header_html(subject, header_config))
        
        # Add each layer
        for layer in layers:
            html_parts.extend(NewsletterGenerator._generate_layer_html(layer, text_color))

        # Add footer section
        html_parts.extend(NewsletterGenerator._generate_footer_html(footer_config))
        
        # Add subscription section if configured
        if subscription_config:
            html_parts.extend(NewsletterGenerator._generate_subscription_html(subscription_config))
        
        # Close tables and body
        html_parts.extend([
            '</table>',
            '</td>',
            '</tr>',
            '</table>',
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    @staticmethod
    def _generate_layer_html(layer: Dict, text_color: str) -> List[str]:
        """
        Generate HTML for a single content layer with image on left or right.
        
        Args:
            layer: Dictionary containing layer content (title, subtitle, subtitle2, content, image, alignment, etc.)
            text_color: Primary text color hex code (for content)
            
        Returns:
            List of HTML strings for the layer
        """
        html_parts = []
        
        # Get layer configuration
        padding = layer.get('padding', 30)
        image_alignment = layer.get('image_alignment', 'left').lower()
        # Get image source - check both URL and Base64, prefer non-empty values
        image_url = layer.get('image_url')
        image_base64 = layer.get('image_base64')
        # Determine which image source to use (URL takes precedence if both exist)
        if image_url and image_url.strip():
            image_src = image_url.strip()
        elif image_base64:
            image_src = image_base64
        else:
            image_src = None
        image_width = layer.get('image_width', 210)
        
        title = layer.get('title', '')
        subtitle = layer.get('subtitle', '')
        subtitle2 = layer.get('subtitle2', '')
        content = layer.get('content', '')
        
        title_color = layer.get('title_color', text_color)
        subtitle_color = layer.get('subtitle_color', '#00925b')  # Green by default
        subtitle2_color = layer.get('subtitle2_color', text_color)
        
        title_font_size = layer.get('title_font_size', 21)
        subtitle_font_size = layer.get('subtitle_font_size', 15)
        subtitle2_font_size = layer.get('subtitle2_font_size', 13)
        
        title_bold = layer.get('title_bold', True)
        subtitle_bold = layer.get('subtitle_bold', True)
        subtitle2_bold = layer.get('subtitle2_bold', False)
        
        content_font_size = layer.get('content_font_size', 13)
        content_color = layer.get('content_color', '#000000')
        
        # Get link URL if provided
        link_url = layer.get('link_url', '').strip()
        has_link = bool(link_url)
        
        # Layer container with padding
        html_parts.append('<tr>')
        html_parts.append(f'<td style="padding: {padding}px 20px;">')
        
        # Create table for image and text layout
        html_parts.append('<table role="presentation" style="width: 100%; border-collapse: collapse;">')
        html_parts.append('<tr>')
        
        # Image on left or right
        if image_src and image_src.strip() and image_alignment == 'left':
            # Image column (left) - wrap in link if provided (Outlook compatible)
            if has_link:
                html_parts.append(f'<td style="vertical-align: top; padding-right: 20px; width: {image_width}px; background-color: transparent;">')
                html_parts.append(f'<a href="{link_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block;">')
                html_parts.append(
                    f'<img src="{image_src}" alt="{title or "Layer Image"}" '
                    f'width="{image_width}" style="width: {image_width}px; max-width: 100%; height: auto; display: block; border: 0; outline: none; background-color: transparent;">'
                )
                html_parts.append('</a>')
                html_parts.append('</td>')
            else:
                html_parts.append(f'<td style="vertical-align: top; padding-right: 20px; width: {image_width}px; background-color: transparent;">')
                html_parts.append(
                    f'<img src="{image_src}" alt="{title or "Layer Image"}" '
                    f'width="{image_width}" style="width: {image_width}px; max-width: 100%; height: auto; display: block; border: 0; outline: none; background-color: transparent;">'
                )
                html_parts.append('</td>')
            
            # Text column (right) - wrap in link if provided (Outlook compatible)
            html_parts.append('<td style="vertical-align: top;">')
            if has_link:
                html_parts.append(f'<a href="{link_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block;">')
            html_parts.extend(NewsletterGenerator._generate_layer_text(
                title, subtitle, subtitle2, content,
                title_color, subtitle_color, subtitle2_color, content_color,
                title_font_size, subtitle_font_size, subtitle2_font_size, content_font_size,
                title_bold, subtitle_bold, subtitle2_bold
            ))
            if has_link:
                html_parts.append('</a>')
            html_parts.append('</td>')
            
        elif image_src and image_src.strip() and image_alignment == 'right':
            # Text column (left) - wrap in link if provided (Outlook compatible)
            html_parts.append('<td style="vertical-align: top; padding-right: 20px;">')
            if has_link:
                html_parts.append(f'<a href="{link_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block;">')
            html_parts.extend(NewsletterGenerator._generate_layer_text(
                title, subtitle, subtitle2, content,
                title_color, subtitle_color, subtitle2_color, content_color,
                title_font_size, subtitle_font_size, subtitle2_font_size, content_font_size,
                title_bold, subtitle_bold, subtitle2_bold
            ))
            if has_link:
                html_parts.append('</a>')
            html_parts.append('</td>')
            
            # Image column (right) - wrap in link if provided (Outlook compatible)
            if has_link:
                html_parts.append(f'<td style="vertical-align: top; width: {image_width}px; background-color: transparent;">')
                html_parts.append(f'<a href="{link_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block;">')
                html_parts.append(
                    f'<img src="{image_src}" alt="{title or "Layer Image"}" '
                    f'width="{image_width}" style="width: {image_width}px; max-width: 100%; height: auto; display: block; border: 0; outline: none; background-color: transparent;">'
                )
                html_parts.append('</a>')
                html_parts.append('</td>')
            else:
                html_parts.append(f'<td style="vertical-align: top; width: {image_width}px; background-color: transparent;">')
                html_parts.append(
                    f'<img src="{image_src}" alt="{title or "Layer Image"}" '
                    f'width="{image_width}" style="width: {image_width}px; max-width: 100%; height: auto; display: block; border: 0; outline: none; background-color: transparent;">'
                )
                html_parts.append('</td>')
        else:
            # No image, just text - wrap in link if provided (Outlook compatible)
            html_parts.append('<td style="vertical-align: top; width: 100%;">')
            if has_link:
                html_parts.append(f'<a href="{link_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block;">')
            html_parts.extend(NewsletterGenerator._generate_layer_text(
                title, subtitle, subtitle2, content,
                title_color, subtitle_color, subtitle2_color, content_color,
                title_font_size, subtitle_font_size, subtitle2_font_size, content_font_size,
                title_bold, subtitle_bold, subtitle2_bold
            ))
            if has_link:
                html_parts.append('</a>')
            html_parts.append('</td>')
        
        html_parts.append('</tr>')
        html_parts.append('</table>')
        
        # Close layer container
        html_parts.append('</td>')
        html_parts.append('</tr>')
        
        return html_parts
    
    @staticmethod
    def _generate_layer_text(
        title: str, subtitle: str, subtitle2: str, content: str,
        title_color: str, subtitle_color: str, subtitle2_color: str, content_color: str,
        title_font_size: int, subtitle_font_size: int, subtitle2_font_size: int, content_font_size: int,
        title_bold: bool, subtitle_bold: bool, subtitle2_bold: bool
    ) -> List[str]:
        """Generate HTML for layer text content (titles and body)."""
        html_parts = []
        
        # Determine font-weight based on bold setting
        title_weight = '700' if title_bold else '400'
        subtitle_weight = '600' if subtitle_bold else '400'
        subtitle2_weight = '500' if subtitle2_bold else '400'
        
        # Title (H2)
        if title:
            html_parts.append(
                f'<h2 style="color: {title_color}; margin: 0 0 10px 0; font-size: {title_font_size}px; font-weight: {title_weight}; line-height: 1.2;">'
                f'{title}</h2>'
            )
        
        # Subtitle (H3) - Green/accent color
        if subtitle:
            html_parts.append(
                f'<h3 style="color: {subtitle_color}; margin: 0 0 10px 0; font-size: {subtitle_font_size}px; font-weight: {subtitle_weight}; line-height: 1.4;">'
                f'{subtitle}</h3>'
            )
        
        # Subtitle 2 (H4) - Third title
        if subtitle2:
            html_parts.append(
                f'<h4 style="color: {subtitle2_color}; margin: 0 0 15px 0; font-size: {subtitle2_font_size}px; font-weight: {subtitle2_weight}; line-height: 1.4;">'
                f'{subtitle2}</h4>'
            )
        
        # Main content
        if content:
            # Check if content is HTML (from rich text editor)
            if '<' in content and '>' in content:
                # Content is HTML from the editor (usually starts with <p>)
                # Wrap it in a container with base styles (color and font-size)
                # This allows inline styles (like specific word colors) to override the base
                html_parts.append(
                    f'<div style="color: {content_color}; font-size: {content_font_size}px; margin: 0; line-height: 1.5;">'
                )
                html_parts.append(content)
                html_parts.append('</div>')
            else:
                # Plain text, convert newlines to <br> tags
                formatted_content = content.replace('\n', '<br>')
                html_parts.append(
                    f'<p style="color: {content_color}; margin: 0; font-size: {content_font_size}px; line-height: 1.5;">{formatted_content}</p>'
                )
        
        return html_parts

    @staticmethod
    def _generate_header_html(subject: str, header_config: Dict) -> List[str]:
        """
        Generates the pre-header (hidden text) and main header section.
        Structure: Image -> Blank Space -> Title -> Text
        
        Args:
            subject: Email subject line
            header_config: Dictionary with header configuration including image, title, text, sizes
        """
        html_parts = []

        # 1. Pre-Header Text (Hidden text for email preview) - Only if provided
        pre_header_text = header_config.get('pre_header_text', '').strip()
        if pre_header_text:  # Only include if the user fills it
            html_parts.append('<tr>')
            # Email styles to hide text but make it readable for pre-header
            html_parts.append(
                '<td style="padding: 0; font-size: 0; line-height: 0; display: none !important; '
                'max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden; mso-hide: all;">'
            )
            html_parts.append(
                f'<span style="font-size: 1px; color: #ffffff; line-height: 1px;">{pre_header_text}</span>'
            )
            html_parts.append('</td>')
            html_parts.append('</tr>')
        
        # 2. Main Header Structure
        header_title = header_config.get('header_title', '').strip()
        if not header_title:  # If no title, use subject as fallback
            header_title = subject
        header_text = header_config.get('header_text', '').strip()
        header_image_base64 = header_config.get('header_image_base64')
        header_image_url = header_config.get('header_image_url')
        header_bg_color = header_config.get('header_bg_color', '#ffffff')
        image_width = header_config.get('image_width', 600)
        
        title_font_size = header_config.get('title_font_size', 28)
        title_color = header_config.get('title_color', '#000000')
        title_bold = header_config.get('title_bold', True)
        
        text_font_size = header_config.get('text_font_size', 16)
        text_color = header_config.get('text_color', '#000000')
        
        # Font weights
        title_weight = '700' if title_bold else '400'
        
        # Determine image source
        image_src = None
        if header_image_base64:
            image_src = header_image_base64
        elif header_image_url:
            image_src = header_image_url
        
        # 2.1. Image Row (if image provided)
        if image_src:
            html_parts.append('<tr>')
            html_parts.append('<td style="padding: 0; margin: 0;">')
            html_parts.append(
                f'<img src="{image_src}" alt="{header_title}" '
                f'style="width: 100%; max-width: {image_width}px; height: auto; display: block; margin: 0; padding: 0;">'
            )
            html_parts.append('</td>')
            html_parts.append('</tr>')
        
        # 2.2. Blank Space Row
        html_parts.append('<tr>')
        html_parts.append(f'<td style="padding: 20px 20px; background-color: {header_bg_color};">')
        html_parts.append('&nbsp;')  # Blank space
        html_parts.append('</td>')
        html_parts.append('</tr>')
        
        # 2.3. Title Row
        if header_title:
            html_parts.append('<tr>')
            html_parts.append(f'<td style="padding: 0 20px 10px 20px; background-color: {header_bg_color};">')
            html_parts.append(
                f'<h1 style="color: {title_color}; font-size: {title_font_size}px; margin: 0; font-weight: {title_weight}; line-height: 1.3;">{header_title}</h1>'
            )
            html_parts.append('</td>')
            html_parts.append('</tr>')
        
        # 2.4. Header Text Row
        if header_text:
            html_parts.append('<tr>')
            html_parts.append(f'<td style="padding: 0 20px 20px 20px; background-color: {header_bg_color};">')
            
            # Check if header_text is HTML (from rich text editor)
            if '<' in header_text and '>' in header_text:
                # Content is HTML from the editor (usually starts with <p>)
                # Wrap it in a container with base styles (color and font-size)
                # This allows inline styles (like specific word colors) to override the base
                html_parts.append(
                    f'<div style="color: {text_color}; font-size: {text_font_size}px; margin: 0; line-height: 1.5;">'
                )
                html_parts.append(header_text)
                html_parts.append('</div>')
            else:
                # Plain text, convert newlines to <br> tags
                formatted_text = header_text.replace('\n', '<br>')
                html_parts.append(
                    f'<p style="color: {text_color}; font-size: {text_font_size}px; margin: 0; line-height: 1.5;">{formatted_text}</p>'
                )
            
            html_parts.append('</td>')
            html_parts.append('</tr>')

        return html_parts

    @staticmethod
    def _generate_footer_html(footer_config: Dict) -> List[str]:
        """
        Generates the footer section with company info, image, and social media links.
        Similar structure to header but for footer.
        
        Args:
            footer_config: Dictionary with footer configuration including image, company info, social media
        """
        html_parts = []
        
        footer_bg_color = footer_config.get('footer_bg_color', '#ffffff')
        footer_image_base64 = footer_config.get('footer_image_base64')
        footer_image_url = footer_config.get('footer_image_url')
        footer_image_position = footer_config.get('footer_image_position', 'Above Text')
        image_width = footer_config.get('image_width', 600)
        footer_alignment = footer_config.get('footer_alignment', 'left').lower()
        
        company_name = footer_config.get('company_name', '')
        company_name_color = footer_config.get('company_name_color', '#000000')
        company_name_size = footer_config.get('company_name_size', 12)
        company_name_bold = footer_config.get('company_name_bold', False)
        
        address = footer_config.get('address', '')
        address_color = footer_config.get('address_color', '#000000')
        address_size = footer_config.get('address_size', 12)
        address_bold = footer_config.get('address_bold', False)
        
        directors = footer_config.get('directors', '')
        directors_color = footer_config.get('directors_color', '#000000')
        directors_size = footer_config.get('directors_size', 12)
        directors_bold = footer_config.get('directors_bold', False)
        
        # Determine image source
        image_src = None
        if footer_image_base64:
            image_src = footer_image_base64
        elif footer_image_url:
            image_src = footer_image_url
        
        # Alignment styles for entire footer
        align_style = {
            'left': 'text-align: left;',
            'center': 'text-align: center;',
            'right': 'text-align: right;'
        }.get(footer_alignment, 'text-align: left;')
        
        # Font weights
        company_name_weight = '700' if company_name_bold else '400'
        address_weight = '700' if address_bold else '400'
        directors_weight = '700' if directors_bold else '400'
        
        # Helper to append image respecting link
        def _append_footer_image():
            if not image_src:
                return
            html_parts.append('<div style="margin-bottom: 20px;">')
            footer_image_link_url = footer_config.get('footer_image_link_url', '')
            if footer_image_link_url and footer_image_link_url.strip():
                html_parts.append(
                    f'<a href="{footer_image_link_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; display: inline-block;">'
                )
            html_parts.append(
                f'<img src="{image_src}" alt="{company_name or "Footer Image"}" '
                f'width="{image_width}" style="width: {image_width}px; max-width: 100%; height: auto; display: inline-block; border: 0; outline: none; background-color: transparent;">'
            )
            if footer_image_link_url and footer_image_link_url.strip():
                html_parts.append('</a>')
            html_parts.append('</div>')
        
        # Footer container with alignment
        html_parts.append('<tr>')
        html_parts.append(f'<td style="padding: 30px 20px; background-color: {footer_bg_color}; {align_style}">')
        
        # Image before text
        if footer_image_position == 'Above Text':
            _append_footer_image()
        
        # Company information
        if company_name or address or directors:
            html_parts.append('<div style="margin-bottom: 15px;">')
            
            if company_name:
                html_parts.append(
                    f'<p style="color: {company_name_color}; margin: 0 0 10px 0; font-size: {company_name_size}px; font-weight: {company_name_weight}; line-height: 1.5;">{company_name}</p>'
                )
            
            if address:
                formatted_address = address.replace('\n', '<br>')
                html_parts.append(
                    f'<p style="color: {address_color}; margin: 0 0 10px 0; font-size: {address_size}px; font-weight: {address_weight}; line-height: 1.5;">{formatted_address}</p>'
                )
            
            if directors:
                formatted_directors = directors.replace('\n', '<br>')
                html_parts.append(
                    f'<p style="color: {directors_color}; margin: 0 0 15px 0; font-size: {directors_size}px; font-weight: {directors_weight}; line-height: 1.5;">{formatted_directors}</p>'
                )
            
            html_parts.append('</div>')
        
        # Image after text (but before social media)
        if footer_image_position == 'After Text':
            _append_footer_image()
        
        # Social media links
        social_media_type = footer_config.get('social_media_type', 'URLs Only')
        social_image_width = footer_config.get('social_image_width', 30)
        
        facebook_url = footer_config.get('facebook_url', '')
        facebook_image_base64 = footer_config.get('facebook_image_base64')
        linkedin_url = footer_config.get('linkedin_url', '')
        linkedin_image_base64 = footer_config.get('linkedin_image_base64')
        xing_url = footer_config.get('xing_url', '')
        xing_image_base64 = footer_config.get('xing_image_base64')
        instagram_url = footer_config.get('instagram_url', '')
        instagram_image_base64 = footer_config.get('instagram_image_base64')
        
        social_links = []
        if social_media_type == "Images":
            # Use table-based layout for better Outlook compatibility
            # Each icon will be in its own table cell with padding for spacing
            # Outlook requires more explicit spacing, so we use larger cell width and separate spacing cells
            spacing_px = 10  # Spacing between icons in pixels (reduced since cells have extra width)
            # Cell width is larger than icon width to provide internal padding
            # This gives extra space around each icon for better visual separation
            cell_width = social_image_width + 5  # Add 5px extra to cell width (can be adjusted)
            
            if facebook_url and facebook_image_base64:
                social_links.append(
                    f'<td style="padding: 0; vertical-align: middle; text-align: center;" width="{cell_width}">'
                    f'<a href="{facebook_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; text-decoration: none;">'
                    f'<img src="{facebook_image_base64}" alt="Facebook" width="{social_image_width}" height="{social_image_width}" '
                    f'style="width: {social_image_width}px !important; height: {social_image_width}px !important; max-width: {social_image_width}px; max-height: {social_image_width}px; border: 0; outline: none; display: block; object-fit: contain;"></a>'
                    f'</td>'
                )
                # Add spacing cell after icon (except for the last one)
                if linkedin_url and linkedin_image_base64 or xing_url and xing_image_base64 or instagram_url and instagram_image_base64:
                    social_links.append(f'<td style="padding: 0; width: {spacing_px}px; font-size: 0; line-height: 0;" width="{spacing_px}">&nbsp;</td>')
            
            if linkedin_url and linkedin_image_base64:
                social_links.append(
                    f'<td style="padding: 0; vertical-align: middle; text-align: center;" width="{cell_width}">'
                    f'<a href="{linkedin_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; text-decoration: none;">'
                    f'<img src="{linkedin_image_base64}" alt="LinkedIn" width="{social_image_width}" height="{social_image_width}" '
                    f'style="width: {social_image_width}px !important; height: {social_image_width}px !important; max-width: {social_image_width}px; max-height: {social_image_width}px; border: 0; outline: none; display: block; object-fit: contain;"></a>'
                    f'</td>'
                )
                # Add spacing cell after icon (except for the last one)
                if xing_url and xing_image_base64 or instagram_url and instagram_image_base64:
                    social_links.append(f'<td style="padding: 0; width: {spacing_px}px; font-size: 0; line-height: 0;" width="{spacing_px}">&nbsp;</td>')
            
            if xing_url and xing_image_base64:
                social_links.append(
                    f'<td style="padding: 0; vertical-align: middle; text-align: center;" width="{cell_width}">'
                    f'<a href="{xing_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; text-decoration: none;">'
                    f'<img src="{xing_image_base64}" alt="Xing" width="{social_image_width}" height="{social_image_width}" '
                    f'style="width: {social_image_width}px !important; height: {social_image_width}px !important; max-width: {social_image_width}px; max-height: {social_image_width}px; border: 0; outline: none; display: block; object-fit: contain;"></a>'
                    f'</td>'
                )
                # Add spacing cell after icon (except for the last one)
                if instagram_url and instagram_image_base64:
                    social_links.append(f'<td style="padding: 0; width: {spacing_px}px; font-size: 0; line-height: 0;" width="{spacing_px}">&nbsp;</td>')
            
            if instagram_url and instagram_image_base64:
                social_links.append(
                    f'<td style="padding: 0; vertical-align: middle; text-align: center;" width="{cell_width}">'
                    f'<a href="{instagram_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; text-decoration: none;">'
                    f'<img src="{instagram_image_base64}" alt="Instagram" width="{social_image_width}" height="{social_image_width}" '
                    f'style="width: {social_image_width}px !important; height: {social_image_width}px !important; max-width: {social_image_width}px; max-height: {social_image_width}px; border: 0; outline: none; display: block; object-fit: contain;"></a>'
                    f'</td>'
                )
        else:
            if facebook_url:
                social_links.append(f'<a href="{facebook_url}" target="_blank" rel="noopener noreferrer" style="color: #999999; text-decoration: none; margin: 0 10px; display: inline-block;">Facebook</a>')
            if linkedin_url:
                social_links.append(f'<a href="{linkedin_url}" target="_blank" rel="noopener noreferrer" style="color: #999999; text-decoration: none; margin: 0 10px; display: inline-block;">LinkedIn</a>')
            if xing_url:
                social_links.append(f'<a href="{xing_url}" target="_blank" rel="noopener noreferrer" style="color: #999999; text-decoration: none; margin: 0 10px; display: inline-block;">Xing</a>')
            if instagram_url:
                social_links.append(f'<a href="{instagram_url}" target="_blank" rel="noopener noreferrer" style="color: #999999; text-decoration: none; margin: 0 10px; display: inline-block;">Instagram</a>')
        
        if social_links:
            social_media_label = footer_config.get('social_media_label', 'Die Social-Media-Kanäle der bfz gGmbH:')
            social_label_color = footer_config.get('social_label_color', '#000000')
            social_label_size = footer_config.get('social_label_size', 14)
            social_label_bold = footer_config.get('social_label_bold', True)
            social_label_weight = '700' if social_label_bold else '400'
            
            html_parts.append('<div style="margin-top: 20px;">')
            if social_media_label:
                html_parts.append(
                    f'<p style="color: {social_label_color}; margin: 0 0 10px 0; font-size: {social_label_size}px; font-weight: {social_label_weight};">{social_media_label}</p>'
                )
            # Use table layout for images (better Outlook compatibility), div for text links
            if social_media_type == "Images":
                html_parts.append('<table cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; border-spacing: 0;">')
                html_parts.append('<tr>')
                html_parts.extend(social_links)
                html_parts.append('</tr>')
                html_parts.append('</table>')
            else:
                html_parts.append('<div>')
                html_parts.extend(social_links)
                html_parts.append('</div>')
            html_parts.append('</div>')
        
        html_parts.append('</td>')
        html_parts.append('</tr>')
        
        return html_parts
    
    @staticmethod
    def _generate_subscription_html(subscription_config: Dict) -> List[str]:
        """
        Generates the subscription section with company info and unsubscribe link.
        
        Args:
            subscription_config: Dictionary with company_name, address, copyright_text, 
                          unsubscribe_link, view_online_link, disclaimer_text
        """
        footer_color = subscription_config.get('footer_color', "#999999")
        html_parts = []
        
        # Separador superior (usando estructura de tabla para compatibilidad con email)
        html_parts.append('<tr>')
        html_parts.append('<td style="padding: 20px 20px 10px 20px;">')
        html_parts.append('<table role="presentation" style="width: 100%; border-collapse: collapse;">')
        html_parts.append('<tr>')
        html_parts.append('<td style="height: 1px; background-color: #e0e0e0; line-height: 1px; font-size: 1px;">&nbsp;</td>')
        html_parts.append('</tr>')
        html_parts.append('</table>')
        html_parts.append('</td>')
        html_parts.append('</tr>')
        
        # Contenido del Footer
        html_parts.append('<tr>')
        html_parts.append(
            f'<td align="center" style="padding: 10px 20px 30px 20px; font-size: 12px; line-height: 18px; color: {footer_color};">'
        )
        
        # Disclaimer
        disclaimer = subscription_config.get('disclaimer_text', 'This email was sent to you because you subscribed to our newsletter.')
        if disclaimer:
            html_parts.append(f'{disclaimer}<br>')
        
        # Copyright
        company_name = subscription_config.get('company_name', 'Your Company Name')
        copyright_text = subscription_config.get('copyright_text', f'© 2024 {company_name}. All rights reserved.')
        # Replace {company} placeholder if present
        if copyright_text and '{company}' in copyright_text:
            copyright_text = copyright_text.replace('{company}', company_name)
        if copyright_text:
            html_parts.append(f'{copyright_text}<br>')
        
        # Address
        address = subscription_config.get('address', '123 Main Street, Suite 400, City, State 12345')
        if address:
            html_parts.append(f'{address}<br><br>')
        
        # Enlaces de Unsubscribe/View Online
        unsubscribe_link = subscription_config.get('unsubscribe_link', '#UNSUBSCRIBE_LINK')
        view_online_link = subscription_config.get('view_online_link', '#VIEW_ONLINE_LINK')
        
        html_parts.append(
            f'<a href="{unsubscribe_link}" target="_blank" style="color: {footer_color}; text-decoration: underline;">Unsubscribe</a>'
        )
        html_parts.append(
            f' &bull; <a href="{view_online_link}" target="_blank" style="color: {footer_color}; text-decoration: underline;">View Online</a>'
        )
        html_parts.append('</td>')
        html_parts.append('</tr>')
        
        return html_parts


def render_sidebar() -> Dict:
    """
    Render sidebar configuration inputs.
    
    Returns:
        Dictionary with configuration values including header and footer configs
    """
    with st.sidebar:
        st.header("📧 Newsletter Configuration")
        
        email_subject = st.text_input(
            "Email Subject",
            value=st.session_state.get("Email Subject", ""),
            key="Email Subject",
            help="The subject line for your newsletter email"
        )
        
        # Initialize default value if not in session_state to avoid conflicts
        if "Number of Layers" not in st.session_state:
            st.session_state["Number of Layers"] = 1
        
        num_layers = st.number_input(
            "Number of Layers",
            min_value=1,
            max_value=10,
            step=1,
            key="Number of Layers",
            help="Select the number of content sections (layers) in your newsletter"
        )
        
        # Initialize default value if not in session_state to avoid conflicts
        if "Maximum Newsletter Width (px)" not in st.session_state:
            st.session_state["Maximum Newsletter Width (px)"] = 1000
        
        max_width = st.number_input(
            "Maximum Newsletter Width (px)",
            min_value=300,
            max_value=1200,
            step=10,
            key="Maximum Newsletter Width (px)",
            help="Maximum width of the newsletter in pixels"
        )
        
        font_options = [
            "Oswald, sans-serif",
            "Arial, sans-serif",
            "Helvetica, sans-serif",
            "Georgia, serif",
            "Times New Roman, serif",
            "Verdana, sans-serif",
            "Courier New, monospace",
            "Trebuchet MS, sans-serif",
            "Comic Sans MS, cursive"
        ]
        
        # Get and normalize Font Family index from session_state
        font_family_value = st.session_state.get("Font Family", 0)
        
        # Ensure the value is a valid integer index
        if isinstance(font_family_value, str):
            # If it's a string, find the index
            try:
                font_family_value = font_options.index(font_family_value)
            except ValueError:
                font_family_value = 0
        else:
            # Convert to int and ensure it's within valid range
            try:
                font_family_value = int(font_family_value)
                if font_family_value < 0 or font_family_value >= len(font_options):
                    font_family_value = 0
            except (ValueError, TypeError):
                font_family_value = 0
        
        # Use a temporary key to avoid serialization issues, then update session_state
        font_family = st.selectbox(
            "Font Family",
            options=font_options,
            index=font_family_value,
            key="font_family_selectbox",
            help="Font family for the newsletter text"
        )
        
        # Update session_state with the selected index
        st.session_state["Font Family"] = font_options.index(font_family)
        
        st.subheader("Color Settings")
        background_color = st.color_picker(
            "Background Color",
            value=st.session_state.get("Background Color", "#FFFFFF"),
            key="Background Color",
            help="Choose the background color for your newsletter"
        )
        
        text_color = st.color_picker(
            "Text Color",
            value=st.session_state.get("Text Color", "#000000"),
            key="Text Color",
            help="Choose the primary text color for your newsletter"
        )
        
        include_subscription = st.checkbox(
            "Include Subscription Section",
            value=st.session_state.get("Include Subscription Section", False),
            key="Include Subscription Section",
            help="Include subscription/unsubscribe section in the newsletter"
        )
        
        return {
            'email_subject': email_subject,
            'num_layers': int(num_layers),
            'max_width': int(max_width),
            'font_family': font_family,
            'background_color': background_color,
            'text_color': text_color,
            'include_subscription': include_subscription
        }


def render_header_config(email_subject: str) -> Dict:
    """
    Render header configuration form in the main area.
    
    Args:
        email_subject: Default email subject for header title
        
    Returns:
        Dictionary with header configuration
    """
    st.header("📋 Header Configuration")
    
    # First row: Pre-Header Text (Optional) | Header Background Color
    col_row1_1, col_row1_2 = st.columns(2)
    with col_row1_1:
        pre_header_text = st.text_input(
            "Pre-Header Text (Optional)",
            value="",
            placeholder="e.g., Hidden text for email preview",
            key="pre_header_text",
            help="Hidden text shown in email preview (optional - only included if filled)"
        )
    with col_row1_2:
        header_bg_color = st.color_picker(
            "Header Background Color",
            value="#ffffff",
            key="header_bg_color",
            help="Background color for the header section"
        )
    
    # Second row: Image Source
    image_source_options = ["External URL", "Upload Image (Base64)"]
    raw_value = st.session_state.get("header_image_source", "External URL")
    # Handle both old format (int index) and new format (option string)
    # IMPORTANT: Set the value in session_state BEFORE creating the widget
    if isinstance(raw_value, int):
        # Old format: convert index to option string
        image_source_value = image_source_options[max(0, min(1, raw_value))]
        st.session_state["header_image_source"] = image_source_value
    elif raw_value not in image_source_options:
        # Invalid value, default to first option
        image_source_value = image_source_options[0]
        st.session_state["header_image_source"] = image_source_value
    else:
        # Value is already a valid option string, ensure it's set in session_state
        if "header_image_source" not in st.session_state or st.session_state["header_image_source"] != raw_value:
            st.session_state["header_image_source"] = raw_value
    # Use the session_state key directly - Streamlit will use the value from session_state
    image_source = st.radio(
        "Image Source",
        options=image_source_options,
        key="header_image_source",
        help="Choose how to provide the header image"
    )
    
    # Third row: Header Image URL | Image Width (px)
    col_row3_1, col_row3_2 = st.columns(2)
    header_image_base64 = None
    header_image_url = None
    
    with col_row3_1:
        # Always check for existing base64 image in session_state (from loaded template)
        existing_base64 = st.session_state.get("header_image_base64")
        
        if image_source == "External URL":
            header_image_url = st.text_input(
                "Header Image URL",
                value=st.session_state.get("header_image_url", ""),
                key="header_image_url",
                help="Enter the URL of the image from an external server"
            )
            # Display image preview if URL is provided
            if header_image_url and header_image_url.strip():
                try:
                    st.image(header_image_url, width='content')
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
            # If URL is empty but we have base64, use base64 instead
            if not header_image_url and existing_base64:
                header_image_base64 = existing_base64
                header_image_url = None
            else:
                header_image_base64 = None
        else:
            if existing_base64:
                st.info("ℹ️ Image loaded from saved template")
                # Display the loaded image
                try:
                    st.image(existing_base64, width='content')
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
                header_image_base64 = existing_base64
            else:
                header_image_base64 = None
            
            header_image_file = st.file_uploader(
                "Header Logo/Image",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG'],
                key="header_image",
                help="Upload a logo or image for the header (optional)"
            )
            # Process header image (new upload takes precedence)
            if header_image_file is not None:
                header_image_base64 = ImageProcessor.convert_to_base64(header_image_file)
                # Update session_state with new image
                st.session_state["header_image_base64"] = header_image_base64
            elif existing_base64:
                # Use existing base64 from session_state
                header_image_base64 = existing_base64
    
    with col_row3_2:
        image_width = st.number_input(
            "Image Width (px)",
            min_value=50,
            max_value=1200,
            value=1000,
            step=10,
            key="header_image_width",
            help="Width of the header image in pixels"
        )
    
    # Header Title with styling
    col_title_1, col_title_2, col_title_3, col_title_4 = st.columns([3, 1, 1, 1])
    with col_title_1:
        header_title = st.text_input(
            "Header Title",
            value="",
            placeholder="e.g., Dear Sir/Madam...",
            key="header_title",
            help="The title displayed in the newsletter header"
        )
    with col_title_2:
        title_color = st.color_picker(
            "Color",
            value="#000000",
            key="header_title_color",
            help="Color for the header title"
        )
    with col_title_3:
        title_font_size = st.number_input(
            "Size (px)",
            min_value=10,
            max_value=72,
            value=28,
            step=1,
            key="header_title_font_size",
            help="Font size for the header title"
        )
    with col_title_4:
        title_bold = st.checkbox(
            "Bold",
            value=True,
            key="header_title_bold",
            help="Make header title bold"
        )
    
    # Header Text with styling
    st.markdown("**Header Text**")
    # Ensure the value is in session_state before creating the widget
    # IMPORTANT: Initialize or ensure value exists BEFORE widget creation
    if "header_text" not in st.session_state:
        st.session_state["header_text"] = ""
    # Check if template was loaded (indicated by temp key)
    if "_header_text_temp" in st.session_state:
        # Template was loaded, update the value and use a unique key to force reinitialization
        header_text_value = st.session_state["_header_text_temp"]
        st.session_state["header_text"] = header_text_value
        # Use a timestamp-based key to force widget reinitialization
        if "header_text_load_timestamp" not in st.session_state:
            st.session_state["header_text_load_timestamp"] = 0
        st.session_state["header_text_load_timestamp"] = st.session_state.get("header_text_load_timestamp", 0) + 1
        del st.session_state["_header_text_temp"]
        # Use unique key only when template was loaded
        widget_key = f"header_text_loaded_{st.session_state['header_text_load_timestamp']}"
    else:
        # Normal usage, use standard key
        widget_key = "header_text"
    # st_quill will use the value from session_state via key=
    header_text = st_quill(
        value=st.session_state.get("header_text", ""),
        placeholder="e.g., Enter header text here...",
        html=True,  # Return HTML content
        key=widget_key,
        toolbar=[
            [{'size': ['small', False, 'large', 'huge']}],
            ['bold', 'italic', 'underline', 'strike'],
            [{'align': []}],
            [{'list': 'ordered'}, {'list': 'bullet'}],
            [{'color': []}, {'background': []}],
            ['link'],
            ['clean']
        ]
    )
    
    # Header Text styling (below editor, like in layers)
    col_text_1, col_text_2 = st.columns(2)
    with col_text_1:
        text_font_size = st.number_input(
            "Header Text Font Size (px)",
            min_value=10,
            max_value=48,
            value=16,
            step=1,
            key="header_text_font_size",
            help="Font size for the header text"
        )
    with col_text_2:
        text_color = st.color_picker(
            "Header Text Color",
            value="#000000",
            key="header_text_color",
            help="Color for the header text"
        )
    return {
        'header_title': header_title,
        'header_text': header_text,
        'header_image_base64': header_image_base64,
        'header_image_url': header_image_url,
        'pre_header_text': pre_header_text,
        'header_bg_color': header_bg_color,
        'image_width': image_width,
        'title_font_size': title_font_size,
        'title_color': title_color,
        'title_bold': title_bold,
        'text_font_size': text_font_size,
        'text_color': text_color
    }


def render_footer_config() -> Dict:
    """
    Render footer configuration form in the main area.
    Similar to header but for footer section.
    
    Returns:
        Dictionary with footer configuration
    """
    st.header("📄 Footer Configuration")
    
    # First row: Footer alignment | Footer Background Color
    col_row1_1, col_row1_2 = st.columns(2)
    with col_row1_1:
        footer_alignment_options = ['Left', 'Center', 'Right']
        footer_alignment_index = st.session_state.get("footer_alignment", 0)
        # Ensure index is an integer
        try:
            footer_alignment_index = int(footer_alignment_index) if footer_alignment_index is not None else 0
        except (ValueError, TypeError):
            footer_alignment_index = 0
        # Ensure index is within valid range
        footer_alignment_index = max(0, min(2, footer_alignment_index))
        # Use temporary key to avoid serialization issues
        footer_alignment = st.selectbox(
            "Footer Alignment",
            options=footer_alignment_options,
            index=footer_alignment_index,
            key="footer_alignment_selectbox",
            help="Alignment of the entire footer content (image and text)"
        )
        # Update session_state with the selected index
        st.session_state["footer_alignment"] = footer_alignment_options.index(footer_alignment)
    with col_row1_2:
        footer_bg_color = st.color_picker(
            "Footer Background Color",
            value="#ffffff",
            key="footer_bg_color",
            help="Background color for the footer section"
        )
    
    # Footer Image External Link URL (optional)
    footer_image_link_url = st.text_input(
        "Footer Image External Link URL (Optional)",
        value=st.session_state.get("footer_image_link_url", ""),
        key="footer_image_link_url",
        help="If provided, the footer image will be clickable and link to this URL"
    )
    
    # Second row: Image Source (full width)
    image_source_options = ["External URL", "Upload Image (Base64)"]
    raw_value = st.session_state.get("footer_image_source", "External URL")
    # Handle both old format (int index) and new format (option string)
    # IMPORTANT: Set the value in session_state BEFORE creating the widget
    footer_key = "footer_image_source"
    if isinstance(raw_value, int):
        # Old format: convert index to option string
        image_source_value = image_source_options[max(0, min(1, raw_value))]
        st.session_state[footer_key] = image_source_value
    elif raw_value not in image_source_options:
        # Invalid value, default to first option
        image_source_value = image_source_options[0]
        st.session_state[footer_key] = image_source_value
    else:
        # Value is already a valid option string, ensure it's set in session_state
        if footer_key not in st.session_state or st.session_state[footer_key] != raw_value:
            st.session_state[footer_key] = raw_value
    # Use the session_state key directly - Streamlit will use the value from session_state
    image_source = st.radio(
        "Image Source",
        options=image_source_options,
        key=footer_key,
        help="Choose how to provide the footer image"
    )
    
    # Second row: Footer Image URL | Image Width (px)
    col_row2_1, col_row2_2 = st.columns(2)
    footer_image_base64 = None
    footer_image_url = None
    
    with col_row2_1:
        # Always check for existing base64 image in session_state (from loaded template)
        existing_base64 = st.session_state.get("footer_image_base64")
        
        if image_source == "External URL":
            footer_image_url = st.text_input(
                "Footer Image URL",
                value=st.session_state.get("footer_image_url", ""),
                key="footer_image_url",
                help="Enter the URL of the image from an external server"
            )
            # Display image preview if URL is provided
            if footer_image_url and footer_image_url.strip():
                try:
                    st.image(footer_image_url, width='content')
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
            # If URL is empty but we have base64, use base64 instead
            if not footer_image_url and existing_base64:
                footer_image_base64 = existing_base64
                footer_image_url = None
            else:
                footer_image_base64 = None
        else:
            if existing_base64:
                st.info("ℹ️ Image loaded from saved template")
                # Display the loaded image
                try:
                    st.image(existing_base64, width='content')
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
                footer_image_base64 = existing_base64
            else:
                footer_image_base64 = None
            
            footer_image_file = st.file_uploader(
                "Footer Logo/Image",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG'],
                key="footer_image",
                help="Upload a logo or image for the footer (optional)"
            )
            # Process footer image (new upload takes precedence)
            if footer_image_file is not None:
                footer_image_base64 = ImageProcessor.convert_to_base64(footer_image_file)
                # Update session_state with new image
                st.session_state["footer_image_base64"] = footer_image_base64
            elif existing_base64:
                # Use existing base64 from session_state
                footer_image_base64 = existing_base64
    
    with col_row2_2:
        image_width = st.number_input(
            "Image Width (px)",
            min_value=50,
            max_value=1200,
            value=600,
            step=10,
            key="footer_image_width",
            help="Width of the footer image in pixels"
        )
    
    # Position of the footer image relative to text
    footer_image_position_options = ["Above Text", "After Text"]
    raw_footer_image_position = st.session_state.get("footer_image_position", "Above Text")
    if isinstance(raw_footer_image_position, int):
        normalized_footer_image_position = footer_image_position_options[max(0, min(1, raw_footer_image_position))]
    else:
        footer_pos_map = {
            "above text": "Above Text",
            "after text": "After Text"
        }
        normalized_footer_image_position = footer_pos_map.get(str(raw_footer_image_position).strip().lower(), "Above Text")
    # Ensure session_state is set before widget creation
    st.session_state["footer_image_position"] = normalized_footer_image_position
    footer_image_position = st.radio(
        "Footer Image Position",
        options=footer_image_position_options,
        index=footer_image_position_options.index(normalized_footer_image_position),
        key="footer_image_position",
        help="Choose if the footer image goes above the text or after the text (always before Social Media links)"
    )
    
    # Third row: Company Name with styling
    col_cn_1, col_cn_2, col_cn_3, col_cn_4 = st.columns([3, 1, 1, 1])
    with col_cn_1:
        company_name = st.text_input(
            "Company Name",
            value=st.session_state.get("footer_company_name", ""),
            placeholder="e.g., Your Company Name",
            key="footer_company_name",
            help="Company or organization name"
        )
    with col_cn_2:
        company_name_color = st.color_picker(
            "Color",
            value="#000000",
            key="footer_company_name_color",
            help="Color for company name"
        )
    with col_cn_3:
        company_name_size = st.number_input(
            "Size (px)",
            min_value=8,
            max_value=48,
            value=12,
            step=1,
            key="footer_company_name_size",
            help="Font size for company name"
        )
    with col_cn_4:
        company_name_bold = st.checkbox(
            "Bold",
            value=False,
            key="footer_company_name_bold",
            help="Make company name bold"
        )
    
    # Fourth row: Address with styling
    col_addr_1, col_addr_2, col_addr_3, col_addr_4 = st.columns([3, 1, 1, 1])
    with col_addr_1:
        address = st.text_area(
            "Company Address",
            value=st.session_state.get("footer_address", ""),
            placeholder="e.g., 123 Main Street, Suite 400, City, State 12345",
            key="footer_address",
            help="Company address and registration information",
            height=80
        )
    with col_addr_2:
        address_color = st.color_picker(
            "Color",
            value="#000000",
            key="footer_address_color",
            help="Color for address"
        )
    with col_addr_3:
        address_size = st.number_input(
            "Size (px)",
            min_value=8,
            max_value=48,
            value=12,
            step=1,
            key="footer_address_size",
            help="Font size for address"
        )
    with col_addr_4:
        address_bold = st.checkbox(
            "Bold",
            value=False,
            key="footer_address_bold",
            help="Make address bold"
        )
    
    # Fifth row: Directors with styling
    col_dir_1, col_dir_2, col_dir_3, col_dir_4 = st.columns([3, 1, 1, 1])
    with col_dir_1:
        directors = st.text_area(
            "Responsibles",
            value=st.session_state.get("footer_directors", ""),
            placeholder="e.g., Managing Directors: John Smith, Jane Doe",
            key="footer_directors",
            help="Company directors or responsible persons",
            height=60
        )
    with col_dir_2:
        directors_color = st.color_picker(
            "Color",
            value="#000000",
            key="footer_directors_color",
            help="Color for directors"
        )
    with col_dir_3:
        directors_size = st.number_input(
            "Size (px)",
            min_value=8,
            max_value=48,
            value=12,
            step=1,
            key="footer_directors_size",
            help="Font size for directors"
        )
    with col_dir_4:
        directors_bold = st.checkbox(
            "Bold",
            value=False,
            key="footer_directors_bold",
            help="Make directors bold"
        )
    
    # Sixth row: Social Media Links section
    st.markdown("**Social Media Links**")
    col_label_1, col_label_2, col_label_3, col_label_4 = st.columns([3, 1, 1, 1])
    with col_label_1:
        social_media_label = st.text_input(
            "Social Media Section Label",
            value="",
            placeholder="e.g., Our Social Media Channels",
            key="footer_social_label",
            help="Label text displayed above social media links"
        )
    with col_label_2:
        social_label_color = st.color_picker(
            "Color",
            value="#000000",
            key="footer_social_label_color",
            help="Color for social media label"
        )
    with col_label_3:
        social_label_size = st.number_input(
            "Size (px)",
            min_value=8,
            max_value=48,
            value=14,
            step=1,
            key="footer_social_label_size",
            help="Font size for social media label"
        )
    with col_label_4:
        social_label_bold = st.checkbox(
            "Bold",
            value=True,
            key="footer_social_label_bold",
            help="Make social media label bold"
        )
    social_media_type_options = ["URLs Only", "Images"]
    raw_value = st.session_state.get("footer_social_type", "URLs Only")
    
    # Check if there are any social media images loaded - if so, default to "Images"
    has_social_images = any([
        st.session_state.get("footer_facebook_image_base64"),
        st.session_state.get("footer_linkedin_image_base64"),
        st.session_state.get("footer_xing_image_base64"),
        st.session_state.get("footer_instagram_image_base64")
    ])
    
    # Handle both old format (int index) and new format (option string)
    # IMPORTANT: Set the value in session_state BEFORE creating the widget
    if isinstance(raw_value, int):
        # Old format: convert index to option string
        social_media_type_value = social_media_type_options[max(0, min(1, raw_value))]
        st.session_state["footer_social_type"] = social_media_type_value
    elif raw_value not in social_media_type_options:
        # Invalid value or if we have images, default to "Images", otherwise "URLs Only"
        social_media_type_value = "Images" if has_social_images else "URLs Only"
        st.session_state["footer_social_type"] = social_media_type_value
    else:
        # Value is already a valid option string, but if we have images and it's "URLs Only", change to "Images"
        if has_social_images and raw_value == "URLs Only":
            st.session_state["footer_social_type"] = "Images"
        elif "footer_social_type" not in st.session_state or st.session_state["footer_social_type"] != raw_value:
            st.session_state["footer_social_type"] = raw_value
    
    # Use the session_state key directly - Streamlit will use the value from session_state
    social_media_type = st.radio(
        "Social Media Type",
        options=social_media_type_options,
        key="footer_social_type",
        help="Choose between text links or image icons"
    )
    
    if social_media_type == "Images":
        social_image_width = st.number_input(
            "Social Media Icon Width (px)",
            min_value=20,
            max_value=100,
            value=30,
            step=5,
            key="footer_social_image_width",
            help="Width of social media icons"
        )
    else:
        social_image_width = None
    
    # First row: Facebook (left) | LinkedIn (right)
    col_social_row1_1, col_social_row1_2 = st.columns(2)
    with col_social_row1_1:
        facebook_url = st.text_input(
            "Facebook URL",
            placeholder="e.g., https://facebook.com",
            key="footer_facebook",
            help="Facebook page URL"
        )
        if social_media_type == "Images":
            # Check if there's a base64 image in session_state (from loaded template)
            existing_facebook_base64 = st.session_state.get("footer_facebook_image_base64")
            if existing_facebook_base64:
                st.info("ℹ️ Facebook image loaded from template")
                try:
                    st.image(existing_facebook_base64, width=50)
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
            
            facebook_image = st.file_uploader(
                "Facebook Icon",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG', 'svg', 'SVG'],
                key="footer_facebook_image",
                help="Upload Facebook icon image"
            )
        else:
            facebook_image = None
    
    with col_social_row1_2:
        linkedin_url = st.text_input(
            "LinkedIn URL",
            placeholder="e.g., https://linkedin.com",
            key="footer_linkedin",
            help="LinkedIn page URL"
        )
        if social_media_type == "Images":
            # Check if there's a base64 image in session_state (from loaded template)
            existing_linkedin_base64 = st.session_state.get("footer_linkedin_image_base64")
            if existing_linkedin_base64:
                st.info("ℹ️ LinkedIn image loaded from template")
                try:
                    st.image(existing_linkedin_base64, width=50)
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
            
            linkedin_image = st.file_uploader(
                "LinkedIn Icon",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG', 'svg', 'SVG'],
                key="footer_linkedin_image",
                help="Upload LinkedIn icon image"
            )
        else:
            linkedin_image = None
    
    # Second row: Xing (left) | Instagram (right)
    col_social_row2_1, col_social_row2_2 = st.columns(2)
    with col_social_row2_1:
        xing_url = st.text_input(
            "Xing URL",
            placeholder="e.g., https://xing.com",
            key="footer_xing",
            help="Xing page URL"
        )
        if social_media_type == "Images":
            # Check if there's a base64 image in session_state (from loaded template)
            existing_xing_base64 = st.session_state.get("footer_xing_image_base64")
            if existing_xing_base64:
                st.info("ℹ️ Xing image loaded from template")
                try:
                    st.image(existing_xing_base64, width=50)
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
            
            xing_image = st.file_uploader(
                "Xing Icon",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG', 'svg', 'SVG'],
                key="footer_xing_image",
                help="Upload Xing icon image"
            )
        else:
            xing_image = None
    
    with col_social_row2_2:
        instagram_url = st.text_input(
            "Instagram URL",
            placeholder="e.g., https://instagram.com",
            key="footer_instagram",
            help="Instagram page URL"
        )
        if social_media_type == "Images":
            # Check if there's a base64 image in session_state (from loaded template)
            existing_instagram_base64 = st.session_state.get("footer_instagram_image_base64")
            if existing_instagram_base64:
                st.info("ℹ️ Instagram image loaded from template")
                try:
                    st.image(existing_instagram_base64, width=50)
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
            
            instagram_image = st.file_uploader(
                "Instagram Icon",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG', 'svg', 'SVG'],
                key="footer_instagram_image",
                help="Upload Instagram icon image"
            )
        else:
            instagram_image = None
    
    # Process social media images to Base64
    # New uploads take precedence, otherwise use images from session_state (loaded from template)
    facebook_image_base64 = None
    linkedin_image_base64 = None
    xing_image_base64 = None
    instagram_image_base64 = None
    
    if social_media_type == "Images":
        # Process new uploads (they take precedence)
        if facebook_image:
            facebook_image_base64 = ImageProcessor.convert_to_base64(facebook_image)
            # Update session_state with new image
            st.session_state["footer_facebook_image_base64"] = facebook_image_base64
        elif st.session_state.get("footer_facebook_image_base64"):
            # Use existing image from session_state (loaded from template)
            facebook_image_base64 = st.session_state.get("footer_facebook_image_base64")
        
        if linkedin_image:
            linkedin_image_base64 = ImageProcessor.convert_to_base64(linkedin_image)
            # Update session_state with new image
            st.session_state["footer_linkedin_image_base64"] = linkedin_image_base64
        elif st.session_state.get("footer_linkedin_image_base64"):
            # Use existing image from session_state (loaded from template)
            linkedin_image_base64 = st.session_state.get("footer_linkedin_image_base64")
        
        if xing_image:
            xing_image_base64 = ImageProcessor.convert_to_base64(xing_image)
            # Update session_state with new image
            st.session_state["footer_xing_image_base64"] = xing_image_base64
        elif st.session_state.get("footer_xing_image_base64"):
            # Use existing image from session_state (loaded from template)
            xing_image_base64 = st.session_state.get("footer_xing_image_base64")
        
        if instagram_image:
            instagram_image_base64 = ImageProcessor.convert_to_base64(instagram_image)
            # Update session_state with new image
            st.session_state["footer_instagram_image_base64"] = instagram_image_base64
        elif st.session_state.get("footer_instagram_image_base64"):
            # Use existing image from session_state (loaded from template)
            instagram_image_base64 = st.session_state.get("footer_instagram_image_base64")
    
    return {
        'footer_image_base64': footer_image_base64,
        'footer_image_url': footer_image_url,
        'footer_image_link_url': footer_image_link_url,
        'company_name': company_name,
        'address': address,
        'directors': directors,
        'footer_bg_color': footer_bg_color,
        'image_width': image_width,
        'footer_alignment': footer_alignment,
        'company_name_color': company_name_color,
        'company_name_size': company_name_size,
        'company_name_bold': company_name_bold,
        'address_color': address_color,
        'address_size': address_size,
        'address_bold': address_bold,
        'footer_image_position': footer_image_position,
        'directors_color': directors_color,
        'directors_size': directors_size,
        'directors_bold': directors_bold,
        'social_media_type': social_media_type,
        'social_media_label': social_media_label,
        'social_label_color': social_label_color,
        'social_label_size': social_label_size,
        'social_label_bold': social_label_bold,
        'social_image_width': social_image_width if social_media_type == "Images" else None,
        'facebook_url': facebook_url,
        'facebook_image_base64': facebook_image_base64,
        'linkedin_url': linkedin_url,
        'linkedin_image_base64': linkedin_image_base64,
        'xing_url': xing_url,
        'xing_image_base64': xing_image_base64,
        'instagram_url': instagram_url,
        'instagram_image_base64': instagram_image_base64
    }


def render_subscription_config() -> Dict:
    """
    Render subscription configuration form in the main area.
    
    Returns:
        Dictionary with subscription configuration
    """
    st.header("📄 Subscription Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        company_name = st.text_input(
            "Company Name",
            placeholder="e.g., Your Company Name",
            key="company_name",
            help="Your company or organization name"
        )
        
        address = st.text_area(
            "Company Address",
            placeholder="e.g., 123 Main Street, Suite 400, City, State 12345",
            key="address",
            help="Company physical address",
            height=100
        )
        
        copyright_text = st.text_input(
            "Copyright Text",
            placeholder="e.g., © 2024 Your Company Name. All rights reserved.",
            key="copyright_text",
            help="Copyright notice text (you can use {company} placeholder)"
        )
    
    with col2:
        disclaimer_text = st.text_area(
            "Disclaimer Text",
            placeholder="e.g., This email was sent to you because you subscribed to our newsletter.",
            key="disclaimer_text",
            help="Legal disclaimer text",
            height=100
        )
        
        unsubscribe_link = st.text_input(
            "Unsubscribe Link",
            placeholder="e.g., Unsubscribe Link",
            key="unsubscribe_link",
            help="URL for unsubscribe link"
        )
        
        view_online_link = st.text_input(
            "View Online Link",
            placeholder="e.g., View Online Link",
            key="view_online_link",
            help="URL for viewing newsletter online"
        )
        
        footer_color = st.color_picker(
            "Footer Text Color",
            value="#999999",
            key="footer_color",
            help="Text color for footer content"
        )
    
    return {
        'company_name': company_name,
        'address': address,
        'copyright_text': copyright_text,
        'disclaimer_text': disclaimer_text,
        'unsubscribe_link': unsubscribe_link,
        'view_online_link': view_online_link,
        'footer_color': footer_color
    }


def render_layer_form(layer_number: int) -> Dict:
    """
    Render form inputs for a single content layer.
    
    Args:
        layer_number: The layer index (1-based)
        
    Returns:
        Dictionary containing layer content data
    """
    st.subheader(f"Layer {layer_number}")
    
    # Layer Order Configuration
    col_order_1, col_order_2 = st.columns([1, 3])
    with col_order_1:
        layer_order = st.number_input(
            f"Order",
            min_value=1,
            max_value=10,
            value=st.session_state.get(f"layer_order_{layer_number}", layer_number),
            step=1,
            key=f"layer_order_{layer_number}",
            help="Display order of this layer (1 = first, 2 = second, etc.)"
        )
    
    # External Link Configuration (first row)
    link_url = st.text_input(
        f"External Link URL - Layer {layer_number}",
        value=st.session_state.get(f"link_url_{layer_number}", ""),
        key=f"link_url_{layer_number}",
        placeholder="e.g., https://example.com",
        help="Optional: URL to open when clicking anywhere on this layer (opens in new tab)"
    )
    
    # Title 1 with styling (second row)
    col_title1_1, col_title1_2, col_title1_3, col_title1_4 = st.columns([3, 1, 1, 1])
    with col_title1_1:
        title = st.text_input(
            f"Title 1 (H2) - Layer {layer_number}",
            key=f"title_{layer_number}",
            value="",
            placeholder="e.g., Enter main title..."
        )
    with col_title1_2:
        title_color = st.color_picker(
            "Color",
            value="#000000",
            key=f"title_color_{layer_number}",
            help="Color for the main title"
        )
    with col_title1_3:
        title_font_size = st.number_input(
            "Size (px)",
            min_value=10,
            max_value=72,
            value=21,
            step=1,
            key=f"title_font_size_{layer_number}",
            help="Font size for main title"
        )
    with col_title1_4:
        title_bold = st.checkbox(
            "Bold",
            value=st.session_state.get(f"title_bold_{layer_number}", True),
            key=f"title_bold_{layer_number}",
            help="Make main title bold"
        )
    
    # Title 2 with styling
    col_title2_1, col_title2_2, col_title2_3, col_title2_4 = st.columns([3, 1, 1, 1])
    with col_title2_1:
        subtitle = st.text_input(
            f"Title 2 (H3) - Layer {layer_number}",
            key=f"subtitle_{layer_number}",
            value="",
            placeholder="e.g., Enter subtitle (green)..."
        )
    with col_title2_2:
        subtitle_color = st.color_picker(
            "Color",
            value="#00925b",
            key=f"subtitle_color_{layer_number}",
            help="Color for the second title"
        )
    with col_title2_3:
        subtitle_font_size = st.number_input(
            "Size (px)",
            min_value=10,
            max_value=48,
            value=15,
            step=1,
            key=f"subtitle_font_size_{layer_number}",
            help="Font size for second title"
        )
    with col_title2_4:
        subtitle_bold = st.checkbox(
            "Bold",
            value=False,
            key=f"subtitle_bold_{layer_number}",
            help="Make subtitle bold"
        )
    
    # Title 3 with styling
    col_title3_1, col_title3_2, col_title3_3, col_title3_4 = st.columns([3, 1, 1, 1])
    with col_title3_1:
        subtitle2 = st.text_input(
            f"Title 3 (H4) - Layer {layer_number}",
            key=f"subtitle2_{layer_number}",
            value="",
            placeholder="e.g., Enter third title..."
        )
    with col_title3_2:
        subtitle2_color = st.color_picker(
            "Color",
            value="#000000",
            key=f"subtitle2_color_{layer_number}",
            help="Color for the third title"
        )
    with col_title3_3:
        subtitle2_font_size = st.number_input(
            "Size (px)",
            min_value=10,
            max_value=48,
            value=13,
            step=1,
            key=f"subtitle2_font_size_{layer_number}",
            help="Font size for third title"
        )
    with col_title3_4:
        subtitle2_bold = st.checkbox(
            "Bold",
            value=False,
            key=f"subtitle2_bold_{layer_number}",
            help="Make third title bold"
        )
    
    st.markdown(f"**Main Content - Layer {layer_number}**")
    # Ensure the value is in session_state before creating the widget
    content_key = f"content_{layer_number}"
    # IMPORTANT: Initialize or ensure value exists BEFORE widget creation
    if content_key not in st.session_state:
        st.session_state[content_key] = ""
    # Check if template was loaded (indicated by temp key)
    temp_key = f"_{content_key}_temp"
    if temp_key in st.session_state:
        # Template was loaded, update the value and use a unique key to force reinitialization
        content_value = st.session_state[temp_key]
        st.session_state[content_key] = content_value
        # Use a timestamp-based key to force widget reinitialization
        load_timestamp_key = f"{content_key}_load_timestamp"
        if load_timestamp_key not in st.session_state:
            st.session_state[load_timestamp_key] = 0
        st.session_state[load_timestamp_key] = st.session_state.get(load_timestamp_key, 0) + 1
        del st.session_state[temp_key]
        # Use unique key only when template was loaded
        widget_key = f"{content_key}_loaded_{st.session_state[load_timestamp_key]}"
    else:
        # Normal usage, use standard key
        widget_key = content_key
    # st_quill will use the value from session_state via key=
    content = st_quill(
        value=st.session_state.get(content_key, ""),
        placeholder="e.g., Enter main content here...",
        html=True,  # Return HTML content
        key=widget_key,
        toolbar=[
            [{'header': [1, 2, 3, False]}],
            ['bold', 'italic', 'underline', 'strike'],
            [{'list': 'ordered'}, {'list': 'bullet'}],
            [{'color': []}, {'background': []}],
            ['link'],
            ['clean']
        ]
    )
    
    # Main Content styling
    col_content1, col_content2 = st.columns(2)
    with col_content1:
        content_font_size = st.number_input(
            f"Content Font Size (px) - Layer {layer_number}",
            min_value=8,
            max_value=48,
            value=13,
            step=1,
            key=f"content_font_size_{layer_number}",
            help="Font size for main content"
        )
    with col_content2:
        content_color = st.color_picker(
            f"Content Color - Layer {layer_number}",
            value="#000000",
            key=f"content_color_{layer_number}",
            help="Color for main content"
        )
    
    st.markdown("**Image Configuration**")
    
    # Image source selection
    image_source_options = ["External URL", "Upload Image (Base64)"]
    raw_value = st.session_state.get(f"image_source_{layer_number}", "External URL")
    # Handle both old format (int index) and new format (option string)
    # IMPORTANT: Set the value in session_state BEFORE creating the widget
    layer_key = f"image_source_{layer_number}"
    if isinstance(raw_value, int):
        # Old format: convert index to option string
        image_source_value = image_source_options[max(0, min(1, raw_value))]
        st.session_state[layer_key] = image_source_value
    elif raw_value not in image_source_options:
        # Invalid value, default to first option
        image_source_value = image_source_options[0]
        st.session_state[layer_key] = image_source_value
    else:
        # Value is already a valid option string, ensure it's set in session_state
        if layer_key not in st.session_state or st.session_state[layer_key] != raw_value:
            st.session_state[layer_key] = raw_value
    # Use the session_state key directly - Streamlit will use the value from session_state
    image_source = st.radio(
        f"Image Source - Layer {layer_number}",
        options=image_source_options,
        key=layer_key,
        help="Choose how to provide the image"
    )
    
    col_img1, col_img2 = st.columns(2)
    
    image_base64 = None
    image_url = None
    
    with col_img1:
        # Always check for existing base64 image in session_state (from loaded template)
        existing_base64 = st.session_state.get(f"image_base64_{layer_number}")
        
        if image_source == "External URL":
            image_url = st.text_input(
                f"Image URL - Layer {layer_number}",
                value=st.session_state.get(f"image_url_{layer_number}", ""),
                key=f"image_url_{layer_number}",
                help="Enter the URL of the image from an external server"
            )
            # Display image preview if URL is provided
            if image_url and image_url.strip():
                try:
                    st.image(image_url, width='content')
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
            # If URL is empty but we have base64, use base64 instead
            if not image_url and existing_base64:
                image_base64 = existing_base64
                image_url = None
            else:
                image_base64 = None
        else:
            if existing_base64:
                st.info(f"ℹ️ Image loaded from saved template (Layer {layer_number})")
                # Display the loaded image at 40% width
                try:
                    col_img_left, col_img_right = st.columns([2, 3])
                    with col_img_left:
                        st.image(existing_base64, width='stretch')
                except Exception as e:
                    st.warning(f"Could not display the image: {str(e)}")
                image_base64 = existing_base64
            else:
                image_base64 = None
            
            image_file = st.file_uploader(
                f"Upload Image - Layer {layer_number}",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG'],
                key=f"image_{layer_number}",
                help="Upload an image for this layer (JPG or PNG)"
            )
            # Process image to Base64 (new upload takes precedence)
            if image_file is not None:
                image_base64 = ImageProcessor.convert_to_base64(image_file)
                if image_base64 is None:
                    st.warning(f"⚠️ Error processing image for Layer {layer_number}. Please try uploading again.")
                else:
                    # Update session_state with new image
                    st.session_state[f"image_base64_{layer_number}"] = image_base64
            elif existing_base64:
                # Use existing base64 from session_state
                image_base64 = existing_base64
        
        alignment_options = ['Left', 'Right']
        alignment_index = st.session_state.get(f"alignment_{layer_number}", 0)
        # Ensure index is an integer
        try:
            alignment_index = int(alignment_index) if alignment_index is not None else 0
        except (ValueError, TypeError):
            alignment_index = 0
        # Ensure index is within valid range
        alignment_index = max(0, min(1, alignment_index))
        # Use temporary key to avoid serialization issues
        image_alignment = st.selectbox(
            f"Image Position - Layer {layer_number}",
            options=alignment_options,
            index=alignment_index,
            key=f"alignment_selectbox_{layer_number}",
            help="Position of image relative to text"
        )
        # Update session_state with the selected index
        st.session_state[f"alignment_{layer_number}"] = alignment_options.index(image_alignment)
    
    with col_img2:
        image_width = st.number_input(
            f"Image Width (px) - Layer {layer_number}",
            min_value=50,
            max_value=800,
            value=210,
            step=10,
            key=f"image_width_{layer_number}",
            help="Width of the image in pixels"
        )
        
        padding = st.number_input(
            f"Padding (px) - Layer {layer_number}",
            min_value=0,
            max_value=100,
            value=30,
            step=5,
            key=f"padding_{layer_number}",
            help="Vertical padding for this layer"
        )
    
    return {
        'order': layer_order,
        'title': title,
        'subtitle': subtitle,
        'subtitle2': subtitle2,
        'content': content,
        'image_url': image_url,
        'image_base64': image_base64,
        'image_alignment': image_alignment,
        'image_width': image_width,
        'padding': padding,
        'link_url': link_url,
        'title_color': title_color,
        'subtitle_color': subtitle_color,
        'subtitle2_color': subtitle2_color,
        'title_font_size': title_font_size,
        'subtitle_font_size': subtitle_font_size,
        'subtitle2_font_size': subtitle2_font_size,
        'title_bold': title_bold,
        'subtitle_bold': subtitle_bold,
        'subtitle2_bold': subtitle2_bold,
        'content_font_size': content_font_size,
        'content_color': content_color
    }


def apply_template_to_session_state(template_data: dict):
    """
    Apply loaded template data to Streamlit session_state.
    
    Args:
        template_data: Dictionary containing template configuration
    """
    # Store the template name for later use
    if 'name' in template_data:
        st.session_state['loaded_template_name'] = template_data['name']
    
    config = template_data.get('config', {})
    header_config = template_data.get('header_config', {})
    layers = template_data.get('layers', [])
    footer_config = template_data.get('footer_config', {})
    subscription_config = template_data.get('subscription_config', {})
    
    # Apply basic config to session_state
    # Convert all values to native Python types to avoid serialization issues
    if 'email_subject' in config:
        st.session_state['Email Subject'] = str(config['email_subject']) if config['email_subject'] is not None else ""
    if 'num_layers' in config:
        # Convert to native Python int to avoid type issues with MongoDB int64
        st.session_state['Number of Layers'] = int(config['num_layers'])
    if 'max_width' in config:
        # Convert to native Python int
        st.session_state['Maximum Newsletter Width (px)'] = int(config['max_width'])
    if 'font_family' in config:
        font_options = [
            "Oswald, sans-serif",
            "Arial, sans-serif",
            "Helvetica, sans-serif",
            "Georgia, serif",
            "Times New Roman, serif",
            "Verdana, sans-serif",
            "Courier New, monospace",
            "Trebuchet MS, sans-serif",
            "Comic Sans MS, cursive"
        ]
        font_family_str = str(config['font_family']) if config['font_family'] is not None else ""
        if font_family_str in font_options:
            # Ensure index is a native Python int
            st.session_state['Font Family'] = int(font_options.index(font_family_str))
        else:
            st.session_state['Font Family'] = 0  # Default to first option
    if 'background_color' in config:
        st.session_state['Background Color'] = str(config['background_color']) if config['background_color'] is not None else "#FFFFFF"
    if 'text_color' in config:
        st.session_state['Text Color'] = str(config['text_color']) if config['text_color'] is not None else "#000000"
    if 'include_subscription' in config:
        # Convert to native Python bool
        st.session_state['Include Subscription Section'] = bool(config['include_subscription'])
    
    # Apply header config
    if 'pre_header_text' in header_config:
        st.session_state['pre_header_text'] = header_config['pre_header_text']
    if 'header_bg_color' in header_config:
        st.session_state['header_bg_color'] = header_config['header_bg_color']
    # Set image source based on what's available
    # Check both URL and base64, URL takes precedence if both exist and are non-empty
    header_image_url_value = header_config.get('header_image_url')
    header_image_base64_value = header_config.get('header_image_base64')
    
    # Check if URL exists and is not empty/null
    if header_image_url_value and str(header_image_url_value).strip():
        st.session_state['header_image_url'] = str(header_image_url_value).strip()
        st.session_state['header_image_source'] = "External URL"  # Store option string, not index
    # Check if base64 exists and is not empty/null
    elif header_image_base64_value and str(header_image_base64_value).strip():
        st.session_state['header_image_base64'] = str(header_image_base64_value).strip()
        st.session_state['header_image_source'] = "Upload Image (Base64)"  # Store option string, not index
    # If neither exists, don't set image_source (will default to 0)
    if 'image_width' in header_config:
        st.session_state['header_image_width'] = int(header_config['image_width'])
    if 'header_title' in header_config:
        st.session_state['header_title'] = str(header_config['header_title']) if header_config['header_title'] is not None else ""
    if 'header_text' in header_config:
        # Force widget reinitialization by using a unique key suffix
        # This ensures the widget gets the new value after template load
        header_text_value = str(header_config['header_text']) if header_config['header_text'] is not None else ""
        # Store in a temporary key first, then copy to the actual key
        st.session_state['_header_text_temp'] = header_text_value
        # Clear the widget state by deleting the key
        if 'header_text' in st.session_state:
            del st.session_state['header_text']
        # Now set the new value
        st.session_state['header_text'] = header_text_value
    if 'header_title_color' in header_config:
        st.session_state['header_title_color'] = str(header_config['title_color']) if header_config.get('title_color') is not None else "#000000"
    if 'header_title_font_size' in header_config:
        st.session_state['header_title_font_size'] = int(header_config['title_font_size'])
    if 'header_title_bold' in header_config:
        st.session_state['header_title_bold'] = bool(header_config['title_bold'])
    if 'header_text_color' in header_config:
        st.session_state['header_text_color'] = str(header_config['text_color']) if header_config.get('text_color') is not None else "#000000"
    if 'header_text_font_size' in header_config:
        st.session_state['header_text_font_size'] = int(header_config['text_font_size'])
    
    # Apply layers
    for i, layer in enumerate(layers, start=1):
        if 'order' in layer:
            st.session_state[f'layer_order_{i}'] = int(layer['order']) if layer['order'] is not None else i
        if 'title' in layer:
            st.session_state[f'title_{i}'] = layer['title']
        if 'subtitle' in layer:
            st.session_state[f'subtitle_{i}'] = layer['subtitle']
        if 'subtitle2' in layer:
            st.session_state[f'subtitle2_{i}'] = layer['subtitle2']
        if 'content' in layer:
            # Force widget reinitialization by using a unique key suffix
            # This ensures the widget gets the new value after template load
            content_key = f'content_{i}'
            content_value = str(layer['content']) if layer['content'] is not None else ""
            # Store in a temporary key first, then copy to the actual key
            st.session_state[f'_{content_key}_temp'] = content_value
            # Clear the widget state by deleting the key
            if content_key in st.session_state:
                del st.session_state[content_key]
            # Now set the new value
            st.session_state[content_key] = content_value
        # Set image source based on what's available
        # Check both URL and base64, URL takes precedence if both exist and are non-empty
        layer_image_url_value = layer.get('image_url')
        layer_image_base64_value = layer.get('image_base64')
        
        # Check if URL exists and is not empty/null
        if layer_image_url_value and str(layer_image_url_value).strip():
            st.session_state[f'image_url_{i}'] = str(layer_image_url_value).strip()
            st.session_state[f'image_source_{i}'] = "External URL"  # Store option string, not index
        # Check if base64 exists and is not empty/null
        elif layer_image_base64_value and str(layer_image_base64_value).strip():
            st.session_state[f'image_base64_{i}'] = str(layer_image_base64_value).strip()
            st.session_state[f'image_source_{i}'] = "Upload Image (Base64)"  # Store option string, not index
        # If neither exists, don't set image_source (will default to 0)
        if 'image_alignment' in layer:
            alignment_index = 0 if str(layer['image_alignment']).lower() == 'left' else 1
            st.session_state[f'alignment_{i}'] = int(alignment_index)
        if 'image_width' in layer:
            st.session_state[f'image_width_{i}'] = int(layer['image_width'])
        if 'padding' in layer:
            st.session_state[f'padding_{i}'] = int(layer['padding'])
        if 'link_url' in layer:
            st.session_state[f'link_url_{i}'] = layer['link_url']
        if 'title_color' in layer:
            st.session_state[f'title_color_{i}'] = layer['title_color']
        if 'subtitle_color' in layer:
            st.session_state[f'subtitle_color_{i}'] = layer['subtitle_color']
        if 'subtitle2_color' in layer:
            st.session_state[f'subtitle2_color_{i}'] = layer['subtitle2_color']
        if 'title_font_size' in layer:
            st.session_state[f'title_font_size_{i}'] = int(layer['title_font_size'])
        if 'title_bold' in layer:
            st.session_state[f'title_bold_{i}'] = bool(layer['title_bold'])
        if 'subtitle_font_size' in layer:
            st.session_state[f'subtitle_font_size_{i}'] = int(layer['subtitle_font_size'])
        if 'subtitle2_font_size' in layer:
            st.session_state[f'subtitle2_font_size_{i}'] = int(layer['subtitle2_font_size'])
        if 'subtitle_bold' in layer:
            st.session_state[f'subtitle_bold_{i}'] = bool(layer['subtitle_bold'])
        if 'subtitle2_bold' in layer:
            st.session_state[f'subtitle2_bold_{i}'] = bool(layer['subtitle2_bold'])
        if 'content_font_size' in layer:
            st.session_state[f'content_font_size_{i}'] = int(layer['content_font_size'])
        if 'content_color' in layer:
            st.session_state[f'content_color_{i}'] = layer['content_color']
    
    # Apply footer config
    if 'footer_bg_color' in footer_config:
        st.session_state['footer_bg_color'] = footer_config['footer_bg_color']
    # Set footer image source based on what's available
    # Check both URL and base64, URL takes precedence if both exist and are non-empty
    footer_image_url_value = footer_config.get('footer_image_url')
    footer_image_base64_value = footer_config.get('footer_image_base64')
    if 'footer_image_position' in footer_config:
        footer_pos_map = {
            "above text": "Above Text",
            "after text": "After Text"
        }
        raw_footer_pos = footer_config['footer_image_position']
        normalized_footer_pos = footer_pos_map.get(str(raw_footer_pos).strip().lower(), "Above Text") if raw_footer_pos is not None else "Above Text"
        st.session_state['footer_image_position'] = normalized_footer_pos
    
    # Check if URL exists and is not empty/null
    if footer_image_url_value and str(footer_image_url_value).strip():
        st.session_state['footer_image_url'] = str(footer_image_url_value).strip()
        st.session_state['footer_image_source'] = "External URL"  # Store option string, not index
    # Check if base64 exists and is not empty/null
    elif footer_image_base64_value and str(footer_image_base64_value).strip():
        st.session_state['footer_image_base64'] = str(footer_image_base64_value).strip()
        st.session_state['footer_image_source'] = "Upload Image (Base64)"  # Store option string, not index
    # If neither exists, don't set image_source (will default to 0)
    if 'image_width' in footer_config:
        st.session_state['footer_image_width'] = int(footer_config['image_width'])
    if 'footer_image_link_url' in footer_config:
        st.session_state['footer_image_link_url'] = str(footer_config['footer_image_link_url']) if footer_config['footer_image_link_url'] is not None else ""
    if 'footer_alignment' in footer_config:
        alignment_map = {'Left': 0, 'Center': 1, 'Right': 2}
        st.session_state['footer_alignment'] = int(alignment_map.get(str(footer_config['footer_alignment']), 0))
    if 'company_name' in footer_config:
        st.session_state['footer_company_name'] = str(footer_config['company_name']) if footer_config['company_name'] is not None else ""
    if 'address' in footer_config:
        st.session_state['footer_address'] = str(footer_config['address']) if footer_config['address'] is not None else ""
    if 'directors' in footer_config:
        st.session_state['footer_directors'] = str(footer_config['directors']) if footer_config['directors'] is not None else ""
    # Footer styling
    if 'company_name_color' in footer_config:
        st.session_state['footer_company_name_color'] = footer_config['company_name_color']
    if 'company_name_size' in footer_config:
        st.session_state['footer_company_name_size'] = int(footer_config['company_name_size'])
    if 'company_name_bold' in footer_config:
        st.session_state['footer_company_name_bold'] = bool(footer_config['company_name_bold'])
    if 'address_color' in footer_config:
        st.session_state['footer_address_color'] = str(footer_config['address_color']) if footer_config['address_color'] is not None else "#000000"
    if 'address_size' in footer_config:
        st.session_state['footer_address_size'] = int(footer_config['address_size'])
    if 'address_bold' in footer_config:
        st.session_state['footer_address_bold'] = bool(footer_config['address_bold'])
    if 'directors_color' in footer_config:
        st.session_state['footer_directors_color'] = str(footer_config['directors_color']) if footer_config['directors_color'] is not None else "#000000"
    if 'directors_size' in footer_config:
        st.session_state['footer_directors_size'] = int(footer_config['directors_size'])
    if 'directors_bold' in footer_config:
        st.session_state['footer_directors_bold'] = bool(footer_config['directors_bold'])
    # Social media
    # Check if there are any social media images - if so, set type to "Images"
    has_social_images = any([
        footer_config.get('facebook_image_base64'),
        footer_config.get('linkedin_image_base64'),
        footer_config.get('xing_image_base64'),
        footer_config.get('instagram_image_base64')
    ])
    
    if 'social_media_type' in footer_config:
        social_media_type_str = str(footer_config['social_media_type'])
        # If we have images, always use "Images", otherwise use the stored value
        if has_social_images:
            st.session_state['footer_social_type'] = "Images"
        else:
            st.session_state['footer_social_type'] = social_media_type_str if social_media_type_str in ["URLs Only", "Images"] else "URLs Only"
    elif has_social_images:
        # If no type specified but we have images, default to "Images"
        st.session_state['footer_social_type'] = "Images"
    if 'social_media_label' in footer_config:
        st.session_state['footer_social_label'] = footer_config['social_media_label']
    if 'social_label_color' in footer_config:
        st.session_state['footer_social_label_color'] = footer_config['social_label_color']
    if 'social_label_size' in footer_config:
        st.session_state['footer_social_label_size'] = int(footer_config['social_label_size'])
    if 'social_label_bold' in footer_config:
        st.session_state['footer_social_label_bold'] = bool(footer_config['social_label_bold'])
    if 'social_image_width' in footer_config:
        width = footer_config['social_image_width']
        if width is not None:
            st.session_state['footer_social_image_width'] = int(width)
    if 'facebook_url' in footer_config:
        st.session_state['footer_facebook'] = footer_config['facebook_url']
    if 'facebook_image_base64' in footer_config and footer_config.get('facebook_image_base64'):
        st.session_state['footer_facebook_image_base64'] = footer_config['facebook_image_base64']
    if 'linkedin_url' in footer_config:
        st.session_state['footer_linkedin'] = footer_config['linkedin_url']
    if 'linkedin_image_base64' in footer_config and footer_config.get('linkedin_image_base64'):
        st.session_state['footer_linkedin_image_base64'] = footer_config['linkedin_image_base64']
    if 'xing_url' in footer_config:
        st.session_state['footer_xing'] = footer_config['xing_url']
    if 'xing_image_base64' in footer_config and footer_config.get('xing_image_base64'):
        st.session_state['footer_xing_image_base64'] = footer_config['xing_image_base64']
    if 'instagram_url' in footer_config:
        st.session_state['footer_instagram'] = footer_config['instagram_url']
    if 'instagram_image_base64' in footer_config and footer_config.get('instagram_image_base64'):
        st.session_state['footer_instagram_image_base64'] = footer_config['instagram_image_base64']
    
    # Apply subscription config
    if subscription_config:
        if 'company_name' in subscription_config:
            st.session_state['company_name'] = subscription_config['company_name']
        if 'address' in subscription_config:
            st.session_state['address'] = subscription_config['address']
        if 'copyright_text' in subscription_config:
            st.session_state['copyright_text'] = subscription_config['copyright_text']
        if 'disclaimer_text' in subscription_config:
            st.session_state['disclaimer_text'] = subscription_config['disclaimer_text']
        if 'unsubscribe_link' in subscription_config:
            st.session_state['unsubscribe_link'] = subscription_config['unsubscribe_link']
        if 'view_online_link' in subscription_config:
            st.session_state['view_online_link'] = subscription_config['view_online_link']
        if 'footer_color' in subscription_config:
            st.session_state['footer_color'] = subscription_config['footer_color']


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Newsletter Builder",
        page_icon="📧",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📧 Newsletter Builder")
    st.markdown("Create responsive HTML newsletters with dynamic content layers")
    
    # Show template save/load/delete success message at the top if available
    # Messages auto-disappear after 10 seconds
    current_time = time.time()
    
    if st.session_state.get('template_save_success_message'):
        message_time = st.session_state.get('template_save_success_message_time', current_time)
        if current_time - message_time < 10:
            st.success(st.session_state['template_save_success_message'])
        else:
            # Message expired, remove it
            del st.session_state['template_save_success_message']
            if 'template_save_success_message_time' in st.session_state:
                del st.session_state['template_save_success_message_time']
    
    if st.session_state.get('template_load_success_message'):
        message_time = st.session_state.get('template_load_success_message_time', current_time)
        if current_time - message_time < 10:
            st.success(st.session_state['template_load_success_message'])
        else:
            # Message expired, remove it
            del st.session_state['template_load_success_message']
            if 'template_load_success_message_time' in st.session_state:
                del st.session_state['template_load_success_message_time']
    
    if st.session_state.get('template_delete_success_message'):
        message_time = st.session_state.get('template_delete_success_message_time', current_time)
        if current_time - message_time < 10:
            st.success(st.session_state['template_delete_success_message'])
        else:
            # Message expired, remove it
            del st.session_state['template_delete_success_message']
            if 'template_delete_success_message_time' in st.session_state:
                del st.session_state['template_delete_success_message_time']
    
    # Note: Messages will automatically disappear after 10 seconds on the next user interaction
    # This is the standard Streamlit behavior - the page re-renders when user interacts with any widget
    # The messages are already set to expire after 10 seconds and will be removed on next render
    
    # Template Management Section
    st.header("💾 Template Management")
    col_save, col_load = st.columns(2)
    
    # Get MongoDB manager and template names
    mongo_manager = get_mongo_manager()
    template_names = mongo_manager.load_templates()
    
    # Check if a template is currently loaded
    loaded_template_name = st.session_state.get('loaded_template_name', None)
    
    # Determine if we're in "update mode" (template loaded) or "save mode" (new template)
    is_update_mode = loaded_template_name is not None
    
    with col_save:
        st.subheader("Save Template")
        
        # Set template name value based on loaded template or empty
        if is_update_mode:
            # When a template is loaded, sync the widget state before creating it
            if st.session_state.get('template_name_input') != loaded_template_name:
                st.session_state['template_name_input'] = loaded_template_name
            template_name_value = loaded_template_name
            template_name_disabled = True
            # Clear the flag if it was set
            if st.session_state.get('clear_template_name_input', False):
                st.session_state['clear_template_name_input'] = False
        else:
            # When not in update mode, allow user to type
            # Check if we need to clear the field (when switching from update to save mode)
            if st.session_state.get('clear_template_name_input', False):
                # Clear the field by removing the key from session_state before widget creation
                if 'template_name_input' in st.session_state:
                    del st.session_state['template_name_input']
                st.session_state['clear_template_name_input'] = False
                template_name_value = ''
            else:
                # Use existing value from widget or empty
                template_name_value = st.session_state.get('template_name_input', '')
            template_name_disabled = False
        
        template_name = st.text_input(
            "Template Name",
            value=template_name_value,
            key="template_name_input",
            help="Enter a unique name for this template",
            placeholder="e.g., Monthly Newsletter Template",
            disabled=template_name_disabled
        )
        
        # Determine button label and action
        if is_update_mode:
            button_label = "💾 Update Template"
        else:
            button_label = "💾 Save Template"
        
        if st.button(button_label, type="primary", width='stretch'):
            if not template_name or not template_name.strip():
                st.error("⚠️ Please enter a name for the template.")
            else:
                # Get MongoDB manager
                mongo_manager = get_mongo_manager()
                
                # We need to collect all data first, but we'll do it after rendering
                # Store flag to save after rendering
                st.session_state['save_template_flag'] = True
                st.session_state['template_name_to_save'] = template_name.strip()
                # If updating, keep the loaded template name in session state
                if is_update_mode:
                    st.session_state['loaded_template_name'] = template_name.strip()
    
    with col_load:
        st.subheader("Load Template")
        
        # Prepare options with default "---" option
        default_option = "---"
        if template_names:
            selectbox_options = [default_option] + template_names
        else:
            selectbox_options = [default_option]
        
        # Get current selection or default to "---"
        current_selection = st.session_state.get('template_selectbox', default_option)
        # If current selection is not in options (e.g., template was deleted), reset to default
        if current_selection not in selectbox_options:
            current_selection = default_option
            st.session_state['template_selectbox'] = default_option
        
        selected_template = st.selectbox(
            "Select Template",
            options=selectbox_options,
            key="template_selectbox",
            help="Choose a template to load",
            index=selectbox_options.index(current_selection) if current_selection in selectbox_options else 0
        )
        
        # Clear loaded template name if "---" is selected
        if selected_template == default_option and loaded_template_name is not None:
            st.session_state['loaded_template_name'] = None
            # Set flag to clear template name input field
            st.session_state['clear_template_name_input'] = True
        
        # Determine if buttons should be disabled
        buttons_disabled = (selected_template == default_option)
        
        col_load_btn, col_delete_btn = st.columns(2)
        
        with col_load_btn:
            if st.button("📂 Load Template", type="secondary", width='stretch', disabled=buttons_disabled):
                template_data = mongo_manager.load_template_data(selected_template)
                if template_data:
                    apply_template_to_session_state(template_data)
                    # Store success message to show at the top
                    st.session_state['template_load_success_message'] = f"✅ Template '{selected_template}' loaded successfully!"
                    st.session_state['template_load_success_message_time'] = time.time()
                    # Rerun to show the message at the top and update the template name field
                    st.rerun()
                else:
                    st.error("⚠️ Error loading the template.")
        
        with col_delete_btn:
            if st.button("🗑️ Delete Template", type="secondary", width='stretch', disabled=buttons_disabled):
                # First confirmation: Set flag to show delete confirmation dialog
                st.session_state['show_delete_confirmation'] = True
                st.session_state['template_to_delete'] = selected_template
                st.rerun()
            
            # Show delete confirmation dialog if flag is set
            if st.session_state.get('show_delete_confirmation', False) and st.session_state.get('template_to_delete') == selected_template:
                st.warning(f"⚠️ You are about to delete the template: **{selected_template}**")
                st.markdown("This action cannot be undone.")
                
                # Double confirmation
                confirm_checkbox = st.checkbox(
                    f"I confirm I want to delete '{selected_template}'",
                    key="delete_confirmation_checkbox"
                )
                
                col_confirm, col_cancel = st.columns(2)
                
                with col_confirm:
                    if st.button("🗑️ Confirm Delete", type="primary", width='stretch', disabled=not confirm_checkbox):
                        if confirm_checkbox:
                            success = mongo_manager.delete_template(selected_template)
                            if success:
                                # Store success message to show at the top
                                st.session_state['template_delete_success_message'] = f"🗑️ Template '{selected_template}' deleted successfully!"
                                st.session_state['template_delete_success_message_time'] = time.time()
                                # Clear confirmation flags
                                st.session_state['show_delete_confirmation'] = False
                                st.session_state['template_to_delete'] = None
                                # Clear loaded template name if the deleted template was loaded
                                if st.session_state.get('loaded_template_name') == selected_template:
                                    st.session_state['loaded_template_name'] = None
                                # Reset selectbox to default
                                st.session_state['template_selectbox'] = default_option
                                # Rerun to refresh template list and show message
                                st.rerun()
                            else:
                                st.error("⚠️ Error deleting the template.")
                
                with col_cancel:
                    if st.button("❌ Cancel", width='stretch'):
                        # Clear confirmation flags
                        st.session_state['show_delete_confirmation'] = False
                        st.session_state['template_to_delete'] = None
                        st.rerun()
        
        # Show message if no templates available
        if not template_names:
            st.info("No templates saved yet.")
    
    st.divider()
    
    # Render sidebar and get basic configuration
    config = render_sidebar()
    
    # Header Configuration (in main area)
    header_config = render_header_config(config['email_subject'])
    st.divider()
    
    # Main content area - Content Layers
    st.header("📝 Content Layers")
    
    # Generate forms for each layer
    layers = []
    for i in range(1, config['num_layers'] + 1):
        layer_data = render_layer_form(i)
        layers.append(layer_data)
        st.divider()
    
    # Validate that layer orders are unique
    orders = [layer.get('order', i) for i, layer in enumerate(layers, start=1)]
    duplicate_orders = [order for order in set(orders) if orders.count(order) > 1]
    
    if duplicate_orders:
        st.error(f"⚠️ Newsletter cannot be generated: The layers have duplicated orders. Duplicated orders: {', '.join(map(str, sorted(duplicate_orders)))}. Please assign a unique order to each layer before generating.")
        # Still sort layers for display, but warn user
        layers = sorted(layers, key=lambda x: (x.get('order', 999), layers.index(x)))
    else:
        # Sort layers by order before generating HTML
        layers = sorted(layers, key=lambda x: x.get('order', 999))
    
    # Footer Configuration (in main area)
    footer_config = render_footer_config()
    st.divider()
    
    # Subscription Configuration (in main area) - only show if enabled
    subscription_config = None
    if config.get('include_subscription', True):
        subscription_config = render_subscription_config()
        st.divider()
    
    # Generate Newsletter button
    if st.button("🚀 Generate Newsletter", type="primary", width='stretch'):
        # Validate layer orders again before generating
        orders = [layer.get('order', i) for i, layer in enumerate(layers, start=1)]
        duplicate_orders = [order for order in set(orders) if orders.count(order) > 1]
        
        if duplicate_orders:
            st.error(f"⚠️ Newsletter cannot be generated: The layers have duplicated orders. Duplicated orders: {', '.join(map(str, sorted(duplicate_orders)))}. Please assign a unique order to each layer before generating.")
        else:
            # Generate HTML
            html_content = NewsletterGenerator.generate_html(
                subject=config['email_subject'],
                background_color=config['background_color'],
                text_color=config['text_color'],
                header_config=header_config,
                layers=layers,
                footer_config=footer_config,
                subscription_config=subscription_config,
                max_width=config['max_width'],
                font_family=config['font_family']
            )
            
            # Store in session state for download
            st.session_state['newsletter_html'] = html_content
            st.session_state['newsletter_subject'] = config['email_subject']
            
            st.success("✅ Newsletter generated successfully!")
    
    # Handle template saving (after all data is collected)
    if st.session_state.get('save_template_flag', False):
        template_name = st.session_state.get('template_name_to_save', '')
        if template_name:
            mongo_manager = get_mongo_manager()
            success = mongo_manager.save_template(
                name=template_name,
                config=config,
                header_config=header_config,
                layers=layers,
                footer_config=footer_config,
                subscription_config=subscription_config
            )
            # Clear the flag BEFORE rerun to prevent infinite loop
            st.session_state['save_template_flag'] = False
            st.session_state['template_name_to_save'] = ''
            
            if success:
                # Store success message to show at the top
                st.session_state['template_save_success_message'] = f"✅ Template '{template_name}' saved successfully!"
                st.session_state['template_save_success_message_time'] = time.time()
                # Rerun to show the message at the top
                st.rerun()
    
    # Preview and Download section
    if 'newsletter_html' in st.session_state:
        st.header("Preview & Download")
        
        # Preview
        st.subheader("Live Preview")
        st.components.v1.html(
            st.session_state['newsletter_html'],
            height=800,
            scrolling=True
        )
        
        # Download button
        st.subheader("Download Newsletter")
        filename = f"{st.session_state['newsletter_subject'].replace(' ', '_')}_newsletter.html"
        
        st.download_button(
            label="📥 Download HTML File",
            data=st.session_state['newsletter_html'],
            file_name=filename,
            mime="text/html",
            width='stretch'
        )


if __name__ == "__main__":
    main()
