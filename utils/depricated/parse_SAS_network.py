import json
from pprint import pprint
from collections import defaultdict
#
# with open('example.sas','r', encoding='utf-8')as f:
#     sas=f.read()

import re

def clean_initial_code(run_code):
    run_code = re.sub(r"/\*-*\*/\s*", "", run_code)
    return run_code
def extract_inputs_outputs(run_code):
    """
    Extracts input and output datasets from `DATA` and `PROC` steps.
    - Outputs: Datasets from `DATA` statements.
    - Inputs: Datasets from `SET`, `MERGE`, and `DATA=`/`OUT=` options in `PROC` steps.
    """
    inputs = set()
    outputs = set()

    # Capture the output dataset from DATA statements
    data_match = re.search(r'\bDATA\s+([A-Z0-9_.]+)', run_code, re.IGNORECASE)
    if data_match:
        outputs.add(data_match.group(1))

    # Capture input datasets from SET
    set_match = re.findall(r'\bSET\s+([A-Z0-9_.]+)', run_code, re.IGNORECASE)
    inputs.update(set_match)

    # Capture input datasets from MERGE
    merge_match = re.findall(r'\bMERGE\s+([^;]+)', run_code, re.IGNORECASE)
    for merge_group in merge_match:
        merge_datasets = re.findall(r'\b([A-Z0-9_.]+)(?:\s*\(IN=[A-Z0-9_]+\))?', merge_group, re.IGNORECASE)
        inputs.update(merge_datasets)

    # Capture input/output datasets from PROC steps
    proc_match = re.findall(r'\b(DATA|OUT)\s*=\s*([A-Z0-9_.]+)', run_code, re.IGNORECASE)
    for keyword, dataset in proc_match:
        if keyword.upper() == "DATA":
            inputs.add(dataset)
        elif keyword.upper() == "OUT":
            outputs.add(dataset)

    return inputs, outputs


def parse_sas_script(sas_script):
    """
    Parses a SAS script and extracts sections, runs, inputs, and outputs.
    """



    sections = re.split(r'--#+', sas_script)  # Split by comment blocks
    parsed_data = []

    for i_sec, section in enumerate(sections):
        """
          Splits a SAS section into individual runs based on full-line `RUN;` and `QUIT;`.
          This ensures comments and conditions remain part of the correct block.
        """
        runs =  re.split(r'\b(RUN|QUIT);\s*\n', section, flags=re.IGNORECASE)

        for i_run, run_code in enumerate(runs):
            run_code = run_code.strip()
            if not run_code:
                continue

            inputs, outputs = extract_inputs_outputs(run_code)

            """
            When split on RUN or QUIT is done, these split sites are separated from the run script. 
            These parts result into output dictionaries with empty inputs,outputs and run_code stating only 'run' or quit'
            That is split_residual (rubbish), therefore removed with this if statement 
            (dont append to final output if its a split residual)
            NOTE: This also removes dictionary if it holds no inputs and run_code is only a comment
            
            Other attemts to deal with it: 
            Tried to use lookup regex, but it requires len('QUIT')==len('RUN') which is false. 
            Could not by pass it by adding ';' to 'RUN' - returns more aforementioned split_residuals 
            """

            is_split_residual=all([inputs==set(),outputs==set()])
            if not is_split_residual:

                parsed_data.append({
                    "section_index": i_sec, # index of a section in code
                    "run_index": i_run, # index of a run in section
                    "run_code": run_code + '',
                    "inputs": list(inputs),
                    "outputs": list(outputs)
                })


    return parsed_data





def merge_identity_runs(parsed_data):
    """
    Detects runs where `inputs` and `outputs` are identical single-element sets.
    Groups them by `inputs`, sorts by `section_index` and `run_index`,
    and concatenates their `run_code` with a newline separator.
    """
    grouped_runs = defaultdict(list)

    # Step 1: Identify and group runs with identical input/output
    for run in parsed_data:
        if len(run["inputs"]) == 1 and run["inputs"] == run["outputs"]:
            key = tuple(run["inputs"])  # Convert set to a tuple (since it's a single element)
            grouped_runs[key].append(run)

    # Step 2: Merge grouped runs
    merged_runs = []
    seen_run_keys = set()

    for group_key, runs in grouped_runs.items():
        # Sort by section_index and run_index
        runs.sort(key=lambda x: (x["section_index"], x["run_index"]))

        # Concatenate run_code
        merged_run_code = "\n".join(run["run_code"] for run in runs)

        # Create a new merged dictionary
        merged_run = {
            "section_index": runs[0]["section_index"],
            "run_index": runs[0]["run_index"],  # Keep the first run index
            "run_code": merged_run_code,
            "inputs": runs[0]["inputs"],
            "outputs": runs[0]["outputs"]
        }
        merged_runs.append(merged_run)

        # Track seen runs using (section_index, run_index)
        for run in runs:
            seen_run_keys.add((run["section_index"], run["run_index"]))

    # Step 3: Keep other runs that were not merged
    final_data = [run for run in parsed_data if
                  (run["section_index"], run["run_index"]) not in seen_run_keys] + merged_runs

    # Sort final data by section_index and run_index again
    final_data.sort(key=lambda x: (x["section_index"], x["run_index"]))

    return final_data

import networkx as nx

