import json
import networkx as nx
from collections import defaultdict


def generate_mermaid_markdown(data):
    unique_inputs = {}
    unique_outputs = {}
    run_codes = {}
    edges = []
    subgraphs = defaultdict(set)  # Use a set to avoid duplicate definitions

    for idx, entry in enumerate(data):
        run_id = f"run_{entry['run_index']}"
        process_id = f"proc_{idx}"
        run_label = entry['run_code'].replace('\n', ' ')
        run_codes[process_id] = run_label
        subgraph_id = f"Chart{entry['sub_graph_id']}"

        for input_node in entry['inputs']:
            if input_node not in unique_inputs:
                unique_inputs[input_node] = f"input_{len(unique_inputs)}"
            edges.append((unique_inputs[input_node], process_id))
            subgraphs[subgraph_id].add((unique_inputs[input_node], input_node))

        for output_node in entry['outputs']:
            if output_node not in unique_outputs:
                unique_outputs[output_node] = f"output_{len(unique_outputs)}"
            edges.append((process_id, unique_outputs[output_node]))
            subgraphs[subgraph_id].add((unique_outputs[output_node], output_node))

        subgraphs[subgraph_id].add((process_id, run_label))

    mermaid_structure = "flowchart TB\n"

    for subgraph, nodes in subgraphs.items():
        mermaid_structure += f'    subgraph {subgraph}\n'
        for node_id, label in nodes:
            mermaid_structure += f'        {node_id}["{label}"]\n'
        mermaid_structure += "    end\n\n"

    # Adding invisible connections to force stacking
    subgraph_keys = list(subgraphs.keys())
    for i in range(len(subgraph_keys) - 1):
        mermaid_structure += f'    {subgraph_keys[i]} -->|Stacked Below| {subgraph_keys[i + 1]}\n'

    for src, dst in edges:
        mermaid_structure += f'    {src} --> {dst}\n'

    mermaid_structure += "\nclassDef input_output fill:#90EE90,stroke:#000,stroke-width:1px;\n"
    mermaid_structure += "classDef run_code fill:#ADD8E6,stroke:#000,stroke-width:1px;\n"

    return mermaid_structure


# Read input data from a JSON file

if __name__=='__main__':
    with open(r'C:\Users\lvasionis\PycharmProjects\devs\SAS DAG\data\parsed_sas_results.json', 'r') as file:
        data = json.load(file)
    # Generate Mermaid markup
    mermaid_markup = generate_mermaid_markdown(data)
    print(mermaid_markup)