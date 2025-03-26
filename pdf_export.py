"""
마크다운 형식의 보고서를 PDF로 변환하는 script입니다.
"""

import streamlit as st
from datetime import datetime

try:
    from fpdf import FPDF

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def generate_pdf(report_data, patient_record=None):
    """
    Generate a PDF from the report data with markdown support

    Args:
        report_data: Dictionary containing report data
        patient_record: Optional tuple containing patient record data

    Returns:
        bytes: PDF file as bytes
    """
    if not PDF_AVAILABLE:
        st.error(
            "PDF generation requires the fpdf package. Please install it with 'pip install fpdf'."
        )
        return None

    try:
        # Create PDF instance
        pdf = FPDF()
        pdf.add_page()

        # Set up font
        pdf.set_font("Arial", size=12)

        # Add title
        pdf.set_font("Arial", "B", 16)
        patient_id = report_data.get("patient_id", "Unknown")
        follow_up = report_data.get("follow_up", "N/A")
        pdf.cell(
            200,
            10,
            txt=f"CXR Report - Patient ID: {patient_id}, Follow-up: {follow_up}",
            ln=True,
            align="C",
        )
        pdf.ln(5)

        # Add creation date
        pdf.set_font("Arial", size=10)
        created_at = report_data.get(
            "created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        pdf.cell(200, 10, txt=f"Created: {created_at}", ln=True)

        # Add patient record data if available
        if patient_record:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(200, 10, txt="Patient Record", ln=True)
            pdf.set_font("Arial", size=10)

            # Unpack patient record information
            (
                image_path,
                finding_labels,
                follow_up,
                patient_id,
                patient_age,
                patient_gender,
                view_position,
            ) = patient_record

            # Format finding labels for better readability
            formatted_findings = (
                ", ".join(finding_labels)
                if isinstance(finding_labels, list)
                else str(finding_labels)
            )

            # Create a table-like structure with patient data
            patient_data = [
                ("Finding Labels", formatted_findings),
                ("Follow-up", str(follow_up) if follow_up is not None else "N/A"),
                ("Patient ID", str(patient_id) if patient_id is not None else "N/A"),
                ("Age", str(patient_age) if patient_age is not None else "N/A"),
                (
                    "Gender",
                    str(patient_gender) if patient_gender is not None else "N/A",
                ),
                (
                    "View Position",
                    str(view_position) if view_position is not None else "N/A",
                ),
            ]

            # Draw patient data in table format
            col_width = 40
            row_height = 6
            for label, value in patient_data:
                pdf.cell(col_width, row_height, txt=label, border=1)
                # Ensure value fits within the remaining width by truncating if necessary
                max_value_width = 150
                value_text = value[:50] + "..." if len(value) > 60 else value
                pdf.cell(max_value_width, row_height, txt=value_text, border=1, ln=True)

        pdf.ln(10)

        # Process report content with markdown handling
        for key, value in report_data.items():
            if key not in ("id", "created_at", "patient_id", "follow_up", "content"):
                # Section header
                pdf.set_font("Arial", "B", 14)
                pdf.cell(200, 10, txt=key, ln=True)
                pdf.ln(2)

                # Section content
                pdf.set_font("Arial", size=12)
                process_markdown_to_pdf(pdf, value)
                pdf.ln(5)
            elif key == "content":
                # For content key, split into sections and process
                process_markdown_to_pdf(pdf, value)

        # Get the PDF as bytes
        pdf_output = pdf.output(dest="S").encode("latin1")
        return pdf_output

    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None


def process_markdown_to_pdf(pdf, markdown_text):
    """
    Process markdown text into PDF format with basic formatting

    Args:
        pdf: FPDF instance
        markdown_text: Text with markdown formatting
    """
    # Split text into lines for processing
    lines = markdown_text.split("\n")

    current_indent = 0
    in_list = False

    for line in lines:
        if not line.strip():
            # Add space for empty lines
            pdf.ln(5)
            continue

        # Check for headers
        if line.startswith("# "):
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, txt=line[2:].strip(), ln=True)
            pdf.ln(2)
            continue
        elif line.startswith("## "):
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, txt=line[3:].strip(), ln=True)
            pdf.ln(2)
            continue
        elif line.startswith("### "):
            pdf.set_font("Arial", "B", 13)
            pdf.cell(0, 10, txt=line[4:].strip(), ln=True)
            pdf.ln(2)
            continue

        # Check for bullet points
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            in_list = True
            indent = len(line) - len(line.lstrip())
            if indent > current_indent:
                current_indent = indent

            bullet_text = line.strip()[2:].strip()

            # Determine indentation level (for nested lists)
            indent_level = indent // 2
            pdf.set_x(10 + (indent_level * 5))

            # Draw bullet
            pdf.set_font("Arial", size=10)
            pdf.cell(
                5, 5, txt="-", ln=0
            )  # Use hyphen instead of bullet point to avoid encoding issues

            # Draw bullet text
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 5, txt=bullet_text)
            continue
        elif (
            in_list
            and line.strip()
            and not (line.strip().startswith("- ") or line.strip().startswith("* "))
        ):
            in_list = False
            current_indent = 0

        # Process bold text with **text** format
        if "**" in line:
            parts = line.split("**")
            x_pos = pdf.get_x()

            for i, part in enumerate(parts):
                # Toggle between normal and bold
                if i % 2 == 1:  # Odd indices are bold
                    pdf.set_font("Arial", "B", 12)
                else:
                    pdf.set_font("Arial", size=12)

                if part:
                    width = pdf.get_string_width(part)
                    if x_pos + width > pdf.w - 20:  # Check if we need to wrap
                        pdf.ln()
                        x_pos = pdf.get_x()
                    pdf.cell(width, 5, txt=part, ln=0)
                    x_pos += width

            pdf.ln()
        else:
            # Normal text
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 5, txt=line)
