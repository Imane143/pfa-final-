import streamlit as st

def add_theme_selector():
    # Initialization - Keep color scheme state
    if "color_scheme" not in st.session_state:
        st.session_state.color_scheme = 0
    
    # Define colors for each theme
    color_schemes = {
        "blue": {"primary": "#1E88E5", "secondary": "#BBDEFB"},
        "green": {"primary": "#43A047", "secondary": "#C8E6C9"}, 
        "purple": {"primary": "#8E24AA", "secondary": "#E1BEE7"},
        "orange": {"primary": "#FB8C00", "secondary": "#FFE0B2"}
    }
    
    color_keys = list(color_schemes.keys())
    active_color_key = color_keys[st.session_state.color_scheme]
    active_color = color_schemes[active_color_key]["primary"]
    active_secondary = color_schemes[active_color_key]["secondary"]
    
    # Create columns with buttons at the top right - ONLY COLOR BUTTON
    cols = st.columns([7, 1])
    
    # Button to change color with unique key
    with cols[1]:
        if st.button("🎨", key="color_button"):
            st.session_state.color_scheme = (st.session_state.color_scheme + 1) % len(color_keys)
            st.rerun()
    
    # Color variables
    bg_color = "#FFFFFF"
    text_color = "#000000"
    sidebar_bg = active_secondary
    card_bg = "#FFFFFF"
    input_bg = "#FFFFFF"
    border_color = active_color
    upload_bg = "#F5F5F5"
    upload_text = "#0075FF"
    upload_limit_text = "#666666"
    
    # Add this CSS to fix the sidebar collapse button specifically
    sidebar_button_css = f"""
    <style>
        /* Target all possible sidebar collapse button variations */
        button[data-testid="baseButton-headerNoPadding"],
        span[data-testid="collapseSidebarTrigger"] button,
        button[data-testid="collapseSidebarTrigger"],
        button[aria-label="Collapse sidebar"],
        button[aria-label="Toggle sidebar visibility"],
        section[data-testid="stSidebar"] span > button {{
            /* Fixed positioning */
            position: fixed;
            left: 16px;
            top: 50px;
            transform: none;
            
            /* Visual styling */
            background-color: {active_color};
            color: white;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            
            /* Layout */
            display: flex;
            align-items: center;
            justify-content: center;
            
            /* Visibility */
            opacity: 1;
            visibility: visible;
            
            /* Layer and borders */
            z-index: 9999;
            border: 2px solid white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }}
        
        /* Style the icon inside the button */
        button[data-testid="baseButton-headerNoPadding"] svg,
        span[data-testid="collapseSidebarTrigger"] button svg,
        button[data-testid="collapseSidebarTrigger"] svg,
        button[aria-label="Collapse sidebar"] svg,
        button[aria-label="Toggle sidebar visibility"] svg,
        section[data-testid="stSidebar"] span > button svg {{
            fill: white;
            color: white;
        }}
        
        /* Style for collapsed state */
        button[data-testid="collapsedControl"] {{
            position: fixed;
            left: 16px;
            top: 50px;
            background-color: {active_color};
            color: white;
            opacity: 1;
            visibility: visible;
            z-index: 9999;
        }}
    </style>
    """
    
    # Apply only the sidebar button CSS separately
    st.markdown(sidebar_button_css, unsafe_allow_html=True)
    
    # Keep the rest of your original CSS (excluding the sidebar button part)
    main_css = f"""
    <style>
        /* Global styles - Applied to all elements */
        body, .stApp, section, main, header, footer, div, span, p, a, button, input, textarea, select, option {{
            color: {text_color};
        }}
        
        /* Main body */
        body, .stApp, .main, section[data-testid="stAppViewContainer"], main, div.stApp > div {{
            background-color: {bg_color};
        }}
        
        /* Fix for header area - TOP BAR */
        header[data-testid="stHeader"], div.stHeader, section.main > div:first-child {{
            background-color: {bg_color};
        }}
        
        /* Main toolbar */
        div[data-testid="stToolbar"] {{
            background-color: {bg_color};
            color: {text_color};
        }}
        
        /* App frame and all containers */
        div[data-testid="AppFrame"], div[data-testid="stDecoration"], 
        div[data-testid="stStatusWidget"], div[data-testid="stAppViewBlockContainer"] {{
            background-color: {bg_color};
        }}
        
        /* Headers and titles */
        h1, h2, h3, h4, h5, h6, .stMarkdown {{
            color: {text_color};
        }}
        
        /* Sidebar */
        section[data-testid="stSidebar"], div.stSidebar, [data-testid="stSidebarUserContent"] {{
            background-color: {sidebar_bg};
            padding: 10px;
        }}
        
        /* Sidebar content - targeting the white boxes */
        [data-testid="stSidebarUserContent"] > div > div > div {{
            margin-bottom: 15px;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        /* Sidebar white boxes internal padding */
        [data-testid="stSidebarUserContent"] div[data-testid="stExpander"] {{
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        /* All other white box containers in sidebar */
        [data-testid="stSidebarUserContent"] > div > div > div > div {{
            background-color: {card_bg};
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
        }}
        
        /* CRITICAL FIX: Hide the "Press Enter to apply" message */
        .stTextInput div[data-baseweb="input"] + div, 
        .stPasswordInput div[data-baseweb="input"] + div,
        .stTextInput div[data-baseweb="base-input"] + div, 
        .stPasswordInput div[data-baseweb="base-input"] + div {{
            display: none;
        }}
        
        /* Ensure input fields show full content */
        .stTextInput input, .stPasswordInput input {{
            width: 100%;
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 14px;
            line-height: 1.5;
            text-overflow: ellipsis;
            white-space: nowrap;
            overflow: hidden;
            text-align: left;
        }}
        
        /* Make sure text inputs have enough height */
        div.stTextInput, div.stPasswordInput {{
            margin-bottom: 15px;
        }}
        
        /* Input container styles */
        div[data-baseweb="input-container"], div[data-baseweb="base-input"] {{
            width: 100%;
        }}
        
        /* Improve input field styling */
        .stTextInput div[data-baseweb="input"], 
        .stPasswordInput div[data-baseweb="input"],
        .stTextInput div[data-baseweb="base-input"], 
        .stPasswordInput div[data-baseweb="base-input"] {{
            background-color: {input_bg};
            padding: 0;
            width: 100%;
        }}
        
        /* Improve user account and conversation history sections */
        [data-testid="stSidebarUserContent"] h1,
        [data-testid="stSidebarUserContent"] h2,
        [data-testid="stSidebarUserContent"] h3 {{
            margin-top: 5px;
            margin-bottom: 10px;
            padding: 5px 10px;
        }}
        
        /* Tabs in sidebar (Login/Signup) */
        [data-testid="stSidebarUserContent"] [data-testid="stTabs"] {{
            background-color: transparent;
        }}
        
        [data-testid="stSidebarUserContent"] button[role="tab"] {{
            padding: 8px;
            margin-bottom: 8px;
        }}
        
        [data-testid="stSidebarUserContent"] [role="tabpanel"] {{
            padding: 5px;
        }}
        
        /* Login form fields */
        [data-testid="stSidebarUserContent"] .stTextInput, 
        [data-testid="stSidebarUserContent"] .stPasswordInput {{
            margin-bottom: 10px;
        }}
        
        /* Login button */
        [data-testid="stSidebarUserContent"] [data-testid="baseButton-primary"] {{
            background-color: {active_color};
            color: white;
            margin-top: 5px;
            width: 100%;
            border-radius: 5px;
        }}
        
        /* Input fields and buttons */
        button, input, textarea, select, .stTextInput > div, .stTextInput input,
        div.stTextArea textarea, div.stFileUploader,
        .stSelectbox > div, button[data-testid="baseButton-secondary"] {{
            background-color: {input_bg};
            color: {text_color};
            border-color: {border_color};
        }}
        
        /* Chat input field */
        div[data-testid="stChatInput"], .stChatInputContainer, div.stChatInput {{
            background-color: {input_bg};
            color: {text_color};
            border-color: {border_color};
        }}
        
        /* Chat messages */
        div[data-testid="stChatMessage"], section[data-testid="stChatContainer"] {{
            background-color: {card_bg};
            color: {text_color};
        }}
        
        /* Submit button and other action buttons */
        button[kind="primary"], button[data-testid="chat-input-submit-button"],
        div[data-testid="stChatInput"] button {{
            background-color: {active_color};
            color: #FFFFFF;
        }}
        
        /* File uploader container */
        div.stFileUploader {{
            background-color: {upload_bg};
            border: 2px dashed {border_color};
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}

        /* The file uploader dropzone */
        div.stUploadDropzone {{
            background-color: #FFFFFF;
            border-radius: 5px;
            padding: 20px;
            text-align: center;
        }}
        
        /* "Drag and drop files here" text */
        div.stUploadDropzone p:first-of-type {{
            color: {upload_text};
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        
        /* The "or" text */
        div.stUploadDropzone p {{
            color: {upload_limit_text};
            margin: 5px 0;
        }}
        
        /* File limit text */
        div.stUploadDropzone p:last-of-type {{
            color: {upload_limit_text};
            font-size: 14px;
            margin-top: 8px;
        }}
        
        /* Make sure all text in upload area is visible */
        div.stUploadDropzone p, 
        div.stUploadDropzone small,
        div.stUploadDropzone span,
        div.stUploadDropzone div {{
            color: {upload_limit_text};
        }}
        
        /* The upload icon */
        div.stUploadDropzone svg {{
            fill: {upload_text};
            width: 40px;
            height: 40px;
            margin-bottom: 10px;
        }}
        
        /* Browse files button */
        div.stFileUploader button,
        div.stUploadDropzone button {{
            background-color: {active_color};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            margin-top: 10px;
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        
        div.stFileUploader button:hover,
        div.stUploadDropzone button:hover {{
            opacity: 0.9;
        }}
        
        /* Uploaded file info */
        div.uploadedFileInfo {{
            background-color: {card_bg};
            color: {text_color};
            border-color: {border_color};
            border-radius: 5px;
            padding: 10px;
            margin-top: 10px;
        }}
        
        /* Links and color accents */
        a, span[data-baseweb="tag"], div[role="radiogroup"] div[aria-checked="true"],
        label[data-baseweb="checkbox"] div[data-testid="stTickedContent"] {{
            color: {active_color};
        }}
        
        /* Tabs and accordions */
        button[role="tab"] {{
            color: {text_color};
            background-color: transparent;
        }}
        
        /* All other white elements that might appear */
        .stAlert, .stInfoBox, div[data-testid="stExpander"], div[data-testid="stNotification"] {{
            background-color: {card_bg};
            color: {text_color};
            border-color: {border_color};
        }}
        
        /* Login/signup area */
        div[data-testid="stExpander"] {{
            background-color: {card_bg};
        }}
        
        /* Chat area */
        div[data-testid="stChatMessageContent"] {{
            background-color: {bg_color};
        }}
        
        /* Password visibility icons */
        div.stPasswordInput {{
            position: relative;
        }}
        
        div.stPasswordInput span {{
            color: {text_color};
        }}
        
        /* Move password visibility icon to better position */
        div.stPasswordInput button {{
            position: absolute;
            right: 5px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 10;
            background: transparent;
            border: none;
        }}
        
        /* Navigation buttons and menus */
        [data-testid="stFormSubmitButton"] button, 
        button.css-15cjy8h {{
            background-color: {active_color};
            color: #FFFFFF;
            border-color: {active_color};
        }}
        
        /* Fix progress bar */
        div.stProgress {{
            background-color: rgba(0,0,0,0.05);
            border-radius: 8px;
            height: 0.5rem;
            margin: 0.5rem 0;
        }}
        
        div.stProgress div.stProgressIndicator {{
            background-color: {active_color};
        }}
        
        /* Force all streamlit containers to use background color */
        div[data-testid="stVerticalBlock"], section.main > div {{
            background-color: {bg_color};
        }}
    </style>
    """
    
    # Apply the main CSS
    st.markdown(main_css, unsafe_allow_html=True)