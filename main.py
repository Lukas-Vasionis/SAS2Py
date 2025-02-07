import streamlit as st
from utils.parse_utils import StructuredSAS
from utils.mermaid_utils import generate_mermaid_markdown
import pyperclip
from utils.network_utils import create_net_html_ins_outs

############################################################
# 1. Set page configuration
############################################################
st.set_page_config(layout="wide")


############################################################
# 2. Persistent State Management
############################################################
# In Streamlit, we can maintain states using st.session_state.
# We will store certain data in the session state to re-use it across interactions.

# Keys used in session_state:
# - 'sas_script': store the SAS script text
# - 'struct_SAS': store the StructuredSAS object
# - 'flow_chart': store the generated mermaid markdown
# - 'show_flow_chart': boolean flag to show/hide flow chart
# - 'show_network_graph': boolean flag to show/hide network graph
# - 'show_metadata': boolean flag to show/hide metadata

# Initialize session state variables if they don't exist
if 'sas_script' not in st.session_state:
    st.session_state['sas_script'] = None

if 'struct_SAS' not in st.session_state:
    st.session_state['struct_SAS'] = None

if 'flow_chart' not in st.session_state:
    st.session_state['flow_chart'] = None

if 'show_flow_chart' not in st.session_state:
    st.session_state['show_flow_chart'] = False

if 'show_network_graph' not in st.session_state:
    st.session_state['show_network_graph'] = False

if 'show_metadata' not in st.session_state:
    st.session_state['show_metadata'] = False

############################################################
# 3. Application Header
############################################################
st.title("SAS code analyser")

############################################################
# 4. File Uploader
############################################################
uploaded_file = st.file_uploader("##Upload SAS code as txt", type=["txt"])

# If a file is uploaded, read and store in session_state
if uploaded_file is not None:
    # Read uploaded file
    content = uploaded_file.read().decode('utf-8')
    st.session_state['sas_script'] = content

# If we have SAS script in session state, parse it
if st.session_state['sas_script']:
    st.session_state['struct_SAS'] = StructuredSAS(st.session_state['sas_script']).execute_all_processing_steps()

############################################################
# 5. Flow Chart Generation
############################################################
# col_flow_chart, col_copy = st.columns([1,0.2])

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            ### Mermaid mardown
            **[Proof of concept | Experimental]**
            
            This is one of the solutions to visualise SAS code in network manner. 
            It attempts to visualise SAS code as inputs -> precessing code -> outputs
            Since python doesnt have a convenient way to visualise this, I use Mermaid markdown and its visuasation tool. 
            
            So click "Copy Flow Chart and paste it into Mermaid tool  at: https://www.mermaidchart.com/play#
            
            """
        )
    with col2:
        if st.button("Get Flow Chart"):
            # Generate flow chart only if we have a struct_SAS
            if st.session_state['struct_SAS']:
                flow_chart = generate_mermaid_markdown(st.session_state['struct_SAS'].struct_code)
                st.session_state['flow_chart'] = flow_chart
                # st.session_state['show_flow_chart'] = True

        # If flow chart is generated, show copy button
        # with col_copy:
        if st.session_state['flow_chart']:
            if st.button('Copy to clipboard'):
                pyperclip.copy(st.session_state['flow_chart'])
                st.success('Text copied successfully!\nPaste it here: https://www.mermaidchart.com/play#')


############################################################
# 6. Show Network Graph
############################################################
with st.container(border=True):
    st.markdown(
        """
        ### Network graph: inputs and outputs
        
        Shows connections between inputs and outputs in the SAS code.
        """
    )
    if st.button("Show Network Graph"):
        st.session_state['show_network_graph'] = True

    if st.session_state['show_network_graph'] and st.session_state['struct_SAS']:

        # Widgets
        graph_net_ins_outs_height = st.slider("Select height for network graph", min_value=100, max_value=800, step=10, value=750)
        physics_button = st.toggle("Toggle Physics in the network graph")

        # Data processing and visualization
        html_data = create_net_html_ins_outs(
            nodes=st.session_state['struct_SAS'].nodes,
            edges=st.session_state['struct_SAS'].edges,
            physics=physics_button,
            height=graph_net_ins_outs_height)

        st.markdown("**Double click a node to copy its name!**")

        st.components.v1.html(html_data, height=graph_net_ins_outs_height)

############################################################
# 7. Capture Metadata
############################################################
if st.button("Capture metadata"):
    st.session_state['show_metadata'] = True

if st.session_state['show_metadata'] and st.session_state['struct_SAS']:
    with st.container():
        st.text("Inputs")
        st.code(st.session_state['struct_SAS'].inputs)

        st.text("Outputs")
        st.code(st.session_state['struct_SAS'].outputs)

        st.text("Sub graphs")
        st.code(st.session_state['struct_SAS'].subgraphs)

############################################################
# 8. Search in the Code
############################################################
with st.form("Capture code snippets"):
    query = st.text_input("Search results")
    search_in = st.radio("What are you interested in?", options=['inputs', 'outputs', 'run_code'])
    submit = st.form_submit_button("Search")
    if submit:
        if st.session_state['struct_SAS']:
            search_results = [x for x in st.session_state['struct_SAS'].pre_processed if query in x[search_in]]
            st.json(search_results)

############################################################
# 9. Show the original SAS script
############################################################
if st.session_state['sas_script']:
    st.subheader("Original SAS Script")
    st.code(st.session_state['sas_script'])
