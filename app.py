"""
Newsletter Builder - Streamlit Application
A web application for generating responsive HTML newsletters with dynamic content layers.
"""

import base64
import io
from typing import Dict, List, Optional

import streamlit as st
from PIL import Image


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
            
            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            buffer.seek(0)
            
            # Encode to Base64
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            # Determine MIME type based on original format
            mime_type = 'image/jpeg'
            if image_file.type in ['image/png', 'image/PNG']:
                mime_type = 'image/png'
            
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
        layers: List[Dict]
    ) -> str:
        """
        Generate complete HTML newsletter with inline CSS.
        
        Args:
            subject: Email subject line
            background_color: Background color hex code
            text_color: Primary text color hex code
            layers: List of layer dictionaries containing content data
            
        Returns:
            Complete HTML string ready for email
        """
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            f'<meta charset="UTF-8">',
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'<title>{subject}</title>',
            '</head>',
            '<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">',
            '<table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f4f4f4;">',
            '<tr>',
            '<td align="center" style="padding: 20px 0;">',
            '<table role="presentation" style="width: 600px; max-width: 100%; border-collapse: collapse; '
            f'background-color: {background_color}; margin: 0 auto;">',
        ]
        
        # Add each layer
        for layer in layers:
            html_parts.extend(NewsletterGenerator._generate_layer_html(layer, text_color))
        
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
        Generate HTML for a single content layer.
        
        Args:
            layer: Dictionary containing layer content (title, subtitle, content, image, alignment)
            text_color: Primary text color hex code
            
        Returns:
            List of HTML strings for the layer
        """
        html_parts = []
        
        # Layer container
        html_parts.append('<tr>')
        html_parts.append('<td style="padding: 30px 20px;">')
        
        # Image section (if present)
        if layer.get('image_base64'):
            alignment = layer.get('image_alignment', 'center').lower()
            align_style = {
                'left': 'text-align: left;',
                'center': 'text-align: center;',
                'right': 'text-align: right;'
            }.get(alignment, 'text-align: center;')
            
            html_parts.append(f'<div style="{align_style} margin-bottom: 20px;">')
            html_parts.append(
                f'<img src="{layer["image_base64"]}" '
                f'alt="{layer.get("title", "Newsletter Image")}" '
                f'style="max-width: 100%; height: auto; border-radius: 8px;">'
            )
            html_parts.append('</div>')
        
        # Title (H2)
        if layer.get('title'):
            html_parts.append(
                f'<h2 style="color: {text_color}; margin: 0 0 10px 0; font-size: 24px; font-weight: bold;">'
                f'{layer["title"]}</h2>'
            )
        
        # Subtitle (H3)
        if layer.get('subtitle'):
            html_parts.append(
                f'<h3 style="color: {text_color}; margin: 0 0 15px 0; font-size: 18px; font-weight: 600; opacity: 0.9;">'
                f'{layer["subtitle"]}</h3>'
            )
        
        # Main content
        if layer.get('content'):
            # Convert newlines to <br> tags
            content = layer['content'].replace('\n', '<br>')
            html_parts.append(
                f'<p style="color: {text_color}; margin: 0 0 20px 0; font-size: 16px; line-height: 1.6;">'
                f'{content}</p>'
            )
        
        # Close layer container
        html_parts.append('</td>')
        html_parts.append('</tr>')
        
        # Add separator between layers
        html_parts.append('<tr>')
        html_parts.append('<td style="border-bottom: 1px solid rgba(0,0,0,0.1); padding: 0 20px;"></td>')
        html_parts.append('</tr>')
        
        return html_parts


def render_sidebar() -> Dict:
    """
    Render sidebar configuration inputs.
    
    Returns:
        Dictionary with configuration values
    """
    with st.sidebar:
        st.header("📧 Newsletter Configuration")
        
        email_subject = st.text_input(
            "Email Subject",
            value="Newsletter",
            help="The subject line for your newsletter email"
        )
        
        num_layers = st.number_input(
            "Number of Layers",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
            help="Select the number of content sections (layers) in your newsletter"
        )
        
        st.subheader("Color Settings")
        background_color = st.color_picker(
            "Background Color",
            value="#FFFFFF",
            help="Choose the background color for your newsletter"
        )
        
        text_color = st.color_picker(
            "Text Color",
            value="#333333",
            help="Choose the primary text color for your newsletter"
        )
        
        return {
            'email_subject': email_subject,
            'num_layers': int(num_layers),
            'background_color': background_color,
            'text_color': text_color
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        title = st.text_input(
            f"Title (H2) - Layer {layer_number}",
            key=f"title_{layer_number}",
            placeholder="Enter layer title..."
        )
    
    with col2:
        subtitle = st.text_input(
            f"Subtitle (H3) - Layer {layer_number}",
            key=f"subtitle_{layer_number}",
            placeholder="Enter layer subtitle..."
        )
    
    content = st.text_area(
        f"Main Content - Layer {layer_number}",
        key=f"content_{layer_number}",
        placeholder="Enter the main content for this layer...",
        height=150
    )
    
    col3, col4 = st.columns(2)
    
    with col3:
        image_file = st.file_uploader(
            f"Image - Layer {layer_number}",
            type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG'],
            key=f"image_{layer_number}",
            help="Upload an image for this layer (JPG or PNG)"
        )
    
    with col4:
        image_alignment = st.selectbox(
            f"Image Alignment - Layer {layer_number}",
            options=['Left', 'Center', 'Right'],
            index=1,
            key=f"alignment_{layer_number}"
        )
    
    # Process image to Base64
    image_base64 = None
    if image_file is not None:
        image_base64 = ImageProcessor.convert_to_base64(image_file)
    
    return {
        'title': title,
        'subtitle': subtitle,
        'content': content,
        'image_base64': image_base64,
        'image_alignment': image_alignment
    }


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
    
    # Render sidebar and get configuration
    config = render_sidebar()
    
    # Main content area
    st.header("Content Layers")
    
    # Generate forms for each layer
    layers = []
    for i in range(1, config['num_layers'] + 1):
        layer_data = render_layer_form(i)
        layers.append(layer_data)
        st.divider()
    
    # Generate Newsletter button
    if st.button("🚀 Generate Newsletter", type="primary", use_container_width=True):
        # Generate HTML
        html_content = NewsletterGenerator.generate_html(
            subject=config['email_subject'],
            background_color=config['background_color'],
            text_color=config['text_color'],
            layers=layers
        )
        
        # Store in session state for download
        st.session_state['newsletter_html'] = html_content
        st.session_state['newsletter_subject'] = config['email_subject']
        
        st.success("✅ Newsletter generated successfully!")
    
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
            use_container_width=True
        )


if __name__ == "__main__":
    main()
