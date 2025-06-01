"""
study_notes_generator.py - Generate structured study notes from conversations
"""
import streamlit as st
from datetime import datetime
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import markdown2

def extract_study_content(messages):
    """Extract educational content from conversation messages"""
    study_content = []
    
    for i, message in enumerate(messages):
        if message['role'] == 'user':
            # Find questions/topics the user asked about
            question = message['content']
            
            # Look for the assistant's response
            if i + 1 < len(messages) and messages[i + 1]['role'] == 'assistant':
                answer = messages[i + 1]['content']
                
                # Skip system messages and greetings
                if not any(greeting in answer.lower() for greeting in ['hello', 'how can i help', 'welcome']):
                    study_content.append({
                        'question': question,
                        'answer': answer
                    })
    
    return study_content

def generate_study_notes(study_content, llm, document_name=None):
    """Generate structured study notes using the LLM"""
    if not study_content or not llm:
        return "No study content available to generate notes."
    
    # Prepare the content for analysis
    content_text = ""
    for item in study_content:
        content_text += f"Q: {item['question']}\nA: {item['answer']}\n\n"
    
    # Create prompt for study notes generation
    prompt = f"""Based on the following educational conversation, create comprehensive study notes in a clear, organized format.

CONVERSATION CONTENT:
{content_text}

Please create study notes that include:

1. **MAIN TOPICS COVERED**
   - List the key subjects/topics discussed

2. **KEY CONCEPTS & DEFINITIONS**
   - Important terms and their definitions
   - Core concepts explained

3. **IMPORTANT FACTS & INFORMATION**
   - Key facts, formulas, or data points
   - Important details to remember

4. **EXAMPLES & APPLICATIONS**
   - Any examples provided in the conversation
   - Practical applications mentioned

5. **SUMMARY POINTS**
   - Main takeaways from the conversation
   - Critical points to remember for studying

Format the notes using clear headings, bullet points, and organized sections. Make them suitable for studying and review.
Keep the language clear and educational. Focus on the most important information that a student should remember.

If there are any prerequisite concepts mentioned, include them in a separate "Prerequisites" section."""

    try:
        # Generate notes using the LLM
        response = llm.invoke(prompt)
        notes = response.content
        
        # Add header with metadata
        header = f"""# Study Notes
**Generated on:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
"""
        if document_name:
            header += f"**Source Document:** {document_name}\n"
        
        header += f"**Total Q&A Pairs Analyzed:** {len(study_content)}\n\n---\n\n"
        
        return header + notes
        
    except Exception as e:
        return f"Error generating study notes: {str(e)}"

