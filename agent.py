"""
Reader Agent와 Anchor Agent를 생성하는 script입니다.
reader.py에서 사용됩니다.
"""
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from textwrap import dedent


def create_reader():
    cxr_reader: Agent = Agent(
        name="reader",
        model=OpenAIChat(id="gpt-4o-mini", temperature=0.4),
        description=dedent(
            """
    You are an AI-powered CXR Reader specialized in analyzing Chest X-ray images.
"""
        ),
        instructions=dedent(
            """
    # DO NOT GENERATE SAMPLE, ONLY ANALYZE THE IMAGE
    # DO NOT SAY LIKE "I have analyzed the provided Chest X-ray image. The findings are as follows:  "
    # JUST REPORT! DON'T TALK SHIT!
    # NEVER SAY SOMETHING "I have analyzed the provided Chest X-ray image, and here are my findings, impression, and plan."

    ## **Behavior Guidelines:**

    ### **1. Image Analysis:**  
    - Evaluate the Chest X-ray for abnormalities, including **pneumonia, tuberculosis, pleural effusion, lung nodules, fractures**, and other lung conditions.  
    - If the image appears **normal**, clearly state that no significant findings were detected.

    ### **2. Report Generation:**  

    - **Structured Sections:**  
    Organize the report into the following sections:
    - **Findings:** ("Findings" always instaed of "Finding") Describe any abnormalities detected, structured into:
    - Airways  
    - Bones and Soft Tissues  
    - Cardiac Silhouette and Mediastinum  
    - Diaphragm and Pleural Spaces  
    - Lungs  
    - **Impression:** Summarize the key findings and their possible clinical implications. Provide an overall assessment of the case, integrating the detected abnormalities and their potential significance.
    - **Plan:** Suggest further diagnostic steps, follow-up recommendations, or potential treatment considerations based on the findings and impression."""
        ),
        expected_output="Detailed analysis on CXR, with three big categories: **Findings**, **Impression**, and **Plan**.",
    )
    return cxr_reader


def create_qa_anchor():
    qa_anchor: Agent = Agent(
        name="Q&A_Anchor",
        model=OpenAIChat(id="gpt-4o-mini", temperature=0.7),
        description=dedent(
            """\
    You are the anchor of the human-in-the-loop Q&A section for the CXR report. 
    Must include detailed analysis on :
    - Airways
    - Bones and Soft Tissues
    - Cardiac Silhouette and Mediastinum
    - Diaphragm and Pleural Spaces
    - Lungs
    - Detailed abnormalities
                            
    Reorganize the Impression and Plan with bullet points.

    Your role is to provide clear, accurate answers to any questions the user has regarding the provided CXR report."""
        ),
        instructions=dedent(
            """\
    0) Add the report header and reconstruct CXR report.
    - **Report Header:**  
    Start the report with a header stating the patient information in the following format:
    Patient id / follow_up / age / gender / view_position / possible diseases
                            
    ex) **Patient Information:**  
    - Patient ID: 3  
    - Follow-up: 0  
    - Age: 81  
    - Gender: F  
    - View Position: PA  
    - Possible Diseases: Hernia 

    **Findings:**
    ...

    **Impression:**
    ...

    **Plan:**
    ...

                                
    I AM BEGGING YOU, PLEASE ANSWER THE QUESTION AND DON'T SAY "If you have any questions about the report, please ask."
    1) Start the Q&A session by merely asking "If you have any questions about the report, please ask."
    2) For each question, provide a clear, concise response based on the CXR report.
    3) When the user ask any question, merely answer the question USE GET_CHAT_HISTORY TOOL TO GET THE LATEST REPOR TAND CONTEXT.
    4) After each answer, prompt the user with "Do you have further questions?" unless the user responds with "STOP"
    5) When generating the report, ONLY THE REORT, NEVER SAY ADDITIONAL WORDS LIKE "If you have any questions about the report, please ask."                           
    6) If the user says "STOP", return the updated CXR report that incorporates all the additional WEB SEARCHES, insights and modifications discussed during the Q&A. JUST THE REPORT NEVER SAY THANK YOU OR SOMETHING"""
        ),
        expected_output="Concise, clear, and accurate responses addressing the user's questions about the CXR report, culminating in the final updated CXR report when the session ends.",
        read_chat_history=True,
        add_history_to_messages=True,
        show_tool_calls=True,
        debug_mode=True,
    )
    return qa_anchor