def assign_subgraph_ids(parsed_data):
    """
    Assigns a unique `sub_graph_id` to each SAS run based on dataset dependencies.
    Uses `networkx` to detect subnetworks.
    """
    G = nx.DiGraph()

    # Step 1: Build the directed graph
    for run in parsed_data:
        for inp in set(run["inputs"]):  # Ensure inputs are treated as a set
            for out in set(run["outputs"]):  # Ensure outputs are treated as a set
                G.add_edge(inp, out)  # Directed edge from input to output

    # Step 2: Identify weakly connected components (subgraphs)
    subgraph_mapping = {}
    for subgraph_id, component in enumerate(nx.connected_components(G.to_undirected())):
        for dataset in component:
            subgraph_mapping[dataset] = subgraph_id  # Map datasets to a subgraph ID

    # Step 3: Assign `sub_graph_id` to each run
    for run in parsed_data:
        # Convert inputs and outputs to sets before processing
        related_datasets = set(run["inputs"]) | set(run["outputs"])
        run["sub_graph_id"] = next((subgraph_mapping[ds] for ds in related_datasets if ds in subgraph_mapping), None)

    return parsed_data




def save_results(results):
    # Save parsed results as JSON

    output_json_path = "../../data/parsed_sas_results.json"

    with open(output_json_path, "w", encoding="utf-8") as json_file:
        json.dump(results, json_file, indent=4)

    print(f"Parsed results saved to {output_json_path}")
    print("Head of saved file:")

if __name__=='__main__':

    # Example usage
    sas_file_path = "../../data/example.sas"  # Replace with your actual SAS file
    with open(sas_file_path, 'r', encoding='utf-8') as file:
        sas_script = file.read()

    sas_script = clean_initial_code(sas_script)
    parsed_results = parse_sas_script(sas_script)
    merged_results = merge_identity_runs(parsed_results)
    merged_results=assign_subgraph_ids(merged_results)
    save_results(merged_results)
    print()
    print("Head of parsed results")
    pprint(merged_results[0:2])




from pyvis.network import Network
import regex as re
import networkx as nx
from graphviz import Digraph

def create_net_html_ins_outs(nodes, edges, physics, height, layout='repulsion'):
    # Create a NetworkX graph from the provided lists
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # Create a PyVis network
    net = Network(
        height=f"{str(height)}px",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        directed=True
        # select_menu=True
    )

    # Populate the PyVis network with the NetworkX graph
    net.from_nx(G)
    net.toggle_physics(physics)

    if layout in ['barnes_hut',"repulsion","force_atlas_2based","hierarchical_repulsion"]:
        # Conditionally apply different layout algorithms or hierarchical settings
        if layout == "repulsion":
            net.repulsion(
                node_distance=200,
                central_gravity=0.2,
                spring_length=200,
                spring_strength=0.05,
                damping=0.09
            )
        elif layout == "barnes_hut":
            net.barnes_hut(
                central_gravity=0.3,
                spring_length=95,
                spring_strength=0.1,
                damping=0.09,
                overlap=0
            )
        elif layout == "force_atlas":
            net.force_atlas_2based(
                gravitation=0.2,
                central_gravity=0.01,
                spring_length=100,
                spring_strength=0.08,
                damping=0.4
            )
        elif layout == "hierarchical":
            net.set_options("""
               var options = {
                 layout: {
                   hierarchical: {
                     enabled: true,
                     levelSeparation: 150,
                     nodeSpacing: 100,
                     treeSpacing: 200,
                     blockShifting: true,
                     edgeMinimization: true,
                     parentCentralization: true,
                     direction: 'UD',
                     sortMethod: 'hubsize',
                     shakeTowards: 'leaves'
                   }
                 }
               }
               """)

    # Generate the HTML for the PyVis network
    html_data = net.generate_html()

    # Adds feature: copy node name upon double-clicking on it
    custom_script = """
    <script>
    (function() {
        // Wait until the Vis network is fully initialized
        // "network" is the variable PyVis uses to reference the Vis.js Network.
        // We'll attach an event listener for 'doubleClick'
        network.on("doubleClick", function(params) {
            if (params.nodes.length > 0) {
                // 'params.nodes[0]' is the ID of the clicked node
                var nodeId = params.nodes[0];

                // Retrieve the node's label from the network data
                var nodeLabel = network.body.data.nodes.get(nodeId).label;

                // Copy to clipboard
                copyTextToClipboard(nodeLabel);

                // Show an alert (optional)
                // alert("Copied node label: " + nodeLabel);
            }
        });

        function copyTextToClipboard(text) {
            if (navigator.clipboard && window.isSecureContext) {
                // modern approach with Clipboard API
                return navigator.clipboard.writeText(text);
            } else {
                // fallback to the 'execCommand()' solution
                let textArea = document.createElement("textarea");
                textArea.value = text;
                // make the textarea out of viewport
                textArea.style.position = "fixed";
                textArea.style.left = "-999999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                document.execCommand("copy");
                document.body.removeChild(textArea);
            }
        }
    })();
    </script>
            """
    modified_html = html_data.replace("</body>", f"{custom_script}\n</body>")

    return modified_html


def create_graphviz_graph_ins_outs(nodes, edges, physics=True, height=1000):
    """
    Create a graphviz Digraph from lists of nodes and edges.

    :param nodes: A list of node identifiers (strings, numbers, etc.).
    :param edges: A list of edges, where each edge is a tuple (source, target).
    :param physics: (Unused in Graphviz) included for signature compatibility.
    :param height: (Unused in Graphviz) included for signature compatibility.
    :return: A graphviz.Digraph object.
    """
    # Create a NetworkX graph from the provided lists (for convenience)
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # Initialize a directed Graphviz graph
    dot = Digraph()
    dot.attr('graph', size=f"0,{height}!")

    # Add nodes to the Graphviz object
    for node in G.nodes():
        dot.node(str(node))

    # Add edges to the Graphviz object
    for u, v in G.edges():
        dot.edge(str(u), str(v))

    return dot