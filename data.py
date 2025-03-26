"""
Streamlit의 sidebar에서 환자 선택 및 이미지 로드 기능을 제공하는 script입니다.
"""

from typing import List, Optional
from dataclasses import dataclass, field
import streamlit as st
from pathlib import Path


@dataclass
class CXRRecord:
    """Data model for a single chest X-ray record."""
    image_index: str
    finding_labels: List[str] = field(default_factory=list)
    follow_up: Optional[int] = None
    patient_id: Optional[int] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    view_position: Optional[str] = None


def simplified_path_finder() -> List[tuple]:
    """
    Simplified function that provides only two predefined patients with their images.
    Returns a list of tuples in the same format as the original path_finder.
    """
    # Use pathlib for relative path resolution
    SCRIPT_DIR = Path(__file__).parent
    IMAGES_DIR = SCRIPT_DIR / "images"
    
    # Create the simplified sidebar
    st.sidebar.header("Patient Selection")
    
    # Preserve selected patient ID and selections in session state
    if "data_patient_id" not in st.session_state:
        st.session_state.data_patient_id = "00000001"
    
    if "data_load_images" not in st.session_state:
        st.session_state.data_load_images = False
    
    if "data_paths" not in st.session_state:
        st.session_state.data_paths = []
    
    # Pusedo define of the two patients and their images
    patients = {
        "00000001": {
            "images": [
                {"name": "00000001_000.png", "finding": ["No Finding"], "follow_up": 0},
                {"name": "00000001_001.png", "finding": ["Pneumonia"], "follow_up": 1},
                {"name": "00000001_002.png", "finding": ["Effusion"], "follow_up": 2},
            ],
            "age": 45,
            "gender": "M",
            "view_position": "PA"
        },
        "00000002": {
            "images": [
                {"name": "00000002_000.png", "finding": ["Nodule"], "follow_up": 0}
            ],
            "age": 62,
            "gender": "F",
            "view_position": "AP"
        }
    }
    
    # Let user select one of the two patients
    patient_id = st.sidebar.radio(
        "Select Patient ID", 
        options=["00000001", "00000002"],
        key="patient_id_select",
        index=0 if st.session_state.data_patient_id == "00000001" else 1,
        on_change=lambda: setattr(st.session_state, "data_patient_id", st.session_state.patient_id_select)
    )
    
    # Get the selected patient's data
    selected_patient = patients[patient_id]
    
    # Show the patient's images
    st.sidebar.subheader(f"Images for Patient {patient_id}")
    
    # Create image options for selection
    image_options = []
    for i, img in enumerate(selected_patient["images"]):
        image_options.append(f"[{i}] {img['name']}")
    
    # Let user select images
    selected_indices = st.sidebar.multiselect(
        "Select Images",
        options=image_options,
        default=image_options,  # Default to all options selected
        key="selected_indices"
    )
    
    # Allow selecting all images
    all_images = st.sidebar.checkbox("Select All Images", value=True, key="all_images")
    
    # Button to confirm selection
    load_button_clicked = st.sidebar.button("Load Selected Images")
    
    # Check if button was clicked or if images were already loaded
    if load_button_clicked:
        st.session_state.data_load_images = True
    
    # Process the selections and store results in session state
    if st.session_state.data_load_images:
        # Reset paths if selection may have changed
        if load_button_clicked:
            st.session_state.data_paths = []
            
        # Only process if paths haven't been processed yet
        if not st.session_state.data_paths:
            if all_images:
                # Process all images for the selected patient
                for img in selected_patient["images"]:
                    # Initialize image_path
                    image_path = IMAGES_DIR / img['name']
                    
                    st.session_state.data_paths.append(
                        (
                            image_path,
                            img["finding"],
                            img["follow_up"],
                            int(patient_id),
                            selected_patient["age"],
                            selected_patient["gender"],
                            selected_patient["view_position"]
                        )
                    )
            elif selected_indices:
                # Process only selected images
                for selection in selected_indices:
                    idx = int(selection.split("]")[0].replace("[", ""))
                    if 0 <= idx < len(selected_patient["images"]):
                        img = selected_patient["images"][idx]
                        image_path = IMAGES_DIR / img['name']
                        
                        st.session_state.data_paths.append(
                            (
                                image_path,
                                img["finding"],
                                img["follow_up"],
                                int(patient_id),
                                selected_patient["age"],
                                selected_patient["gender"],
                                selected_patient["view_position"]
                            )
                        )
            else:
                st.sidebar.warning("No images selected. Please select at least one image.")
                
        # Show what's been loaded
        if st.session_state.data_paths:
            st.sidebar.success(f"Loaded {len(st.session_state.data_paths)} images")
            
            # Add a small preview of loaded images
            for i, path_tuple in enumerate(st.session_state.data_paths):
                path = path_tuple[0]
                filename = path.name
                st.sidebar.write(f"{i+1}. {filename}")
    
    # Return the paths from session state
    return st.session_state.data_paths


# Replace the original path_finder with our simplified version
def path_finder(*args, **kwargs) -> List[tuple]:
    """
    Main function to load predefined patient data.
    Returns a list of tuples containing (image_path, finding_labels, follow_up, patient_id, patient_age, patient_gender, view_position).
    """
    return simplified_path_finder()
