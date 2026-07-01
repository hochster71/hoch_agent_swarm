# HOCH Agent Swarm Live Runtime Instrument Doctrine

## Principle
The active product is a live operational instrument, not a demo dashboard.
Every active UI component must be backed by runtime data and provide operational decision value.

## Allowed Active Component Criteria
A component may appear in active UI only if it has:
1. Live endpoint or stream source.
2. Last updated timestamp or freshness age.
3. Truth state: LIVE, DEGRADED, FAILED, EMPTY, ERROR, DISABLED, or APPROVAL_REQUIRED.
4. Operator decision value.
5. Contract or E2E test coverage proving live backing.

## Forbidden Active Content
- Demo swarm panels.
- Static cartoon rosters.
- Fake agent states.
- Fake CPU / RAM / IP / topology values.
- Fake health percentage.
- Fake asset counts.
- Fake terminal logs.
- Fake network latency.
- Static ConMon scorecards.
- YouTube research demo lanes.
- Canned workstream feeds.
- Catchphrase panels.
- Decorative-only animations.
- Static mission intelligence.
- Panels without source endpoint and freshness.

## Conversion Rule
If a component is useful:
convert it to live runtime.
If not useful:
delete it from active UI.
If needed for history:
move it under archive and label:
ARCHIVED / NOT LIVE / NOT USED FOR READINESS
Archive must not appear in active navigation.
