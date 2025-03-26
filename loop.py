"""
Streamlit의 workflow를 구현한 스크립트입니다.
st.session_state를 사용하여 각 process의 상태를 관리합니다.

기본 상태 추적 키:
current_image_index: 현재 처리 중인 이미지의 인덱스
reports_generated: "Generate Reports" 버튼이 클릭되었는지 여부
all_reports_complete: 모든 보고서 생성이 완료되었는지 여부
all_reports: 생성된 모든 보고서를 저장하는 리스트
processing_complete: 현재 이미지에 대한 처리가 완료되었는지 여부
records: 처리 중인 환자 기록 데이터

이미지별 동적 키 (image_id 기반):
qa_complete_{image_id}: 특정 이미지의 Q&A 세션이 완료되었는지 여부
final_report_{image_id}: 특정 이미지의 최종 보고서
chat_history_{image_id}: 특정 이미지의 Q&A 세션 채팅 기록
report_{image_id}: 특정 이미지의 초기 보고서
qa_anchor_{image_id}: 특정 이미지의 QA 앵커
current_report_{image_id}: Q&A 세션 중 업데이트되는 보고서 내용
"""

from agno.media import Image
from textwrap import dedent
import streamlit as st
import uuid
from datetime import datetime
from reader import CXR_Report_Generator, parse_report
from data import path_finder
from pdf_export import generate_pdf


def save_report(report_content, patient_id="Unknown", follow_up=""):
    """Save the report to reports collection. Deduplicate if the same patient ID and follow-up exists."""
    new_report = {
        "id": str(uuid.uuid4()),
        "content": report_content,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "patient_id": patient_id,
        "follow_up": follow_up,
    }

    # Check if we already have a report with the same patient ID and follow-up
    if "all_reports" in st.session_state:
        existing_indices = []
        for i, report in enumerate(st.session_state["all_reports"]):
            if (
                report.get("patient_id") == patient_id
                and report.get("follow_up") == follow_up
                and patient_id != "Unknown"
            ):  # Only deduplicate if patient ID is known
                existing_indices.append(i)

        # Remove any duplicate reports (from newest to oldest to maintain index validity)
        for idx in sorted(existing_indices, reverse=True):
            st.session_state["all_reports"].pop(idx)

    # Initialize all_reports if it doesn't exist
    if "all_reports" not in st.session_state:
        st.session_state["all_reports"] = []

    # Add the new report
    st.session_state["all_reports"].append(new_report)
    return new_report


