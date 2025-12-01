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
        content_bold = layer.get('content_bold', False)
        
        # Layer container with padding
        html_parts.append('<tr>')
        html_parts.append(f'<td style="padding: {padding}px 20px;">')
        
        # Create table for image and text layout
        html_parts.append('<table role="presentation" style="width: 100%; border-collapse: collapse;">')
        html_parts.append('<tr>')
        
        # Image on left or right
        if image_src and image_src.strip() and image_alignment == 'left':
            # Image column (left) - transparent background to preserve PNG transparency
            html_parts.append(f'<td style="vertical-align: top; padding-right: 20px; width: {image_width}px; background-color: transparent;">')
            html_parts.append(
                f'<img src="{image_src}" alt="{title or "Layer Image"}" '
                f'width="{image_width}" style="width: {image_width}px; max-width: 100%; height: auto; display: block; border: 0; outline: none; background-color: transparent;">'
            )
            html_parts.append('</td>')
            
            # Text column (right)
            html_parts.append('<td style="vertical-align: top;">')
            html_parts.extend(NewsletterGenerator._generate_layer_text(
                title, subtitle, subtitle2, content,
                title_color, subtitle_color, subtitle2_color, content_color,
                title_font_size, subtitle_font_size, subtitle2_font_size, content_font_size,
                title_bold, subtitle_bold, subtitle2_bold, content_bold
            ))
            html_parts.append('</td>')
            
        elif image_src and image_src.strip() and image_alignment == 'right':
            # Text column (left) - use auto width to allow proper layout
            html_parts.append('<td style="vertical-align: top; padding-right: 20px;">')
            html_parts.extend(NewsletterGenerator._generate_layer_text(
                title, subtitle, subtitle2, content,
                title_color, subtitle_color, subtitle2_color, content_color,
                title_font_size, subtitle_font_size, subtitle2_font_size, content_font_size,
                title_bold, subtitle_bold, subtitle2_bold, content_bold
            ))
            html_parts.append('</td>')
            
            # Image column (right) - transparent background to preserve PNG transparency
            html_parts.append(f'<td style="vertical-align: top; width: {image_width}px; background-color: transparent;">')
            html_parts.append(
                f'<img src="{image_src}" alt="{title or "Layer Image"}" '
                f'width="{image_width}" style="width: {image_width}px; max-width: 100%; height: auto; display: block; border: 0; outline: none; background-color: transparent;">'
            )
            html_parts.append('</td>')
        else:
            # No image, just text
            html_parts.append('<td style="vertical-align: top; width: 100%;">')
            html_parts.extend(NewsletterGenerator._generate_layer_text(
                title, subtitle, subtitle2, content,
                title_color, subtitle_color, subtitle2_color, content_color,
                title_font_size, subtitle_font_size, subtitle2_font_size, content_font_size,
                title_bold, subtitle_bold, subtitle2_bold, content_bold
            ))
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
        title_bold: bool, subtitle_bold: bool, subtitle2_bold: bool, content_bold: bool
    ) -> List[str]:
        """Generate HTML for layer text content (titles and body)."""
        html_parts = []
        
        # Determine font-weight based on bold setting
        title_weight = '700' if title_bold else '400'
        subtitle_weight = '600' if subtitle_bold else '400'
        subtitle2_weight = '500' if subtitle2_bold else '400'
        content_weight = '700' if content_bold else '400'
        
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
            formatted_content = content.replace('\n', '<br>')
            html_parts.append(
                f'<p style="color: {content_color}; margin: 0; font-size: {content_font_size}px; font-weight: {content_weight}; line-height: 1.5;">'
                f'{formatted_content}</p>'
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
                f'<h1 style="color: #000000; font-size: {title_font_size}px; margin: 0; font-weight: bold; line-height: 1.3;">{header_title}</h1>'
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
                f'<p style="color: #000000; font-size: {text_font_size}px; margin: 0; line-height: 1.5;">{formatted_text}</p>'
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
        image_width = footer_config.get('image_width', 600)
        footer_alignment = footer_config.get('footer_alignment', 'left').lower()
        
        company_name = footer_config.get('company_name', '')
        company_name_color = footer_config.get('company_name_color', '#000000')
        company_name_size = footer_config.get('company_name_size', 14)
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
        
        # Footer container with alignment
        html_parts.append('<tr>')
        html_parts.append(f'<td style="padding: 30px 20px; background-color: {footer_bg_color}; {align_style}">')
        
        # Image section (if provided)
        if image_src:
            html_parts.append('<div style="margin-bottom: 20px;">')
            html_parts.append(
                f'<img src="{image_src}" alt="{company_name or "Footer Image"}" '
                f'width="{image_width}" style="width: {image_width}px; max-width: 100%; height: auto; display: inline-block; border: 0; outline: none; background-color: transparent;">'
            )
            html_parts.append('</div>')
        
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
        
        # Social media links
        social_media_type = footer_config.get('social_media_type', 'URLs Only')
        social_image_width = footer_config.get('social_image_width', 30)
        
        facebook_url = footer_config.get('facebook_url', '')
        facebook_image_base64 = footer_config.get('facebook_image_base64')
        linkedin_url = footer_config.get('linkedin_url', '')
        linkedin_image_base64 = footer_config.get('linkedin_image_base64')
        twitter_url = footer_config.get('twitter_url', '')
        twitter_image_base64 = footer_config.get('twitter_image_base64')
        instagram_url = footer_config.get('instagram_url', '')
        instagram_image_base64 = footer_config.get('instagram_image_base64')
        
        social_links = []
        if social_media_type == "Images":
            if facebook_url and facebook_image_base64:
                social_links.append(
                    f'<a href="{facebook_url}" target="_blank" style="margin: 0 10px; display: inline-block;">'
                    f'<img src="{facebook_image_base64}" alt="Facebook" width="{social_image_width}" '
                    f'style="width: {social_image_width}px; height: auto; border: 0; outline: none;"></a>'
                )
            if linkedin_url and linkedin_image_base64:
                social_links.append(
                    f'<a href="{linkedin_url}" target="_blank" style="margin: 0 10px; display: inline-block;">'
                    f'<img src="{linkedin_image_base64}" alt="LinkedIn" width="{social_image_width}" '
                    f'style="width: {social_image_width}px; height: auto; border: 0; outline: none;"></a>'
                )
            if twitter_url and twitter_image_base64:
                social_links.append(
                    f'<a href="{twitter_url}" target="_blank" style="margin: 0 10px; display: inline-block;">'
                    f'<img src="{twitter_image_base64}" alt="X" width="{social_image_width}" '
                    f'style="width: {social_image_width}px; height: auto; border: 0; outline: none;"></a>'
                )
            if instagram_url and instagram_image_base64:
                social_links.append(
                    f'<a href="{instagram_url}" target="_blank" style="margin: 0 10px; display: inline-block;">'
                    f'<img src="{instagram_image_base64}" alt="Instagram" width="{social_image_width}" '
                    f'style="width: {social_image_width}px; height: auto; border: 0; outline: none;"></a>'
                )
        else:
            if facebook_url:
                social_links.append(f'<a href="{facebook_url}" target="_blank" style="color: #999999; text-decoration: none; margin: 0 10px; display: inline-block;">Facebook</a>')
            if linkedin_url:
                social_links.append(f'<a href="{linkedin_url}" target="_blank" style="color: #999999; text-decoration: none; margin: 0 10px; display: inline-block;">LinkedIn</a>')
            if twitter_url:
                social_links.append(f'<a href="{twitter_url}" target="_blank" style="color: #999999; text-decoration: none; margin: 0 10px; display: inline-block;">X</a>')
            if instagram_url:
                social_links.append(f'<a href="{instagram_url}" target="_blank" style="color: #999999; text-decoration: none; margin: 0 10px; display: inline-block;">Instagram</a>')
        
        if social_links:
            html_parts.append('<div style="margin-top: 20px;">')
            html_parts.append('<p style="color: #999999; margin: 0 0 10px 0; font-size: 11px;">Los canales de redes sociales de bfz gGmbH:</p>')
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
                "Oswald, sans-serif",
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
            value="#000000",
            help="Choose the primary text color for your newsletter"
        )
        
        include_subscription = st.checkbox(
            "Include Subscription Section",
            value=False,
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
            placeholder="Example: Sehr geehrte/r Frau/Herr...",
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
    Similar to header but for footer section.
    
    Returns:
        Dictionary with footer configuration
    """
    st.header("📄 Footer Configuration")
    
    # First row: Footer alignment | Footer Background Color
    col_row1_1, col_row1_2 = st.columns(2)
    with col_row1_1:
        footer_alignment = st.selectbox(
            "Footer Alignment",
            options=['Left', 'Center', 'Right'],
            index=1,
            key="footer_alignment",
            help="Alignment of the entire footer content (image and text)"
        )
    with col_row1_2:
        footer_bg_color = st.color_picker(
            "Footer Background Color",
            value="#ffffff",
            key="footer_bg_color",
            help="Background color for the footer section"
        )
    
    # Second row: Image Source (full width)
    image_source = st.radio(
        "Image Source",
        options=["External URL", "Upload Image (Base64)"],
        key="footer_image_source",
        help="Choose how to provide the footer image"
    )
    
    # Second row: Footer Image URL | Image Width (px)
    col_row2_1, col_row2_2 = st.columns(2)
    footer_image_base64 = None
    footer_image_url = None
    
    with col_row2_1:
        if image_source == "External URL":
            footer_image_url = st.text_input(
                "Footer Image URL",
                value="",
                key="footer_image_url",
                help="Enter the URL of the image from an external server"
            )
        else:
            footer_image_file = st.file_uploader(
                "Footer Logo/Image",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG'],
                key="footer_image",
                help="Upload a logo or image for the footer (optional)"
            )
            # Process footer image
            if footer_image_file is not None:
                footer_image_base64 = ImageProcessor.convert_to_base64(footer_image_file)
    
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
    
    # Third row: Company Name with styling
    col_cn_1, col_cn_2, col_cn_3, col_cn_4 = st.columns([3, 1, 1, 1])
    with col_cn_1:
        company_name = st.text_input(
            "Company Name",
            value="Berufliche Fortbildungszentren der Bayerischen Wirtschaft (bfz) gemeinnützige GmbH",
            placeholder="Example: bfz gGmbH",
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
            value=14,
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
            value="Sitz/Registergericht: München, Registernummer: HRB 121447",
            placeholder="Example: Sitz/Registergericht: München, Registernummer: HRB 121447",
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
            "Directors/Responsibles",
            value="Geschäftsführer: Sandra Stenger, Wolfgang Braun, Jörg Plesch",
            placeholder="Example: Geschäftsführer: Sandra Stenger, Wolfgang Braun, Jörg Plesch",
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
    social_media_type = st.radio(
        "Social Media Type",
        options=["URLs Only", "Images"],
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
    
    col_social1, col_social2 = st.columns(2)
    with col_social1:
        facebook_url = st.text_input(
            "Facebook URL",
            value="",
            key="footer_facebook",
            help="Facebook page URL"
        )
        if social_media_type == "Images":
            facebook_image = st.file_uploader(
                "Facebook Icon",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG', 'svg', 'SVG'],
                key="footer_facebook_image",
                help="Upload Facebook icon image"
            )
        else:
            facebook_image = None
        
        linkedin_url = st.text_input(
            "LinkedIn URL",
            value="",
            key="footer_linkedin",
            help="LinkedIn page URL"
        )
        if social_media_type == "Images":
            linkedin_image = st.file_uploader(
                "LinkedIn Icon",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG', 'svg', 'SVG'],
                key="footer_linkedin_image",
                help="Upload LinkedIn icon image"
            )
        else:
            linkedin_image = None
    
    with col_social2:
        twitter_url = st.text_input(
            "X (Twitter) URL",
            value="",
            key="footer_twitter",
            help="X (Twitter) page URL"
        )
        if social_media_type == "Images":
            twitter_image = st.file_uploader(
                "X (Twitter) Icon",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG', 'svg', 'SVG'],
                key="footer_twitter_image",
                help="Upload X (Twitter) icon image"
            )
        else:
            twitter_image = None
        
        instagram_url = st.text_input(
            "Instagram URL",
            value="",
            key="footer_instagram",
            help="Instagram page URL"
        )
        if social_media_type == "Images":
            instagram_image = st.file_uploader(
                "Instagram Icon",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG', 'svg', 'SVG'],
                key="footer_instagram_image",
                help="Upload Instagram icon image"
            )
        else:
            instagram_image = None
    
    # Process social media images to Base64
    facebook_image_base64 = None
    linkedin_image_base64 = None
    twitter_image_base64 = None
    instagram_image_base64 = None
    
    if social_media_type == "Images":
        if facebook_image:
            facebook_image_base64 = ImageProcessor.convert_to_base64(facebook_image)
        if linkedin_image:
            linkedin_image_base64 = ImageProcessor.convert_to_base64(linkedin_image)
        if twitter_image:
            twitter_image_base64 = ImageProcessor.convert_to_base64(twitter_image)
        if instagram_image:
            instagram_image_base64 = ImageProcessor.convert_to_base64(instagram_image)
    
    return {
        'footer_image_base64': footer_image_base64,
        'footer_image_url': footer_image_url,
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
        'directors_color': directors_color,
        'directors_size': directors_size,
        'directors_bold': directors_bold,
        'social_media_type': social_media_type,
        'social_image_width': social_image_width if social_media_type == "Images" else None,
        'facebook_url': facebook_url,
        'facebook_image_base64': facebook_image_base64,
        'linkedin_url': linkedin_url,
        'linkedin_image_base64': linkedin_image_base64,
        'twitter_url': twitter_url,
        'twitter_image_base64': twitter_image_base64,
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
    
    # Title 1 with styling
    col_title1_1, col_title1_2, col_title1_3, col_title1_4 = st.columns([3, 1, 1, 1])
    with col_title1_1:
        title = st.text_input(
            f"Title 1 (H2) - Layer {layer_number}",
            key=f"title_{layer_number}",
            value="P.I.A SPEED Einzelcoaching",
            placeholder="Enter main title..."
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
            value=True,
            key=f"title_bold_{layer_number}",
            help="Make title bold"
        )
    
    # Title 2 with styling
    col_title2_1, col_title2_2, col_title2_3, col_title2_4 = st.columns([3, 1, 1, 1])
    with col_title2_1:
        subtitle = st.text_input(
            f"Title 2 (H3) - Layer {layer_number}",
            key=f"subtitle_{layer_number}",
            value="Perspektive. Integration. Arbeit.",
            placeholder="Enter subtitle (green)..."
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
            value="Schnell und sicher im Umgang mit Bewerbungen und E-Service",
            placeholder="Enter third title..."
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
    
    content = st.text_area(
        f"Main Content - Layer {layer_number}",
        key=f"content_{layer_number}",
        value="Ist ein individuell kombinierbares Angebot für Menschen, denen ohne Unterstützung der Einstieg in den deutschen Arbeitsmarkt nicht gelingt. Diese Maßnahme basiert auf dem Zertifikat: 2025M100864-10001.",
        placeholder="Enter the main content for this layer...",
        height=150
    )
    
    # Main Content styling
    col_content1, col_content2, col_content3 = st.columns(3)
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
    with col_content3:
        content_bold = st.checkbox(
            f"Content Bold - Layer {layer_number}",
            value=False,
            key=f"content_bold_{layer_number}",
            help="Make content bold"
        )
    
    st.markdown("**Image Configuration**")
    
    # Image source selection
    image_source = st.radio(
        f"Image Source - Layer {layer_number}",
        options=["External URL", "Upload Image (Base64)"],
        key=f"image_source_{layer_number}",
        help="Choose how to provide the image",
        index=0  # Default to URL
    )
    
    col_img1, col_img2 = st.columns(2)
    
    image_base64 = None
    image_url = None
    
    with col_img1:
        if image_source == "External URL":
            image_url = st.text_input(
                f"Image URL - Layer {layer_number}",
                value="",
                key=f"image_url_{layer_number}",
                help="Enter the URL of the image from an external server"
            )
        else:
            image_file = st.file_uploader(
                f"Upload Image - Layer {layer_number}",
                type=['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG'],
                key=f"image_{layer_number}",
                help="Upload an image for this layer (JPG or PNG)"
            )
            # Process image to Base64
            if image_file is not None:
                image_base64 = ImageProcessor.convert_to_base64(image_file)
                if image_base64 is None:
                    st.warning(f"⚠️ Error processing image for Layer {layer_number}. Please try uploading again.")
        
        image_alignment = st.selectbox(
            f"Image Position - Layer {layer_number}",
            options=['Left', 'Right'],
            index=0,
            key=f"alignment_{layer_number}",
            help="Position of image relative to text"
        )
    
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
        'title': title,
        'subtitle': subtitle,
        'subtitle2': subtitle2,
        'content': content,
        'image_url': image_url,
        'image_base64': image_base64,
        'image_alignment': image_alignment,
        'image_width': image_width,
        'padding': padding,
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
        'content_color': content_color,
        'content_bold': content_bold
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
    
    # Subscription Configuration (in main area) - only show if enabled
    subscription_config = None
    if config.get('include_subscription', True):
        subscription_config = render_subscription_config()
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
            subscription_config=subscription_config,
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
