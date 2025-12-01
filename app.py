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
        header_config: Dict,
        layers: List[Dict],
        footer_config: Dict,
        max_width: int = 1000,
        font_family: str = "Arial, sans-serif"
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
            max_width: Maximum width of the newsletter in pixels
            font_family: Font family for the newsletter text
            
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
            f'<body style="margin: 0; padding: 0; font-family: {font_family}; background-color: #f4f4f4;">',
            '<table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f4f4f4;">',
            '<tr>',
            '<td align="center" style="padding: 20px 0;">',
            f'<table role="presentation" style="width: {max_width}px; max-width: 100%; border-collapse: collapse; '
            f'background-color: {background_color}; margin: 0 auto;">',
        ]

        html_parts.extend(NewsletterGenerator._generate_header_html(subject, header_config))
        
        # Add each layer
        for layer in layers:
            html_parts.extend(NewsletterGenerator._generate_layer_html(layer, text_color))

        html_parts.extend(NewsletterGenerator._generate_footer_html(footer_config))
        
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
                f'<h2 style="color: {text_color}; margin: 0 0 10px 0; font-size: 26px; font-weight: 700; line-height: 1.2;">'
                f'{layer["title"]}</h2>'
            )
        
        # Subtitle (H3) - Subtítulo (H
        if layer.get('subtitle'):
            html_parts.append(
                f'<h3 style="color: {text_color}; margin: 0 0 15px 0; font-size: 18px; font-weight: 500; line-height: 1.4; opacity: 0.8;">'
                f'{layer["subtitle"]}</h3>'
            )
        
        # Main content - Contenido principal
        if layer.get('content'):
            content = layer['content'].replace('\n', '<br>')
            html_parts.append(
                f'<p style="color: {text_color}; margin: 0 0 20px 0; font-size: 16px; line-height: 1.5;">'
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

        # 1. Pre-Header Text (Texto oculto para la vista previa del email) - Solo si se proporciona
        pre_header_text = header_config.get('pre_header_text', '').strip()
        if pre_header_text:  # Solo incluir si el usuario lo completa
            html_parts.append('<tr>')
            # Estilos de email para ocultar texto pero hacerlo legible para el pre-header
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
        if not header_title:  # Si no hay título, usar el subject como fallback
            header_title = subject
        header_text = header_config.get('header_text', '').strip()
        header_image_base64 = header_config.get('header_image_base64')
        header_image_url = header_config.get('header_image_url')
        header_bg_color = header_config.get('header_bg_color', '#ffffff')
        image_width = header_config.get('image_width', 600)
        title_font_size = header_config.get('title_font_size', 28)
        text_font_size = header_config.get('text_font_size', 16)
        
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
                f'<h1 style="color: #333333; font-size: {title_font_size}px; margin: 0; font-weight: bold; line-height: 1.3;">{header_title}</h1>'
            )
            html_parts.append('</td>')
            html_parts.append('</tr>')
        
        # 2.4. Header Text Row
        if header_text:
            # Convert newlines to <br> tags
            formatted_text = header_text.replace('\n', '<br>')
            html_parts.append('<tr>')
            html_parts.append(f'<td style="padding: 0 20px 20px 20px; background-color: {header_bg_color};">')
            html_parts.append(
                f'<p style="color: #333333; font-size: {text_font_size}px; margin: 0; line-height: 1.5;">{formatted_text}</p>'
            )
            html_parts.append('</td>')
            html_parts.append('</tr>')

        return html_parts

    @staticmethod
    def _generate_footer_html(footer_config: Dict) -> List[str]:
        """
        Generates the legal footer with company info and unsubscribe link.
        
        Args:
            footer_config: Dictionary with company_name, address, copyright_text, 
                          unsubscribe_link, view_online_link, disclaimer_text
        """
        footer_color = footer_config.get('footer_color', "#999999")
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
        disclaimer = footer_config.get('disclaimer_text', 'This email was sent to you because you subscribed to our newsletter.')
        if disclaimer:
            html_parts.append(f'{disclaimer}<br>')
        
        # Copyright
        company_name = footer_config.get('company_name', 'Your Company Name')
        copyright_text = footer_config.get('copyright_text', f'© 2024 {company_name}. All rights reserved.')
        # Replace {company} placeholder if present
        if copyright_text and '{company}' in copyright_text:
            copyright_text = copyright_text.replace('{company}', company_name)
        if copyright_text:
            html_parts.append(f'{copyright_text}<br>')
        
        # Address
        address = footer_config.get('address', '123 Main Street, Suite 400, City, State 12345')
        if address:
            html_parts.append(f'{address}<br><br>')
        
        # Enlaces de Unsubscribe/View Online
        unsubscribe_link = footer_config.get('unsubscribe_link', '#UNSUBSCRIBE_LINK')
        view_online_link = footer_config.get('view_online_link', '#VIEW_ONLINE_LINK')
        
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
        
        max_width = st.number_input(
            "Maximum Newsletter Width (px)",
            min_value=300,
            max_value=1200,
            value=1000,
            step=10,
            help="Maximum width of the newsletter in pixels"
        )
        
        font_family = st.selectbox(
            "Font Family",
            options=[
                "Arial, sans-serif",
                "Helvetica, sans-serif",
                "Georgia, serif",
                "Times New Roman, serif",
                "Verdana, sans-serif",
                "Courier New, monospace",
                "Trebuchet MS, sans-serif",
                "Comic Sans MS, cursive"
            ],
            index=0,
            help="Font family for the newsletter text"
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
            'max_width': int(max_width),
            'font_family': font_family,
            'background_color': background_color,
            'text_color': text_color
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
    
    # Image source selection
    image_source = st.radio(
        "Image Source",
        options=["External URL", "Upload Image (Base64)"],
        key="header_image_source",
        help="Choose how to provide the header image"
    )
    
    col1, col2 = st.columns(2)
    
    header_image_base64 = None
    header_image_url = None
    
    with col1:
        if image_source == "External URL":
            header_image_url = st.text_input(
                "Header Image URL",
                value="",
                key="header_image_url",
                help="Enter the URL of the image from an external server"
            )
        else:
            header_image_file = st.file_uploader(
                "Header Logo/Image",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG'],
                key="header_image",
                help="Upload a logo or image for the header (optional)"
            )
            # Process header image
            if header_image_file is not None:
                header_image_base64 = ImageProcessor.convert_to_base64(header_image_file)
        
        header_title = st.text_input(
            "Header Title",
            value="Sehr geehrte/r Frau/Herr....",
            placeholder="Ejemplo: Sehr geehrte/r Frau/Herr...",
            key="header_title",
            help="The title displayed in the newsletter header"
        )
        
        header_text = st.text_area(
            "Header Text",
            value="ich freue mich Ihnen unsere neuesten Angebote der beruflichen Fortbildungszentren der Bayerischen Wirtschaft (bfz) gGmbH vorzustellen. Mit unserer Jahrzehnten langen Erfahrung sind wir Ihr erfolgreicher Partner für Beratung, Bildung und Integration für Arbeitnehmer*innen.",
            key="header_text",
            help="Text content below the title in the header",
            height=100
        )
    
    with col2:
        pre_header_text = st.text_input(
            "Pre-Header Text (Opcional)",
            value="",
            placeholder="Texto oculto para vista previa de email",
            key="pre_header_text",
            help="Hidden text shown in email preview (opcional - solo se incluye si se completa)"
        )
        
        header_bg_color = st.color_picker(
            "Header Background Color",
            value="#ffffff",
            key="header_bg_color",
            help="Background color for the header section"
        )
        
        # Image size configuration
        image_width = st.number_input(
            "Image Width (px)",
            min_value=50,
            max_value=1200,
            value=1000,
            step=10,
            key="header_image_width",
            help="Width of the header image in pixels"
        )
        
        # Font sizes
        title_font_size = st.number_input(
            "Title Font Size (px)",
            min_value=10,
            max_value=72,
            value=28,
            step=1,
            key="header_title_font_size",
            help="Font size for the header title"
        )
        
        text_font_size = st.number_input(
            "Header Text Font Size (px)",
            min_value=10,
            max_value=48,
            value=16,
            step=1,
            key="header_text_font_size",
            help="Font size for the header text"
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
        'text_font_size': text_font_size
    }


def render_footer_config() -> Dict:
    """
    Render footer configuration form in the main area.
    
    Returns:
        Dictionary with footer configuration
    """
    st.header("📄 Footer Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        company_name = st.text_input(
            "Company Name",
            value="Your Company Name",
            key="company_name",
            help="Your company or organization name"
        )
        
        address = st.text_area(
            "Company Address",
            value="123 Main Street, Suite 400, City, State 12345",
            key="address",
            help="Company physical address",
            height=100
        )
        
        copyright_text = st.text_input(
            "Copyright Text",
            value="© 2024 Your Company Name. All rights reserved.",
            key="copyright_text",
            help="Copyright notice text (you can use {company} placeholder)"
        )
    
    with col2:
        disclaimer_text = st.text_area(
            "Disclaimer Text",
            value="This email was sent to you because you subscribed to our newsletter.",
            key="disclaimer_text",
            help="Legal disclaimer text",
            height=100
        )
        
        unsubscribe_link = st.text_input(
            "Unsubscribe Link",
            value="#UNSUBSCRIBE_LINK",
            key="unsubscribe_link",
            help="URL for unsubscribe link"
        )
        
        view_online_link = st.text_input(
            "View Online Link",
            value="#VIEW_ONLINE_LINK",
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        title = st.text_input(
            f"Title (H2) - Layer {layer_number}",
            key=f"title_{layer_number}",
            value="P.I.A SPEED Einzelcoaching",
            placeholder="Enter layer title..."
        )
    
    with col2:
        subtitle = st.text_input(
            f"Subtitle (H3) - Layer {layer_number}",
            key=f"subtitle_{layer_number}",
            value="Perspektive. Integration. Arbeit.",
            placeholder="Enter layer subtitle..."
        )
    
    content = st.text_area(
        f"Main Content - Layer {layer_number}",
        key=f"content_{layer_number}",
        value="Ist ein individuell kombinierbares Angebot für Menschen, denen ohne Unterstützung der Einstieg in den deutschen Arbeitsmarkt nicht gelingt. Diese Maßnahme basiert auf dem Zertifikat: 2025M100864-10001.",
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
    
    # Footer Configuration (in main area)
    footer_config = render_footer_config()
    st.divider()
    
    # Generate Newsletter button
    if st.button("🚀 Generate Newsletter", type="primary", use_container_width=True):
        # Generate HTML
        html_content = NewsletterGenerator.generate_html(
            subject=config['email_subject'],
            background_color=config['background_color'],
            text_color=config['text_color'],
            header_config=header_config,
            layers=layers,
            footer_config=footer_config,
            max_width=config['max_width'],
            font_family=config['font_family']
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
