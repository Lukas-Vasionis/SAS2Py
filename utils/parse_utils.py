import json
from pprint import pprint
from collections import defaultdict
import networkx as nx
#
# with open('example.sas','r', encoding='utf-8')as f:
#     sas=f.read()

import re


class StructuredSAS:
    def __init__(self, raw_code):
        self.raw_code = raw_code
        self.pre_processed=None
        self.struct_code=None
        self.mermaid_structure=None
        self.inputs = None
        self.outputs = None
        self.subgraphs = None
        self.edges=None
        self.nodes=None

    def clean_initial_code(self):
        self.struct_code = re.sub(r"/\*-*\*/\s*", "", self.raw_code)
        return self

    def parse_sas_script(self):
        def extract_inputs_outputs(run_code_):
            """
            Extracts input and output datasets from `DATA` and `PROC` steps.
            - Outputs: Datasets from `DATA` statements.
            - Inputs: Datasets from `SET`, `MERGE`, and `DATA=`/`OUT=` options in `PROC` steps.
            """
            inputs = set()
            outputs = set()

            # Capture the output dataset from DATA statements
            data_match = re.search(r'\bDATA\s+([A-Z0-9_.]+)', run_code_, re.IGNORECASE)
            if data_match:
                outputs.add(data_match.group(1))

            # Capture input datasets from SET
            set_match = re.findall(r'\bSET\s+([A-Z0-9_.]+)', run_code_, re.IGNORECASE)
            inputs.update(set_match)

            # Capture input datasets from MERGE
            merge_match = re.findall(r'\bMERGE\s+([^;]+)', run_code_, re.IGNORECASE)
            for merge_group in merge_match:
                merge_datasets = re.findall(r'\b([A-Z0-9_.]+)(?:\s*\(IN=[A-Z0-9_]+\))?', merge_group, re.IGNORECASE)
                inputs.update(merge_datasets)

            # Capture input/output datasets from PROC steps
            proc_match = re.findall(r'\b(DATA|OUT)\s*=\s*([A-Z0-9_.]+)', run_code_, re.IGNORECASE)
            for keyword, dataset in proc_match:
                if keyword.upper() == "DATA":
                    inputs.add(dataset)
                elif keyword.upper() == "OUT":
                    outputs.add(dataset)

            return inputs, outputs
        """
        Parses a SAS script and extracts sections, runs, inputs, and outputs.
        """

        sections = re.split(r'--#+', self.struct_code)  # Split by comment blocks
        parsed_data = []

        for i_sec, section in enumerate(sections):
            """
              Splits a SAS section into individual runs based on full-line `RUN;` and `QUIT;`.
              This ensures comments and conditions remain part of the correct block.
            """
            runs = re.split(r'\b(RUN|QUIT);\s*\n', section, flags=re.IGNORECASE)

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

                is_split_residual = all([inputs == set(), outputs == set()])
                if not is_split_residual:
                    parsed_data.append({
                        "section_index": i_sec,  # index of a section in code
                        "run_index": i_run,  # index of a run in section
                        "run_code": run_code + '',
                        "inputs": list(inputs),
                        "outputs": list(outputs)
                    })
        self.pre_processed=parsed_data
        return self

    def merge_identity_runs(self):
        """
        Detects runs where `inputs` and `outputs` are identical single-element sets.
        Groups them by `inputs`, sorts by `section_index` and `run_index`,
        and concatenates their `run_code` with a newline separator.
        """
        grouped_runs = defaultdict(list)

        # Step 1: Identify and group runs with identical input/output
        for run in self.pre_processed:
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
        final_data = [run for run in self.pre_processed if
                      (run["section_index"], run["run_index"]) not in seen_run_keys] + merged_runs

        # Sort final data by section_index and run_index again
        final_data.sort(key=lambda x: (x["section_index"], x["run_index"]))

        self.struct_code=final_data
        return self

    def assign_subgraph_ids(self):
        """
        Assigns a unique `sub_graph_id` to each SAS run based on dataset dependencies.
        Uses `networkx` to detect subnetworks.
        """
        G = nx.DiGraph()

        # Step 1: Build the directed graph
        for run in self.struct_code:
            for inp in set(run["inputs"]):  # Ensure inputs are treated as a set
                for out in set(run["outputs"]):  # Ensure outputs are treated as a set
                    G.add_edge(inp, out)  # Directed edge from input to output

        # Step 2: Identify weakly connected components (subgraphs)
        subgraph_mapping = {}
        for subgraph_id, component in enumerate(nx.connected_components(G.to_undirected())):
            for dataset in component:
                subgraph_mapping[dataset] = subgraph_id  # Map datasets to a subgraph ID

        # Step 3: Assign `sub_graph_id` to each run
        for run in self.struct_code:
            # Convert inputs and outputs to sets before processing
            related_datasets = set(run["inputs"]) | set(run["outputs"])
            run["sub_graph_id"] = next((subgraph_mapping[ds] for ds in related_datasets if ds in subgraph_mapping),
                                       None)

        return self

    def clean_run_code(self):
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

        for entry in self.struct_code:
            run_code = entry.get("run_code", "")

            # Remove inline comments (/* ... */)
            run_code = re.sub(r"/\*.*?\*/", "", run_code, flags=re.DOTALL)

            # Remove special characters that may break Mermaid
            run_code = run_code.replace("?", "")

            # Replace raw newlines inside a Mermaid-friendly structure
            run_code = [x.strip().replace(r'\n', "<br>") for x in run_code.splitlines()]
            run_code = '<br>'.join(run_code)
            run_code = re.sub("<br>+", "<br>", run_code)

            # run_code = run_code.replace("\n", r"\n")

            # Replacing single and double quotes
            run_code = run_code.replace("'", "&apos;")
            run_code = run_code.replace("\"", "&apos;")

            # Store cleaned result
            cleaned_entry = entry.copy()
            cleaned_entry["run_code"] = run_code
            cleaned_results.append(cleaned_entry)

        self.struct_code=cleaned_results
        return self
    def execute_all_processing_steps(self):
        return self.clean_initial_code()\
            .parse_sas_script().merge_identity_runs()\
            .assign_subgraph_ids()\
            .clean_run_code()\
            .get_metadata()\
            .get_metadata_network()

    def save_results(self):
        # Save parsed results as JSON

        output_json_path = "../data/parsed_sas_results.json"

        with open(output_json_path, "w", encoding="utf-8") as json_file:
            json.dump(self.struct_code, json_file, indent=4)

        print(f"Parsed results saved to {output_json_path}")
        print("Head of saved file:")


    def get_metadata(self):
        def get_selected_metadata(selected_metadata:list, metadata_type)-> list:
            """
            Extracts sets of inputs, outputs and subgraphs in unfiltered code.
            Returns list(set(selected_metadata))

            :param selected_metadata: self.struct_metadata or any list of dictionaries with metadata of sas subscripts
            :param metadata_type: allowed values: 'input', 'output' or 'sub_graph_id'
            :return: list(set(selected_metadata))
            """

            selected_metadata=[x[metadata_type] for x in selected_metadata]

            if all([type(x)==list for x in selected_metadata]): #only inputs and outputs need to be flattened
                selected_metadata=[item for sublist in selected_metadata for item in sublist]

            selected_metadata=list(set(selected_metadata))
            selected_metadata.sort()
            return selected_metadata

        self.inputs = get_selected_metadata(self.struct_code, 'inputs')
        self.outputs = get_selected_metadata(self.struct_code, 'outputs')
        self.subgraphs = get_selected_metadata(self.struct_code, 'sub_graph_id')

        return self

    def get_metadata_network(self):
        """
        Gets nodes and edges of inputs and outputs. Will be used for network of inputs and outputs
        :return: self (values for nodes and edges)
        """

        def get_nodes():
            """
            Adds names of inputs and outputs. Uses list(set()) to remove duplicate node names
            :return: list of nodes
            """
            all_nodes = list(set(self.inputs+self.outputs))
            return all_nodes

        def get_edges():
            """
            Gets edges
            :return: list of edges where (A, B) is considered different from (B, A),
            excluding edges where A == B.
            """

            def get_sub_edges(input_list, output_list):
                """
                Return a list of unique directed pairs (inp, out) from input_list to output_list,
                excluding pairs where inp == out.
                """
                # Using dict.fromkeys(...) preserves insertion order and removes duplicates
                # but keeps the first occurrence.
                sub_edges = list(
                    dict.fromkeys(
                        (inp, out)
                        for inp in input_list
                        for out in output_list
                        if inp != out
                    )
                )
                return sub_edges

            edges = []
            for run in self.struct_code:
                edges.extend(get_sub_edges(run['inputs'], run['outputs']))

            return edges

        self.nodes = get_nodes()
        self.edges = get_edges()

        return self


if __name__ == '__main__':
    # Example usage
    sas_file_path = "../data/example.sas"  # Replace with your actual SAS file
    with open(sas_file_path, 'r', encoding='utf-8') as file:
        sas_script = file.read()

    struct_SAS = StructuredSAS(sas_script)
    struct_SAS = struct_SAS.clean_initial_code()
    struct_SAS = struct_SAS.parse_sas_script()
    struct_SAS = struct_SAS.merge_identity_runs()
    struct_SAS = struct_SAS.assign_subgraph_ids()
    struct_SAS = struct_SAS.get_metadata()
    struct_SAS = struct_SAS.get_metadata_network()
    struct_SAS.save_results()

    print("#############")






