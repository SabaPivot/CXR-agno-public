"""
Reader Agent와 Anchor Agent로 구성된 Workflow를 작성한 script입니다.
CXR 이미지를 분석하고, 보고서를 생성하고, 사용자와 상호작용하는 기능을 제공합니다.
"""

from agno.agent import Agent, RunResponse
from agno.workflow import Workflow
from agno.media import Image
from agno.utils.log import logger
import re
from textwrap import dedent
from agent import create_reader, create_qa_anchor
import streamlit as st


class CXR_Report_Generator(Workflow):
    """
    Advanced workflow for generating CXR Analysis and Report with integrated human-in-the-loop Q&A.

    This workflow leverages multiple AI models to process Chest X-ray (CXR) images and generate comprehensive medical reports.
    After the initial diagnostic report is produced, a human-in-the-loop Q&A session is initiated, allowing the Q_A_agent
    to interactively address user questions. This interactive session continues until the user explicitly signals to "STOP."
    Upon completion of the Q&A, the report is automatically updated to incorporate the additional clinical insights and
    clarifications provided during the session, ensuring that the final output is both accurate and tailored to user needs.
    """

    description: str = dedent(
        """\
An advanced AI-powered workflow designed for generating comprehensive Chest X-ray (CXR) analysis and detailed medical reports.
This system integrates multiple AI models to process radiological images, extract clinical insights, and produce structured diagnostic summaries.
It enhances radiological assessments by leveraging deep learning for abnormality detection and severity classification.
The workflow ensures medical accuracy by incorporating automated findings explanations, medical terminology standardization,
and integration with clinical guidelines.
Furthermore, it features a human-in-the-loop Q&A session immediately following the initial report generation, 
where the Q_A_agent engages with the user to address any questions or clarifications until a "STOP" command is issued.
The final report is subsequently updated with the gathered insights, ensuring that all relevant clinical details are thoroughly addressed.
"""
    )

    def __init__(self):
        super().__init__()

        self.reader = create_reader()
        self.qa_anchor = create_qa_anchor()

    def generate_cxr_report(self, image: Image) -> RunResponse:
        """Generate a CXR report using the reader_anchor."""
        try:
            # Actual agent run
            ATTEMPTS = 15
            ban_words = ("sorry", "certainly", "AI")
            for attempt in range(ATTEMPTS):
                logger.info(f"Attempt {attempt+1}/{ATTEMPTS}")
                reader_ans: RunResponse = self.reader.run(images=[image])
                # Ensure the report is detailed and free of undesired language.
                if len(reader_ans.content) < 500 or any(
                    word in reader_ans.content.strip().lower() for word in ban_words
                ):
                    continue
                break

            return reader_ans

        except Exception as e:
            # Return an error message as the response
            return RunResponse(content=f"Error generating report: {str(e)}")

    def run_qa_session(self, image_id: str = "default") -> RunResponse:
        """
        Run an interactive Q&A session with the user about the chest X-ray report.
        The session continues until the user types 'stop'.

        Args:
            image_id: A unique identifier for this Q&A session

        Returns:
            RunResponse: The final response after completing the Q&A session
        """
        # Setup key names for session state
        chat_history_key = f"chat_history_{image_id}"
        qa_complete_key = f"qa_complete_{image_id}"
        final_report_key = f"final_report_{image_id}"
        current_report_key = (
            f"current_report_{image_id}"  # Key to track the evolving report
        )
        pending_msg_key = f"pending_msg_{image_id}"  # Key for pending assistant message

        # Initialize chat history if not already present
        if chat_history_key not in st.session_state:
            st.session_state[chat_history_key] = []

        # If Q&A session is already complete, just return the final report
        if (
            st.session_state.get(qa_complete_key, False)
            and final_report_key in st.session_state
        ):
            return st.session_state[final_report_key]

        # Show the current evolving report at the top
        if current_report_key in st.session_state:
            with st.expander("Report Detail", expanded=True):
                st.markdown(st.session_state[current_report_key])

        # Display the chat history
        for i, (sender, message) in enumerate(st.session_state[chat_history_key]):
            # Skip the first assistant message since it duplicates the report
            if i == 0 and sender == "assistant":
                continue

            with st.chat_message(sender):
                st.markdown(message)

        # Check if there's a pending message to display
        if pending_msg_key in st.session_state:
            with st.chat_message("assistant"):
                st.markdown(st.session_state[pending_msg_key])
            # Clear the pending message
            del st.session_state[pending_msg_key]

        # Get user input for the Q&A session
        st.info(
            "Ask questions about the report or type 'stop' to finish and move to the next image."
        )
        user_input = st.chat_input("Your question:")

        # Process user input
        if user_input:
            # Add user input to chat history
            st.session_state[chat_history_key].append(("user", user_input))

            # Check if user wants to stop
            if user_input.lower().strip() in ["stop", "quit", "exit", "finish", "end"]:
                # Generate final summary based on Q&A session
                with st.spinner("Generating final report based on Q&A session..."):

                    try:
                        # Get the latest report to provide context
                        latest_report = st.session_state.get(current_report_key, "")

                        # Get all chat messages for complete context
                        chat_context = "\n".join(
                            [
                                f"{sender}: {message}"
                                for sender, message in st.session_state[
                                    chat_history_key
                                ]
                            ]
                        )

                        # Create a final prompt that includes the latest report and all Q&A interactions
                        final_prompt = f"""
                        Current Report:
                        {latest_report}
                        
                        Complete Q&A Session:
                        {chat_context}
                        
                        User has requested to finalize the report. Please provide the final comprehensive CXR report
                        that incorporates all the information from our Q&A session. Maintain the existing report structure
                        and ensure all relevant details are included.
                        """

                        # Generate the final report
                        final_response = self.qa_anchor.run(final_prompt)

                        # Ensure we have valid content before proceeding
                        if (
                            hasattr(final_response, "content")
                            and final_response.content
                        ):
                            final_content = final_response.content
                        else:
                            final_content = str(final_response)

                        # Store the final report
                        st.session_state[final_report_key] = final_response
                        # Update the current report too
                        st.session_state[current_report_key] = final_content
                        # Mark Q&A as complete
                        st.session_state[qa_complete_key] = True

                        # Add the final response to chat history
                        st.session_state[chat_history_key].append(
                            (
                                "assistant",
                                "Q&A session complete. Final report generated.",
                            )
                        )

                        # Show success message
                        st.success("Q&A session complete. You can now edit the report.")

                        # Force rerun to update UI and show the "Proceed to Edit" button in loop.py
                        st.rerun()

                    except Exception as e:
                        error_msg = f"Error generating final report: {str(e)}"
                        st.error(error_msg)

                        # Add error to chat history
                        st.session_state[chat_history_key].append(
                            (
                                "assistant",
                                f"⚠️ {error_msg} Please try again or contact support.",
                            )
                        )

                        # Ensure we have a reasonable fallback report
                        if current_report_key in st.session_state:
                            # Use the most recent updated report as the final report
                            st.session_state[final_report_key] = RunResponse(
                                content=st.session_state[current_report_key]
                            )
                            st.session_state[qa_complete_key] = True
                        else:
                            return RunResponse(content=f"Error: {str(e)}")
            else:
                # Normal Q&A interaction
                with st.spinner("Generating response..."):
                    try:
                        # Get the latest report to provide context
                        latest_report = st.session_state.get(current_report_key, "")

                        # 1. Get direct response to the user's question, with the latest report as context
                        question_with_context = dedent(
                            f"""\
                        Current Report:
                        {latest_report}
                        
                        User Question: {user_input}
                        
                        Please answer the user's question directly based on the report above."""
                        )

                        response = self.qa_anchor.run(question_with_context)

                        # Ensure we have valid content
                        if hasattr(response, "content") and response.content:
                            response_content = response.content
                        else:
                            response_content = str(response)

                        # Check if response has report format
                        # Look for standard report sections
                        report_sections = [
                            "Patient Information:",
                            "Findings:",
                            "Impression:",
                            "Plan:",
                        ]
                        is_report_format = any(
                            section in response_content for section in report_sections
                        )

                        # If it's a report format, get only the last sentence
                        if is_report_format:
                            # Split by periods and get the last non-empty sentence
                            sentences = [
                                s.strip()
                                for s in response_content.split(".")
                                if s.strip()
                            ]
                            if sentences:
                                chat_display_content = sentences[
                                    -1
                                ]  # Do you have further questions?
                            else:
                                chat_display_content = "I've updated the report."
                        else:
                            # Use the full content if not a report
                            chat_display_content = response_content

                        # Store the full response as a pending message to display in chat
                        st.session_state[pending_msg_key] = chat_display_content

                        # Add to chat history - only the last sentence if it's a report
                        st.session_state[chat_history_key].append(
                            ("assistant", chat_display_content)
                        )

                        # 2. Generate an updated comprehensive report that incorporates this QA interaction
                        with st.spinner("Updating the report with this information..."):
                            # Get all chat messages since the last report update
                            chat_context = "\n".join(
                                [
                                    f"{sender}: {message}"
                                    for sender, message in st.session_state[
                                        chat_history_key
                                    ]
                                ]
                            )

                            # Provide the QA anchor with the latest report and the recent chat messages
                            update_prompt = dedent(
                                f"""\
                            Current Report:
                            {latest_report}
                            
                            Recent Q&A Session:
                            {chat_context}
                            
                            Please update the report based on the information from the Q&A session above.
                            IF NOTHING SPECIAL TO UPDATE, JUST PRINT THE INPUT REPORT.
                            Incorporate any relevant new information while maintaining the report structure.
                            """
                            )

                            updated_report_response = self.qa_anchor.run(update_prompt)

                            # Store the updated report
                            st.session_state[
                                current_report_key
                            ] = updated_report_response.content

                        # Force UI refresh to update both chat and report
                        st.rerun()
                    except Exception as e:
                        error_msg = f"Error generating response: {str(e)}"
                        st.error(error_msg)

                        # Add error to chat history, but format it as assistant message
                        error_response = f"⚠️ I encountered an error while processing your question: {str(e)}. Please try again or rephrase your question."
                        st.session_state[chat_history_key].append(
                            ("assistant", error_response)
                        )

                        # If we have a pending message key, clear it to avoid confusion
                        if pending_msg_key in st.session_state:
                            del st.session_state[pending_msg_key]

                        # Don't update the report if we had an error in the response
                        st.rerun()

        # Return appropriate response based on state
        if final_report_key in st.session_state:
            return st.session_state[final_report_key]
        elif len(st.session_state[chat_history_key]) > 0:
            return RunResponse(
                content=st.session_state[chat_history_key][-1][1]
                if st.session_state[chat_history_key][-1][0] == "assistant"
                else "Waiting for response..."
            )
        else:
            return RunResponse(
                content=f"Q&A session for image {image_id} in progress. Ask questions about the report."
            )

    def run(self, query: str, image: Image, image_id: str = None) -> RunResponse:
        """
        Modularized run method that:
        1. Generates a CXR report.
        2. Starts an interactive Q&A session with the generated report.

        Args:
            query: Query information for the report
            image: The chest X-ray image to analyze
            image_id: A unique identifier for the image/report (defaults to image filename)
        """

        # Reset the chat history for this image_id - important to clear between runs
        chat_history_key = f"chat_history_{image_id}"
        qa_complete_key = f"qa_complete_{image_id}"

        # Check if we already have a report generated for this image_id
        report_key = f"report_{image_id}"
        qa_anchor_key = f"qa_anchor_{image_id}"

        # Initialize session state variables if this is a new image or we're reprocessing
        should_initialize = (
            st.session_state.get("current_image_index", 0)
            == len(st.session_state.get("all_reports", []))
            or qa_complete_key not in st.session_state
            or not st.session_state.get(qa_complete_key, False)
        )

        if should_initialize:
            # Clear existing chat history to start fresh
            if chat_history_key in st.session_state:
                del st.session_state[chat_history_key]
            st.session_state[chat_history_key] = []

            # Reset Q&A completion flag
            st.session_state[qa_complete_key] = False

        # Step 1: Generate the CXR report or retrieve from session state if already generated
        if report_key not in st.session_state:
            with st.spinner(f"Generating CXR report for Image {image_id}..."):
                reader_ans = self.generate_cxr_report(image)
                # Store report in session state to avoid regenerating it
                st.session_state[report_key] = reader_ans

                # Create a QA anchor - this is a separate agent for each image
                initial_context = f"""
                Please generate a properly formatted CXR report based on the following information:

                Patient Information:
                {query}

                CXR Analysis:
                {reader_ans.content}

                Format the report with clear sections in this exact order:
                1. Patient Information (including ID, follow-up, age, gender, view position, and possible diseases)
                2. Findings (including airways, bones and soft tissues, cardiac silhouette and mediastinum, diaphragm and pleural spaces, and lungs)
                3. Impression (key findings and clinical implications)
                4. Plan (recommended next steps)
                """

                # Store it in the session state
                initial_response = self.qa_anchor.run(initial_context)

                # Ensure we have valid content
                if hasattr(initial_response, "content") and initial_response.content:
                    initial_content = initial_response.content
                else:
                    initial_content = str(initial_response)

                st.session_state[qa_anchor_key] = initial_response
                st.session_state[f"current_report_{image_id}"] = initial_content

                # Add initial message to chat history
                if (
                    chat_history_key not in st.session_state
                    or not st.session_state[chat_history_key]
                ):
                    initial_response = st.session_state[qa_anchor_key]
                    st.session_state[chat_history_key] = [
                        ("assistant", initial_response.content)
                    ]
        else:
            # Retrieve existing report from session state
            reader_ans = st.session_state[report_key]
            st.success(f"Retrieved existing report for Image {image_id}")

        # Combine the original query with the generated report as context for the Q&A session.
        initial_context = query + reader_ans.content

        # Step 2: Start the Q&A session and return its final response.
        final_q_a = self.run_qa_session(image_id)
        return final_q_a


def parse_report(report_content: str) -> dict:
    """
    Parse the report into the standard four sections.

    Args:
        report_content: The content of the report

    Returns:
        dict: A dictionary with section names as keys and their corresponding content as values
    """
    # The four standard sections
    sections = ["Patient Information", "Findings", "Impression", "Plan"]
    parsed_report = {}

    # Extract each section using the standard markdown format
    for i, section in enumerate(sections):
        # Find the section header
        pattern = f"\\*\\*{section}:\\*\\*"
        match = re.search(pattern, report_content)

        if match:
            # Get the start position (after the header)
            start_idx = match.end()

            # Find the end - either the next section or the end of the content
            if i < len(sections) - 1:
                end_pattern = f"\\*\\*{sections[i+1]}:\\*\\*"
                end_match = re.search(end_pattern, report_content[start_idx:])

                if end_match:
                    end_idx = start_idx + end_match.start()
                else:
                    end_idx = len(report_content)
            else:
                # Last section goes to the end
                end_idx = len(report_content)

            # Extract and clean the content
            content = report_content[start_idx:end_idx].strip()
            parsed_report[section] = content
        else:
            # If section not found, provide an empty string
            parsed_report[section] = ""

    return parsed_report
