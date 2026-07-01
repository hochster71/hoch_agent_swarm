import os
import json
import math
import logging

logger = logging.getLogger("PertManager")

class PertManager:
    def __init__(self, data_file=None):
        if data_file is None:
            data_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "pert_tasks.json"))
        self.data_file = data_file
        self.tasks = {}
        self.load_tasks()

    def get_default_tasks(self):
        return {
            "T1": {
                "id": "T1",
                "name": "Requirements & Swarm Enclaves Setup",
                "optimistic": 2.0,
                "most_likely": 3.0,
                "pessimistic": 4.0,
                "predecessors": []
            },
            "T2": {
                "id": "T2",
                "name": "CDAO RAI Ethics Alignment Model Audit",
                "optimistic": 3.0,
                "most_likely": 5.0,
                "pessimistic": 7.0,
                "predecessors": ["T1"]
            },
            "T3": {
                "id": "T3",
                "name": "Secure API Development & ZTA Gateway",
                "optimistic": 4.0,
                "most_likely": 6.0,
                "pessimistic": 14.0,
                "predecessors": ["T1"]
            },
            "T4": {
                "id": "T4",
                "name": "Gordy Coding Container Agent Instantiation",
                "optimistic": 2.0,
                "most_likely": 4.0,
                "pessimistic": 6.0,
                "predecessors": ["T2"]
            },
            "T5": {
                "id": "T5",
                "name": "DoD ZTA Continuous Monitoring Audit Check",
                "optimistic": 3.0,
                "most_likely": 4.0,
                "pessimistic": 11.0,
                "predecessors": ["T3", "T4"]
            },
            "T6": {
                "id": "T6",
                "name": "Operator Approval & SWARM Dispatch",
                "optimistic": 1.0,
                "most_likely": 2.0,
                "pessimistic": 3.0,
                "predecessors": ["T5"]
            }
        }

    def load_tasks(self):
        if not os.path.exists(self.data_file):
            self.tasks = self.get_default_tasks()
            self.save_tasks()
            return

        try:
            with open(self.data_file, "r") as f:
                self.tasks = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load PERT tasks: {e}")
            self.tasks = self.get_default_tasks()

    def save_tasks(self):
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save PERT tasks: {e}")

    def reset_to_default(self):
        self.tasks = self.get_default_tasks()
        self.save_tasks()
        return self.calculate_pert()

    def add_or_update_task(self, task_data):
        task_id = task_data.get("id")
        if not task_id:
            raise ValueError("Task ID is required")

        # Basic validations
        optimistic = float(task_data.get("optimistic", 0))
        most_likely = float(task_data.get("most_likely", 0))
        pessimistic = float(task_data.get("pessimistic", 0))

        if not (optimistic <= most_likely <= pessimistic):
            raise ValueError("Time values must satisfy constraint: Optimistic <= Most Likely <= Pessimistic")

        preds = task_data.get("predecessors", [])
        # Check if predecessors exist
        for pred in preds:
            if pred not in self.tasks and pred != task_id:
                raise ValueError(f"Predecessor task '{pred}' does not exist.")

        # Temporarily save current state to detect cycles
        old_task = self.tasks.get(task_id)
        
        self.tasks[task_id] = {
            "id": task_id,
            "name": task_data.get("name", "Unnamed Task"),
            "optimistic": optimistic,
            "most_likely": most_likely,
            "pessimistic": pessimistic,
            "predecessors": preds
        }

        # Check for circular dependency cycle
        try:
            self.topological_sort()
        except ValueError as e:
            # Revert
            if old_task:
                self.tasks[task_id] = old_task
            else:
                del self.tasks[task_id]
            raise ValueError(f"Circular dependency cycle detected: {e}")

        self.save_tasks()
        return self.calculate_pert()

    def delete_task(self, task_id):
        if task_id not in self.tasks:
            return False, "Task not found"

        # Check if this task is a predecessor to any other task
        dependent_tasks = [tid for tid, t in self.tasks.items() if task_id in t.get("predecessors", [])]
        if dependent_tasks:
            raise ValueError(f"Cannot delete task '{task_id}' because it is a dependency for: {', '.join(dependent_tasks)}")

        del self.tasks[task_id]
        self.save_tasks()
        return True, self.calculate_pert()

    def topological_sort(self):
        # Kahn's algorithm or DFS topological sort
        in_degree = {tid: 0 for tid in self.tasks}
        adj = {tid: [] for tid in self.tasks}

        for tid, t in self.tasks.items():
            for p in t.get("predecessors", []):
                if p in adj:
                    adj[p].append(tid)
                    in_degree[tid] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.tasks):
            raise ValueError("Cycle detected in task dependencies.")
        
        return order

    def calculate_pert(self):
        if not self.tasks:
            return {
                "tasks": [],
                "critical_path": [],
                "expected_project_duration": 0.0,
                "project_variance": 0.0,
                "project_std_dev": 0.0
            }

        # Step 1: Compute topological order
        try:
            topo_order = self.topological_sort()
        except ValueError as e:
            return {"error": str(e)}

        # Step 2: Compute Expected Time (TE) and Variance for each task
        calculated_tasks = {}
        for tid, t in self.tasks.items():
            o = t["optimistic"]
            m = t["most_likely"]
            p = t["pessimistic"]
            
            te = (o + 4*m + p) / 6.0
            var = ((p - o) / 6.0) ** 2
            
            calculated_tasks[tid] = {
                "id": tid,
                "name": t["name"],
                "optimistic": o,
                "most_likely": m,
                "pessimistic": p,
                "predecessors": t["predecessors"],
                "te": round(te, 2),
                "variance": round(var, 3),
                "es": 0.0,
                "ef": 0.0,
                "ls": 0.0,
                "lf": 0.0,
                "slack": 0.0,
                "is_critical": False
            }

        # Step 3: Forward Pass (compute ES, EF)
        for tid in topo_order:
            task = calculated_tasks[tid]
            preds = task["predecessors"]
            if not preds:
                task["es"] = 0.0
            else:
                task["es"] = max(calculated_tasks[p]["ef"] for p in preds)
            task["ef"] = task["es"] + task["te"]

        # Project expected duration is the maximum EF value
        project_duration = max(calculated_tasks[tid]["ef"] for tid in topo_order)

        # Step 4: Backward Pass (compute LF, LS)
        # Find all nodes with no successors
        successors = {tid: [] for tid in calculated_tasks}
        for tid, task in calculated_tasks.items():
            for p in task["predecessors"]:
                if p in successors:
                    successors[p].append(tid)

        # Traverse reverse topological order
        for tid in reversed(topo_order):
            task = calculated_tasks[tid]
            s_list = successors[tid]
            if not s_list:
                task["lf"] = project_duration
            else:
                task["lf"] = min(calculated_tasks[s]["ls"] for s in s_list)
            task["ls"] = task["lf"] - task["te"]

            # Round values to float decimals to avoid IEEE float formatting issues
            task["es"] = round(task["es"], 2)
            task["ef"] = round(task["ef"], 2)
            task["ls"] = round(task["ls"], 2)
            task["lf"] = round(task["lf"], 2)
            
            slack = task["lf"] - task["ef"]
            task["slack"] = round(slack, 2)
            task["is_critical"] = (abs(task["slack"]) < 0.01)

        # Step 5: Identify Critical Path and calculate stats
        critical_path = [tid for tid in topo_order if calculated_tasks[tid]["is_critical"]]

        # Calculate project variance (sum of variances on the critical path)
        project_variance = sum(calculated_tasks[tid]["variance"] for tid in critical_path)
        project_std_dev = math.sqrt(project_variance)

        return {
            "tasks": list(calculated_tasks.values()),
            "critical_path": critical_path,
            "expected_project_duration": round(project_duration, 2),
            "project_variance": round(project_variance, 3),
            "project_std_dev": round(project_std_dev, 3)
        }
