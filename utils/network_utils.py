import networkx as nx
from pyvis.network import Network
import regex as re

def create_net_html_ins_outs(nodes, edges, physics, height):
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
    net.repulsion()
    html_data=net.generate_html()

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