def main():
    st.title("CXR Report Generator")
    st.write("This application generates medical reports from chest X-ray images.")

    # Add debug info at the top of the application
    st.sidebar.subheader("Debug Information")
    debug_expander = st.sidebar.expander("Session State", expanded=False)
    with debug_expander:
        st.write("Current Image Index:", st.session_state.get("current_image_index", 0))
        st.write(
            "Processing Complete:", st.session_state.get("processing_complete", False)
        )
        st.write(
            "All Reports Complete:", st.session_state.get("all_reports_complete", False)
        )
        st.write("Number of Reports:", len(st.session_state.get("all_reports", [])))
        if st.button("Clear All Session State", key="clear_all"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("All session state cleared!")
            st.rerun()

    # Initialize session state for tracking progress
    if "current_image_index" not in st.session_state:
        st.session_state.current_image_index = 0
        st.session_state.reports_generated = False
        st.session_state.all_reports_complete = False
        st.session_state.all_reports = []
        st.session_state.processing_complete = False

    # Check if we've moved to a new image index but haven't reset processing_complete
    if (
        st.session_state.get("current_image_index", 0) > 0
        and len(st.session_state.get("all_reports", []))
        < st.session_state.current_image_index
    ):
        st.session_state.processing_complete = False

    # Add a reset button to restart processing if needed
    cols = st.columns([3, 1])
    with cols[1]:
        if st.button("Reset Processing"):
            for key in list(st.session_state.keys()):
                if (
                    key.startswith("qa_complete_")
                    or key.startswith("final_report_")
                    or key.startswith("chat_history_")
                ):
                    del st.session_state[key]
            st.session_state.current_image_index = 0
            st.session_state.reports_generated = False
            st.session_state.all_reports_complete = False
            st.session_state.all_reports = []
            st.session_state.processing_complete = False
            st.success("Processing reset. You can start again.")
            st.rerun()

    # Get records from patient_data module
    with st.spinner("Loading patient records..."):
        records = path_finder()

    if not records:
        st.warning("No records found. Please select patient records first.")
        return

    st.success(f"Loaded {len(records)} patient record(s)")

    # Check if the number of records has changed since last run
    if "records" in st.session_state and len(st.session_state.records) != len(records):
        # Reset processing state for a new set of records
        st.session_state.current_image_index = 0
        st.session_state.reports_generated = False
        st.session_state.all_reports_complete = False
        st.session_state.processing_complete = False

    # Initialize the report generator
    generator = CXR_Report_Generator()

    # Display selected images
    st.subheader("Selected Images")
    image_cols = st.columns(min(3, len(records)))

    for i, record in enumerate(records):
        with image_cols[i % min(3, len(records))]:
            st.image(
                record[0], caption=f"Follow-up: {record[2]}", use_container_width=True
            )

    # Store records in session state for access during processing
    st.session_state.records = records

    # Generate reports button
    if st.button("Generate Reports") or st.session_state.reports_generated:
        # If we're just starting with Generate Reports, ensure all processing flags are reset
        if not st.session_state.reports_generated:
            st.session_state.current_image_index = 0
            st.session_state.all_reports_complete = False
            st.session_state.processing_complete = False

        st.session_state.reports_generated = True

        # Process each image/record sequentially
        if st.session_state.current_image_index < len(st.session_state.records):
            current_record = st.session_state.records[
                st.session_state.current_image_index
            ]

            # Create a unique image_id
            image_id = f"img_{st.session_state.current_image_index}_{current_record[3]}"

            st.subheader(
                f"Processing image {st.session_state.current_image_index + 1}/{len(st.session_state.records)}"
            )

            # Load image and prepare query
            image = Image(filepath=current_record[0])
            query = dedent(
                f"""
            possible disease: {current_record[1]}
            follow-up: {current_record[2]}
            patient id: {current_record[3]}
            patient age: {current_record[4]}
            patient gender: {current_record[5]}
            view position: {current_record[6]}
            """
            )

            # Check if this Q&A session is complete
            qa_complete_key = f"qa_complete_{image_id}"

            # If the current Q&A session is complete, move to the next record
            if st.session_state.get(qa_complete_key, False):
                # Show a clear message that we're finished with this image
                st.success(
                    f"Report for image {st.session_state.current_image_index + 1}/{len(st.session_state.records)} completed."
                )

                # Retrieve the final report and parse it
                final_report_key = f"final_report_{image_id}"
                if final_report_key in st.session_state:
                    report_content = st.session_state[final_report_key].content
                    parsed_report = parse_report(report_content)

                    # Extract patient info from record
                    patient_id = (
                        current_record[3] if len(current_record) > 3 else "Unknown"
                    )
                    follow_up = current_record[2] if len(current_record) > 2 else ""

                    # Display editable report
                    for key in parsed_report:
                        edited_value = st.text_area(
                            f"Edit {key}",
                            parsed_report[key],
                            height=150,
                            key=f"edit_{key}_{image_id}",
                        )
                        parsed_report[key] = edited_value

                    # Combine all edited sections back into a single report
                    final_report_content = "\n\n".join(
                        [f"{key}\n{value}" for key, value in parsed_report.items()]
                    )

                    # Save the report with deduplication if same patient_id and follow_up
                    save_report(
                        final_report_content, patient_id=patient_id, follow_up=follow_up
                    )

                    # Add "Download as PDF" option for the edited report
                    edited_report = {
                        "content": final_report_content,
                        "patient_id": patient_id,
                        "follow_up": follow_up,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    pdf_bytes = generate_pdf(
                        edited_report, patient_record=current_record
                    )
                    if pdf_bytes is not None:
                        st.download_button(
                            label="Download Edited Report as PDF",
                            data=pdf_bytes,
                            file_name=f"report_{patient_id}_{follow_up}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{image_id}",
                        )

                # Display a prominent button to move to the next image
                if st.button(
                    "Process Next Image",
                    key=f"next_img_{image_id}",
                    use_container_width=True,
                ):
                    # Move to the next image
                    current_index = st.session_state.current_image_index
                    st.session_state.current_image_index += 1
                    st.session_state.processing_complete = False

                    # Log for debugging
                    st.info(
                        f"Moving from image {current_index+1} to image {st.session_state.current_image_index+1} of {len(st.session_state.records)} total images"
                    )

                    # If this was the last image, mark all processing as complete
                    if st.session_state.current_image_index >= len(
                        st.session_state.records
                    ):
                        st.session_state.all_reports_complete = True
                        st.write(
                            f"All {len(st.session_state.records)} images have been processed."
                        )

                    # Clear QA complete flag for the next image to ensure it's processed correctly
                    if st.session_state.current_image_index < len(
                        st.session_state.records
                    ):
                        next_record = st.session_state.records[
                            st.session_state.current_image_index
                        ]
                        next_image_id = f"img_{st.session_state.current_image_index}_{next_record[3]}"
                        qa_complete_next_key = f"qa_complete_{next_image_id}"
                        if qa_complete_next_key in st.session_state:
                            del st.session_state[qa_complete_next_key]

                        # Also clear report keys for the next image to ensure fresh processing
                        report_key_next = f"report_{next_image_id}"
                        if report_key_next in st.session_state:
                            del st.session_state[report_key_next]

                        # Clear other related keys for the next image
                        keys_to_clear = [
                            f"qa_anchor_{next_image_id}",
                            f"current_report_{next_image_id}",
                            f"final_report_{next_image_id}",
                        ]
                        for key in keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]

                    # Force a complete rerun to refresh the UI
                    st.rerun()

                # If we get here and there's a valid report, but we haven't moved to next image yet,
                # we're waiting for user to click the "Process Next Image" button
                return
            else:
                # Only process the image if we haven't already started processing it
                if not st.session_state.get(
                    "processing_complete", False
                ) or st.session_state.current_image_index > len(
                    st.session_state.get("all_reports", [])
                ):
                    # Generate the report and start Q&A session
                    with st.spinner(
                        f"Generating report for patient ID {current_record[3]}..."
                    ):
                        generator.run(query=query, image=image, image_id=image_id)
                        st.session_state.processing_complete = False

        # After all reports are processed, show the editing interface
        elif st.session_state.all_reports_complete:
            st.subheader("All Reports Generated")

            # Display and allow viewing of all reports
            for i, report_data in enumerate(st.session_state["all_reports"]):
                with st.expander(
                    f"Report {i+1} - Patient ID: {report_data['patient_id']}, Follow-up: {report_data.get('follow_up', 'N/A')}",
                    expanded=True,
                ):
                    for key, value in report_data.items():
                        if key not in ("id", "created_at", "patient_id", "follow_up"):
                            if key == "content":
                                # Display content directly without a header
                                st.markdown(value)
                            else:
                                st.markdown(f"### {key}")
                                st.markdown(value)

                    # Generate PDF and display download link
                    # Find the corresponding patient record if available
                    patient_record = None
                    if "records" in st.session_state:
                        for record in st.session_state.records:
                            if str(record[3]) == str(report_data.get("patient_id")):
                                patient_record = record
                                break

                    pdf_bytes = generate_pdf(report_data, patient_record=patient_record)
                    if pdf_bytes is not None:
                        st.download_button(
                            label=f"Download Report {i+1}",
                            data=pdf_bytes,
                            file_name=f"report_{i+1}.pdf",
                            mime="application/pdf",
                        )
