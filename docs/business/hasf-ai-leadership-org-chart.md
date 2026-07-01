# HASF AI Leadership Org Chart

This document defines the reporting hierarchy and leadership structure for the AI-run business organization.

```mermaid
graph TD
    MH[Michael Hoch<br>Founder / Owner / Final Approval Authority]
    
    COO[AI Chief Operating Officer<br>HAS Commander]
    CFO[AI Chief Financial Officer<br>HASF Finance Manager]
    COS[AI Chief of Staff]
    
    TD[AI Technical Director]
    SO[AI Security & Compliance Officer]
    PO[AI Product Officer]
    GD[AI Growth & Launch Director]
    QA[AI QA & Release Authority]
    MOD[AI Mission Operations Director]
    
    MH --> COO
    MH --> CFO
    MH --> COS
    
    COO --> MOD
    COO --> TD
    COO --> PO
    
    CFO --> GD
    
    TD --> QA
    SO --> QA
    
    style MH fill:#003366,stroke:#33ccff,stroke-width:2px,color:#fff
    style COO fill:#1a3300,stroke:#39ff88,stroke-width:2px,color:#fff
    style CFO fill:#1a3300,stroke:#39ff88,stroke-width:2px,color:#fff
```

## 1. Executive Roles
- **Michael Hoch (Founder & Owner)**: Holds final veto, signing authority, and approval rights on all high-risk actions, pricing packages, and monetization code releases.
- **AI Chief Operating Officer (COO)**: Manages day-to-day pod orchestration, scheduling node matching, and overall operational execution.
- **AI Chief Financial Officer (CFO)**: Responsible for financial health, billing integrations, unit economics, and generating the Finance Operations Brief.
- **AI Chief of Staff (COS)**: Facilitates coordination between the COO and CFO, managing administrative queues and audit alignments.
