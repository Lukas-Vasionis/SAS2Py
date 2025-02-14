import streamlit as st
import networkx as nx
from pyvis.network import Network
from collections import defaultdict, deque

def create_pyvis_force_layout(nodes, edges):
    """
    A force-directed layout using NetworkX's spring_layout
    (similar in spirit to Graphviz 'neato').
    """
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)


    # Force-directed layout in NetworkX
    pos = nx.spring_layout(G, seed=42)  # 'pos' = {node: (x, y), ...}

    net = Network(
        width="100%",
        height="600px",
        bgcolor="#222222",
        font_color="white",
        directed=True,
        # filter_menu=True

    )

    for node in G.nodes():
        x, y = pos[node]
        # Scale and flip Y (optional) so the graph isn't too small or upside-down
        net.add_node(
            str(node),
            x=float(x)*500,
            y=float(-y)*500,
            label=str(node),
            physics=False
        )

    for u, v in G.edges():
        net.add_edge(str(u), str(v))

    return net


def create_pyvis_hierarchical_layout(nodes, edges):
    """
    A BFS-based hierarchical layout (top -> down).
    This is somewhat similar to Graphviz 'dot' for DAGs.
    """
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # --- 1) Find BFS layers (assuming acyclic graph) ---
    in_degree_zero = [n for n in G.nodes() if G.in_degree(n) == 0]
    queue = deque(in_degree_zero)
    layer = 0
    node_levels = {}  # node -> integer level

    while queue:
        layer_size = len(queue)
        for _ in range(layer_size):
            node = queue.popleft()
            # Assign layer if not assigned
            if node not in node_levels:
                node_levels[node] = layer
            # Enqueue children
            for child in G.successors(node):
                if child not in node_levels:
                    queue.append(child)
        layer += 1

    # Group nodes by assigned layer
    level_dict = defaultdict(list)
    for n, lvl in node_levels.items():
        level_dict[lvl].append(n)

    # --- 2) Map each node to (x, y) ---
    pos = {}
    y_gap = 200.0
    x_gap = 150.0

    for lvl, nodes_in_level in level_dict.items():
        for i, n in enumerate(nodes_in_level):
            x = i * x_gap
            # Negative Y so it goes top -> bottom
            y = -lvl * y_gap
            pos[n] = (x, y)

    # --- 3) Create the PyVis Network (no physics) and add nodes/edges ---
    net = Network(
        width="100%",
        height="600px",
        bgcolor="#222222",
        font_color="white",
        directed=True,
        # filter_menu=True

    )

    for n in G.nodes():
        x, y = pos[n]
        net.add_node(
            str(n),
            x=float(x),
            y=float(y),
            label=str(n),
        )

    for u, v in G.edges():
        net.add_edge(str(u), str(v))

    return net


def create_pyvis_multipartite_layout(nodes, edges, layer_map):
    """
    Uses NetworkX's multipartite_layout which arranges nodes by 'subset' (layer).
    Similar to a layered approach. Provide each node's layer in 'layer_map'.
    """
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)

    # Attach the 'subset' attribute for multipartite_layout
    for n in G.nodes():
        G.nodes[n]['subset'] = layer_map.get(n, 0)

    # Layout: horizontal or vertical. (align='horizontal' by default => layers stacked vertically)
    pos = nx.multipartite_layout(G, subset_key="subset")

    net = Network(
        width="100%",
        height="600px",
        bgcolor="#222222",
        font_color="white",
        directed=True,
        # filter_menu=True
    )

    for node in G.nodes():
        x, y = pos[node]
        # Scale and flip Y
        net.add_node(
            str(node),
            x=float(x)*300,
            y=float(-y)*300,
            label=str(node),
            physics=False
        )

    for u, v in G.edges():
        net.add_edge(str(u), str(v))

    return net

def inject_js_for_node_cp(net):
    """
    Injects js script to add this feature: copy node name upon double click
    :param net: NetworkX net object
    :return: str, html of pyvis graph
    """

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
    return html_data.replace("</body>", f"{custom_script}\n</body>")

def main():
    st.title("PyVis Layout Examples (Without PyGraphviz)")

    st.write("""
    This demo shows three layout strategies:
    1. Force-directed (NetworkX's `spring_layout`)
    2. BFS-based hierarchical
    3. Multipartite layout
    """)

    # Sample data
    nodes = ["A", "B", "C", "D", "E", "F"]
    edges = [("A","B"), ("A","C"), ("B","D"), ("C","E"), ("D","F"), ("E","F")]


    layout_choice = st.selectbox(
        "Choose a layout:",
        ["Force-directed (spring_layout)", "BFS hierarchical", "Multipartite"]
    )

    if layout_choice == "Force-directed (spring_layout)":
        net = create_pyvis_force_layout(nodes, edges)
    elif layout_choice == "BFS hierarchical":
        net = create_pyvis_hierarchical_layout(nodes, edges)
    else:  # "Multipartite"
        # For multipartite layout, define which layer each node belongs to
        layer_map = {
            "A": 0,
            "B": 1,
            "C": 1,
            "D": 2,
            "E": 2,
            "F": 3
        }
        net = create_pyvis_multipartite_layout(nodes, edges, layer_map)

    # Generate HTML from PyVis
    html_str = net.generate_html()

    # Display in Streamlit via st.components.v1.html
    st.components.v1.html(html_str, height=650, scrolling=True)



if __name__ == "__main__":
    main()
