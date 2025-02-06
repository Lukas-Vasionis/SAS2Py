
class StLink:
    def __init__(self, SAS_obj):
        self.SAS_obj = SAS_obj
        self.st_link_data = None

    def prepare_data(self):
        def struct_nodes():
            nodes_struct=[
                {"data": {"id": index + 1, "label": "VARIABLE", "name": node}}
                for index, node in enumerate(self.SAS_obj.nodes)
            ]
            return nodes_struct

        def struct_edges(nodes_structured):
            """
            Given a list of edges (tuples) and a list of node dictionaries of the form:
                {"data": {"id": <int>, "label": <str>, "name": <str>}}
            This function returns a list of edge dictionaries:
                {"data": {"id": <edge_index + 1>,
                          "label": None,
                          "source": <node_id_of_first_in_tuple>,
                          "target": <node_id_of_second_in_tuple>}}
            """
            # Create a map from node name -> node id for quick lookup
            node_map = {d["data"]["name"]: d["data"]["id"] for d in nodes_structured}

            # Build each edge dict using list comprehension
            edges_structured = [
                {
                    "data": {
                        "id": i + 1,
                        "label": "graph_edge",
                        "source": node_map[src],
                        "target": node_map[tgt],
                    }
                }
                for i, (src, tgt) in enumerate(self.SAS_obj.edges)
            ]
            return edges_structured

        nodes_struct=struct_nodes()
        edges_struct=struct_edges(nodes_struct)

        self.st_link_data={
            "nodes":nodes_struct,
            "edges":edges_struct
        }
        return self