def create_downloadable_notes(notes_content, filename_prefix="study_notes"):
    """Create a downloadable PDF file for the study notes"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Ensure filename_prefix is not None and clean it
    if not filename_prefix:
        filename_prefix = "study_notes"
    elif filename_prefix.endswith('.pdf'):
        filename_prefix = filename_prefix.replace('.pdf', '')
    
    filename = f"{filename_prefix}_{timestamp}.pdf"
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=HexColor('#2E86C1')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=HexColor('#1B4F72')
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12,
        textColor=HexColor('#2874A6')
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        alignment=0  # Left alignment
    )
    
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=10
    )
    
    # Build PDF content
    story = []
    
    # Parse the markdown-like content and convert to PDF elements
    lines = notes_content.split('\n')
    
    def clean_text(text):
        """Clean text to remove problematic characters and formatting"""
        # Remove or replace problematic characters
        text = text.replace('**', '')  # Remove markdown bold
        text = text.replace('*', '')   # Remove markdown italic
        text = text.replace('<', '&lt;')  # Escape HTML
        text = text.replace('>', '&gt;')  # Escape HTML
        text = text.replace('&', '&amp;')  # Escape ampersand
        # Remove any remaining HTML tags
        import re
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()
    
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        
        try:
            # Main title (# Study Notes)
            if line.startswith('# '):
                title_text = clean_text(line[2:])
                story.append(Paragraph(title_text, title_style))
                story.append(Spacer(1, 12))
                
            # Level 2 headings (## or **)
            elif line.startswith('## ') or (line.startswith('**') and line.endswith('**')):
                if line.startswith('## '):
                    heading_text = clean_text(line[3:])
                else:
                    heading_text = clean_text(line)
                story.append(Paragraph(heading_text, heading_style))
                
            # Level 3 headings (###)
            elif line.startswith('### '):
                subheading_text = clean_text(line[4:])
                story.append(Paragraph(subheading_text, subheading_style))
                
            # Bullet points
            elif line.startswith('- ') or line.startswith('• '):
                bullet_text = clean_text(line[2:])
                story.append(Paragraph(f"• {bullet_text}", bullet_style))
                
            # Horizontal rule
            elif line.startswith('---'):
                story.append(Spacer(1, 12))
                # Use a simple line instead of underscores
                from reportlab.platypus import HRFlowable
                story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=HexColor('#CCCCCC')))
                story.append(Spacer(1, 12))
                
            # Regular paragraph
            elif line:
                cleaned_line = clean_text(line)
                if cleaned_line:  # Only add if there's content after cleaning
                    story.append(Paragraph(cleaned_line, body_style))
                    
        except Exception as e:
            # If there's an error with a specific line, skip it and continue
            print(f"Error processing line: {line[:50]}... - {str(e)}")
            continue
    
    try:
        # Build PDF
        doc.build(story)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data, filename
        
    except Exception as e:
        buffer.close()
        print(f"Error building PDF: {str(e)}")
        # Return a simple text-based PDF as fallback
        return create_simple_pdf_fallback(notes_content, filename)

def create_simple_pdf_fallback(notes_content, filename):
    """Create a simple text-only PDF as fallback"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Add title
    story.append(Paragraph("Study Notes", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Add content as simple paragraphs
    lines = notes_content.split('\n')
    for line in lines:
        line = line.strip()
        if line:
            # Clean the line completely
            clean_line = line.replace('**', '').replace('*', '').replace('#', '').replace('-', '').strip()
            if clean_line:
                try:
                    story.append(Paragraph(clean_line, styles['Normal']))
                    story.append(Spacer(1, 6))
                except:
                    # If even this fails, skip the line
                    continue
    
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data, filename

def display_study_notes_generator():
    """Display the study notes generator in the sidebar"""
    if not st.session_state.get('messages') or len(st.session_state.messages) <= 1:
        st.sidebar.info("💡 Have a conversation first to generate study notes!")
        return
    
    # Check if we have educational content (not just greetings)
    study_content = extract_study_content(st.session_state.messages)
    
    if not study_content:
        st.sidebar.info("💡 Ask some questions to generate study notes!")
        return
    
    # Show the study notes generator section
    with st.sidebar.expander("📚 Study Notes Generator", expanded=False):
        # Simple display without technical details
        if len(study_content) == 1:
            st.write(f"📝 **1 question** ready for notes")
        else:
            st.write(f"📝 **{len(study_content)} questions** ready for notes")
        
        if st.session_state.get('processed_file_name'):
            # Show just the document name without extension
            doc_name = st.session_state.processed_file_name
            if doc_name and doc_name.endswith('.pdf'):
                doc_name = doc_name.replace('.pdf', '')
            st.write(f"📄 **From:** {doc_name}")
        
        # Generate notes button
        if st.button("📝 Generate Study Notes", key="generate_notes"):
            if not st.session_state.get('llm'):
                st.error("LLM not available for generating notes.")
                return
            
            with st.spinner("🧠 Creating your study notes..."):
                # Generate the notes
                notes = generate_study_notes(
                    study_content, 
                    st.session_state.llm,
                    st.session_state.get('processed_file_name')
                )
                
                # Store in session state for display
                st.session_state.generated_notes = notes
                
            st.success("✅ Study notes ready!")
            st.rerun()
        
        # Display and download options if notes exist
        if st.session_state.get('generated_notes'):
            st.write("---")
            
            # Download button
            notes_bytes, filename = create_downloadable_notes(
                st.session_state.generated_notes,
                st.session_state.get('processed_file_name', 'study_notes')
            )
            
            st.download_button(
                label="⬇️ Download Notes (.pdf)",
                data=notes_bytes,
                file_name=filename,
                mime="application/pdf",
                key="download_notes"
            )
            
            # Option to view notes in app
            if st.button("👁️ View Notes", key="view_notes"):
                st.session_state.show_notes_modal = True
                st.rerun()

def display_notes_modal():
    """Display the generated notes in a modal-like container"""
    if st.session_state.get('show_notes_modal') and st.session_state.get('generated_notes'):
        # Create a prominent container for the notes
        with st.container():
            st.markdown("---")
            
            # Header with close button
            col1, col2 = st.columns([6, 1])
            with col1:
                st.subheader("📚 Generated Study Notes")
            with col2:
                if st.button("✖️ Close", key="close_notes"):
                    st.session_state.show_notes_modal = False
                    st.rerun()
            
            # Display the notes
            st.markdown(st.session_state.generated_notes)
            
            # Download button at the bottom
            filename_base = st.session_state.get('processed_file_name', 'study_notes')
            if filename_base and filename_base.endswith('.pdf'):
                filename_base = filename_base.replace('.pdf', '')
                
            notes_bytes, filename = create_downloadable_notes(
                st.session_state.generated_notes,
                filename_base
            )
            
            st.download_button(
                label="⬇️ Download These Notes",
                data=notes_bytes,
                file_name=filename,
                mime="application/pdf",
                key="download_notes_modal"
            )
            
            st.markdown("---")

# Initialize session state variables
def init_study_notes_session_state():
    """Initialize session state variables for study notes"""
    if 'generated_notes' not in st.session_state:
        st.session_state.generated_notes = None
    if 'show_notes_modal' not in st.session_state:
        st.session_state.show_notes_modal = False