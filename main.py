import streamlit as st
from utils import parse_SAS_network as parse_SAS
from utils.dev_MermaidMD import generate_mermaid_markdown
import pyperclip

import regex as re

def clean_run_code(parsed_results):
    """
    Cleans the `run_code` values in the parsed SAS results dictionary list.

    Fixes:
    - Removes special characters like `?` and inline comments (`/* */`).
    - Replaces newlines with `\n` literal inside Mermaid `[ ... ]` brackets.
    - Ensures Mermaid compatibility for `run_code` values.

    Args:
        parsed_results (list): List of dictionaries containing SAS parsing results.

    Returns:
        list: Cleaned list of dictionaries.
    """
    cleaned_results = []

    for entry in parsed_results:
        run_code = entry.get("run_code", "")

        # Remove inline comments (/* ... */)
        run_code = re.sub(r"/\*.*?\*/", "", run_code, flags=re.DOTALL)

        # Remove special characters that may break Mermaid
        run_code = run_code.replace("?", "")

        # Replace raw newlines inside a Mermaid-friendly structure
        run_code=[x.strip().replace(r'\n', "<br>") for x in run_code.splitlines()]
        run_code = '<br>'.join(run_code)
        # run_code = run_code.replace("\n", r"\n")

        # Replacing single quotes
        run_code=run_code.replace("'","&apos;")

        # Store cleaned result
        cleaned_entry = entry.copy()
        cleaned_entry["run_code"] = run_code
        cleaned_results.append(cleaned_entry)

    return cleaned_results

if "svg_height" not in st.session_state:
    st.session_state["svg_height"] = 200

if "previous_mermaid" not in st.session_state:
    st.session_state["previous_mermaid"] = ""

st.title("Graph Visualization with Mermaid")

# File uploader for JSON input
uploaded_file = st.file_uploader("Upload SAS file", type=["sas"])


if uploaded_file:
    sas_script = uploaded_file.read().decode('utf-8')

    sas_script = parse_SAS.clean_initial_code(sas_script)
    parsed_results = parse_SAS.parse_sas_script(sas_script)
    merged_results = parse_SAS.merge_identity_runs(parsed_results)
    merged_results = clean_run_code(merged_results)
    merged_results = parse_SAS.assign_subgraph_ids(merged_results)

    flow_chart=generate_mermaid_markdown(merged_results)
    with open("fl_chart.txt", 'w',encoding="utf-8") as f:
        f.write(flow_chart)

    if flow_chart:
        if st.button('Copy'):
            pyperclip.copy(flow_chart)
            st.success('Text copied successfully!\nPaste it here: https://www.mermaidchart.com/play#')
