# CXR Report Generator

## Overview

CXR-agno-public is an AI-powered application designed to assist medical professionals in generating and analyzing chest X-ray (CXR) reports. The application leverages two AI Agents(reader and anchor) to automate initial report generation while providing an interactive human-in-the-loop refinement process through a Q&A session.

## Features
- **Patient Selection**: Browse and select patient records with associated chest X-ray images
- **AI-Generated Reports**: Automatically generate initial CXR reports based on image analysis
- **Interactive Q&A Session**: Engage in a question-and-answer session to refine and enhance the generated reports
- **PDF Export**: Export finalized reports to PDF format for documentation and sharing
- **User-Friendly Interface**: Clean Streamlit interface for easy navigation and interaction

## Project Structure

```
CXR-agno-public/
├── app.py                  # Main entry point for the Streamlit application
├── agent.py                # AI agent implementation for report generation and QA
├── cxr_workflow.py         # Create a workflow to organize reader and qa_anchor agents
├── loop.py                 # Main application loop and control flow
├── data.py                 # Data handling and patient record management
├── pdf_export.py           # PDF generation and export functionality
├── requirements.txt        # Project dependencies
└── images/                 # Directory containing chest X-ray images
```

## Requirements

- agno==1.2.4
- fpdf==1.7.2
- streamlit==1.42.1
- openai==1.68.2

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/SabaPivot/CXR-agno-public.git
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the Streamlit application:
   ```
   streamlit run app.py
   ```

2. Use the sidebar to select a patient and their associated chest X-ray images.

3. Click "Load Selected Images" to load the images and generate the initial report.

4. Engage in the interactive Q&A session to refine the report. The agent will update the report in real-time based on your questions.

5. Type "stop" to end the Q&A session and generate the final report.

6. Edit the structured report sections (findings, impressions, plan, etc.) as needed.

7. Export the report to PDF in markdown format.

8. The report remains available on the web UI until you restart the session.

## Application Flow

1. **Patient Selection**: The application loads predefined patient data with associated chest X-ray images.

2. **Report Generation**: The Reader Agent analyzes the selected images and generates an initial report.

3. **Interactive Refinement**: The QA Anchor facilitates an interactive session where users can ask questions about the findings, with the report being updated in real-time.

4. **Session Termination**: User types "stop" to end the Q&A session and generate the final report.

5. **Report Editing**: User can edit the structured report sections.

6. **PDF Export**: The finalized report can be exported to PDF format in markdown.

7. **Session Persistence**: The report remains available on the web UI until the session is restarted.

## Deployment

This application is designed to be deployed on Streamlit Community Cloud:

1. Ensure all files are committed to a GitHub repository.
2. Connect your repository to Streamlit Community Cloud.
3. Select the `app.py` file as the entry point.
4. The application uses relative paths for image loading, ensuring compatibility across different environments.

## Technical Details
- The application uses `pathlib` for cross-platform path handling (Required by streamlit)
- The application is powered by [Agno]("https://github.com/agno-agi/agno"), an AI agent framework.
    - `Workflow` implemented by Agno, empower the developer to orchestrate various agents spontaneously.
- The application implements two main AI components:
  - Reader Agent: Generates the initial CXR report (one-time analysis)
  - QA Anchor: Facilitates the interactive Q&A session (multiple interactions)

