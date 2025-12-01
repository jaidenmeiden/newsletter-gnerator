"""
HTML Editor Component for Streamlit using Quill.js
"""
import streamlit.components.v1 as components
import os

# Path to the HTML file
_component_path = os.path.dirname(os.path.abspath(__file__))
_html_path = os.path.join(_component_path, "html_editor.html")

def html_editor(key: str, value: str = "", height: int = 300, label: str = ""):
    """
    Render a rich text HTML editor using Quill.js.
    
    Args:
        key: Unique key for the editor instance
        value: Initial HTML content
        height: Editor height in pixels
        label: Optional label for the editor
        
    Returns:
        HTML content from the editor (stored in session state)
    """
    # Read the HTML template
    try:
        with open(_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        return value
    
    # Replace placeholders
    html_content = html_content.replace('{{ELEMENT_ID}}', key)
    html_content = html_content.replace('{{INITIAL_VALUE}}', value.replace('"', '&quot;'))
    html_content = html_content.replace('height: 200px;', f'height: {height}px;')
    html_content = html_content.replace('min-height: 150px;', f'min-height: {height - 50}px;')
    
    # Initialize session state
    session_key = f"html_editor_{key}"
    if session_key not in st.session_state:
        st.session_state[session_key] = value
    
    # Render the component
    components.html(html_content, height=height + 100, key=f"editor_iframe_{key}")
    
    # Return current value from session state
    return st.session_state.get(session_key, value)

