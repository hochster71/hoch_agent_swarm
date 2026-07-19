from __future__ import annotations
from typing import Dict, List, Set

class CircularEvidenceDetector:
    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}

    def add_node(self, node: str):
        if node not in self.graph:
            self.graph[node] = set()

    def add_edge(self, u: str, v: str):
        """Adds a directed dependency edge: u depends on v."""
        self.add_node(u)
        self.add_node(v)
        self.graph[u].add(v)

    def detect_cycles(self) -> List[List[str]]:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles: List[List[str]] = []

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle, extract sub-path from first occurrence of neighbor
                    try:
                        idx = path.index(neighbor)
                        cycle = path[idx:] + [neighbor]
                        cycles.append(cycle)
                    except ValueError:
                        pass

            path.pop()
            rec_stack.remove(node)

        for start_node in list(self.graph.keys()):
            if start_node not in visited:
                dfs(start_node, [])

        return cycles
