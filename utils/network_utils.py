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