"""
Phase 22: Graph-Based Knowledge Engine (GBrain)
Replaces flat FTS5 with a Graph architecture using strict context-tagging.
"""
from typing import List, Dict, Any, Optional
import networkx as nx
from datetime import datetime

class GraphKnowledgeEngine:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self._initialize_graph()

    def _initialize_graph(self):
        """Initialize the graph structure."""
        # This replaces legacy FTS5 with structural graph representations.
        pass

    def insert_memory(self, memory_id: str, content: str, context_tags: Dict[str, Any]):
        """
        Insert memory into the graph using strict context-tagging.
        Context tags should include 'time', 'project', and 'entities'.
        """
        time_tag = context_tags.get("time", datetime.now().isoformat())
        project_tag = context_tags.get("project", "default")
        entities = context_tags.get("entities", [])

        # Add node for memory
        self.graph.add_node(memory_id, type="memory", content=content, time=time_tag, project=project_tag)

        # Create structural relational pathways
        for entity in entities:
            self.graph.add_node(entity, type="entity")
            self.graph.add_edge(entity, memory_id, relation="MENTIONED_IN")
            self.graph.add_edge(memory_id, entity, relation="MENTIONS")
            
        self.graph.add_node(project_tag, type="project")
        self.graph.add_edge(project_tag, memory_id, relation="CONTAINS_MEMORY")
        
    def recall_memory(self, query: str, context_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Recall memories by traversing relational pathways based on context tags.
        """
        context_filters = context_filters or {}
        project_filter = context_filters.get("project")
        entity_filter = context_filters.get("entities", [])
        
        results = []
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "memory":
                # Strict context tagging filters
                if project_filter and data.get("project") != project_filter:
                    continue
                
                # If specific entities are queried, traverse relational pathways to check
                if entity_filter:
                    has_all_entities = True
                    for entity in entity_filter:
                        if not self.graph.has_edge(node, entity):
                            has_all_entities = False
                            break
                    if not has_all_entities:
                        continue
                        
                results.append({"id": node, "content": data.get("content"), "time": data.get("time")})
                
        return results

    def trace_path(self, start_entity: str, end_entity: str) -> List[str]:
        """
        Graph architecture allowing agents to traverse relational pathways.
        Example: Who calls what.
        """
        try:
            path = nx.shortest_path(self.graph, source=start_entity, target=end_entity)
            return path
        except nx.NetworkXNoPath:
            return []
        except nx.NodeNotFound:
            return []
