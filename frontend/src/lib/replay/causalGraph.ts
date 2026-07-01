import type { AuditEvent } from "../audit/auditTypes";

export type CausalNode = {
  id: string;
  label: string;
  timestamp: string;
  type: string;
  result: string;
};

export type CausalLink = {
  source: string;
  target: string;
  relationType: string;
};

export type CausalGraphData = {
  nodes: CausalNode[];
  links: CausalLink[];
};

export function buildCausalGraph(events: AuditEvent[]): CausalGraphData {
  const nodes: CausalNode[] = events.map(e => ({
    id: e.event_id,
    label: e.action.type,
    timestamp: e.timestamp,
    type: e.target.type,
    result: e.result
  }));

  const links: CausalLink[] = [];
  
  // Link sequentially by timestamp
  for (let i = 0; i < events.length - 1; i++) {
    links.push({
      source: events[i].event_id,
      target: events[i+1].event_id,
      relationType: "sequence"
    });
  }

  // Link by matching correlation IDs
  for (let i = 0; i < events.length; i++) {
    for (let j = i + 1; j < events.length; j++) {
      if (events[i].correlation_id === events[j].correlation_id && events[i].correlation_id) {
        // Only link if not already sequentially linked
        if (j !== i + 1) {
          links.push({
            source: events[i].event_id,
            target: events[j].event_id,
            relationType: "correlation"
          });
        }
      }
    }
  }

  return { nodes, links };
}
