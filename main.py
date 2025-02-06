import streamlit as st
from utils.parse_utils import StructuredSAS
from utils.mermaid_utils import generate_mermaid_markdown
import pyperclip
from utils.network_utils import create_net_html_ins_outs

import networkx as nx
import matplotlib.pyplot as plt
import regex as re

st.set_page_config(layout="wide")


st.title("Graph Visualization with Mermaid")

# File uploader for JSON input
uploaded_file = st.file_uploader("Upload SAS file", type=["sas", "txt"])


if uploaded_file:
    ####################
    # Data processing
    sas_script = uploaded_file.read().decode('utf-8')
    struct_SAS = StructuredSAS(sas_script).execute_all_processing_steps()
    ####################
    # Get Flow chart
    flow_chart_button=st.button("Get Flow Chart")
    if flow_chart_button:
        flow_chart=generate_mermaid_markdown(struct_SAS.struct_code)
        if flow_chart:
            with open("data/fl_chart.txt", 'w', encoding="utf-8") as f:
                f.write(flow_chart)

            if st.button('Copy'):
                pyperclip.copy(flow_chart)
                st.success('Text copied successfully!\nPaste it here: https://www.mermaidchart.com/play#')

    ####################
    # Show network graph
    show_network_graph=st.button("Show network graph")
    with st.container(border=True):
        graph_net_ins_outs_height=st.slider("Select height for network graph", min_value=100, max_value=800, step=10, value=750)
        html_data=create_net_html_ins_outs(struct_SAS.nodes, struct_SAS.edges)
        # Embed the HTML into the Streamlit app
        st.markdown("**Double click a node to copy its name!**")
        st.components.v1.html(html_data, height=graph_net_ins_outs_height)

    ####################
    # Capture metadata
    capture_metadata=st.button("Capture metadata")
    if capture_metadata:
        with st.container(border=True):
            with st.container(border=True):
                st.text("Inputs")
                st.code(struct_SAS.inputs)
            with st.container(border=True):
                st.text("Outputs")
                st.code(struct_SAS.outputs)
            with st.container(border=True):
                st.text("Sub graphs")
                st.code(struct_SAS.subgraphs)

    ####################
    # Search in the code
    form_capture_script = st.form("Capture code snippets")
    query = form_capture_script.text_input("Search results")
    search_in = form_capture_script.radio("What are you interested in?", options=['inputs', 'outputs', 'run_code'])

    submit = form_capture_script.form_submit_button("Search")
    if submit:
        search_results = [x for x in struct_SAS.pre_processed if query in x[search_in]]
        form_capture_script.json(search_results,)

    st.code(sas_script)