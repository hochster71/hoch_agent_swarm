# HAS/HASF local Kubernetes Sidecar Runtime

This directory contains the Kubernetes manifests to run the HAS/HASF worker mesh as an isolated sidecar execution fabric inside a local `k3d` Kubernetes cluster.

## Architecture

```mermaid
graph TD
    subgraph Host macOS (Authoritative Baseline)
        Tracker["Tracker (:3001)"]
        API["HAS API (:8000)"]
        RegistryDB["registry.sqlite"]
        EventsFile["events.ndjson"]
    end

    subgraph k3d Cluster (Sidecar Runtime)
        subgraph has-workers Namespace
            Heartbeat["agent-heartbeat (Deployment)"]
            BatchA["batch-a-inventory (Job)"]
            Registry["registry-build (Job)"]
            Dora["dora-event (CronJob)"]
            Evidence["evidence-pack (CronJob)"]
            Scan["devsecops-scan (CronJob)"]
            Snapshot["snapshot (CronJob)"]
        end
        PV["Persistent Volume (Data Mount)"]
    end

    PV <--> RegistryDB
    PV <--> EventsFile
    Heartbeat -- Emit Events --> EventsFile
    BatchA -- Emit Events --> EventsFile
    Registry -- Emit Events --> EventsFile
    Dora -- Emit Events --> EventsFile
    Evidence -- Emit Events --> EventsFile
    Scan -- Emit Events --> EventsFile
    Snapshot -- Emit Events --> EventsFile
```

- **Autoritative Source**: The host filesystem (`has_live_project_tracker/data`) remains the sole authority.
- **Sidecar Isolation**: All workers run as containerized pods in the `has-workers` namespace.
- **Shared Storage**: A PersistentVolume mapping `/tracker-data` is mounted to expose the database and events log.
- **Safe Writer Pattern**: Individual jobs write outputs to `outbox/`. Only the registry builder promotions are serialized. Multiple workers never write directly to the database file.

## Manifest Layout

- `k3d-cluster.yaml`: Configures the multi-node `k3d` cluster (1 server, 2 agent nodes) with host path mounts.
- `namespace.yaml`: Declares `has-workers` namespace.
- `resource-quotas.yaml`: Places resource quotas on the namespace (max 4 CPUs, 8 GB RAM).
- `configmap.yaml`: Exposes basic configuration parameters.
- `pvc.yaml`: Declares the PersistentVolumeClaim mapped to the host directory.
- `rbac.yaml`: Service accounts and permissions.
- `jobs/`: Run-once inventory and registry compilation steps.
- `cronjobs/`: Background DORA, scans, evidence collecting, and database snapshots.
- `deployments/`: Long-running agent heartbeat probes.

## Running the Sidecar Runtime

Use the bootstrap scripts in `scripts/` to control the runtime:
- Create & start the cluster: `./scripts/k8s_sidecar_bootstrap.sh`
- Query cluster status: `./scripts/k8s_sidecar_status.sh`
- Trigger inventory job: `./scripts/k8s_sidecar_run_batch_a.sh`
- Pause/Stop the sidecar: `./scripts/k8s_sidecar_stop.sh`
- Destroy the cluster: `./scripts/k8s_sidecar_destroy.sh`
