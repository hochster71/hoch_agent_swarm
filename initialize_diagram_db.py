import sqlite3
import json
import os

DB_PATH = "cybersecurity_diagrams.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the cybersecurity diagrams table with additional metadata fields
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagrams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            description TEXT,
            architecture_type TEXT,
            components TEXT,
            threat_vectors TEXT,
            mitigations TEXT,
            status TEXT DEFAULT 'PENDING',
            analyzed_at TIMESTAMP,
            quality_score REAL,
            artifact_links TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if migration is needed for existing databases
    cursor.execute("PRAGMA table_info(diagrams)")
    columns = [row[1] for row in cursor.fetchall()]
    
    new_cols = {
        "status": "TEXT DEFAULT 'PENDING'",
        "analyzed_at": "TIMESTAMP",
        "quality_score": "REAL",
        "artifact_links": "TEXT"
    }
    
    for col, col_def in new_cols.items():
        if col not in columns:
            cursor.execute(f"ALTER TABLE diagrams ADD COLUMN {col} {col_def}")
            print(f"Added column {col} to diagrams table via migration.")
            
    # Pre-populate with typical cybersecurity reference diagrams
    mock_data = [
        {
            "title": "Three-Tier AWS Web Architecture with VPC peering",
            "source": "Reference Library",
            "description": "Standard cloud web application deployment with public, private app, and isolated database subnets.",
            "architecture_type": "Cloud Network Architecture",
            "components": json.dumps(["Application Load Balancer", "Auto Scaling Group (EC2)", "RDS Database Multi-AZ", "VPC Peering Connection", "IGW", "NAT Gateway"]),
            "threat_vectors": json.dumps([
                "VPC peering route misconfigurations routing private traffic over public routes",
                "Unrestricted RDS security groups allowing port 3306/5432 ingress from the entire VPC",
                "Lack of ingress encryption (HTTPS termination) at the load balancer level",
                "Bastion host exposed directly to 0.0.0.0/0 on SSH port 22"
            ]),
            "mitigations": json.dumps([
                "Implement least-privilege security groups targeting only the Application tier security group",
                "Enforce HTTPS-only traffic at ALB and configure ACM SSL certificates",
                "Migrate Bastion to AWS Systems Manager (SSM) Session Manager to disable public SSH access",
                "Strictly define VPC route tables to isolate peered subnet traffic and avoid routing loops"
            ])
        },
        {
            "title": "Zero Trust Identity and Access Management Flow",
            "source": "Enterprise Reference Architecture",
            "description": "User authentication and resource access flow leveraging identity providers (IDP) and policy enforcement points.",
            "architecture_type": "Identity & Access Control",
            "components": json.dumps(["Identity Provider (Okta)", "Multi-Factor Authentication (MFA)", "Policy Enforcement Point (PEP)", "Policy Decision Point (PDP)", "Enterprise Resources"]),
            "threat_vectors": json.dumps([
                "Session hijacking via token reuse or lack of IP binding",
                "Bypass of Multi-Factor Authentication via MFA fatigue attacks",
                "Weak PEP logic allowing unauthorized direct endpoint access",
                "Over-privileged role permissions violating least-privilege principles"
            ]),
            "mitigations": json.dumps([
                "Implement risk-based adaptive MFA and phishing-resistant FIDO2 keys",
                "Enforce continuous token validation at PEP with short session expirations",
                "Perform regular automated identity audits and implement role-based access controls (RBAC)",
                "Bind authentication tokens to TLS client certificates or user IP addresses"
            ])
        },
        {
            "title": "Kubernetes Cluster Ingress and Microservice Network Policies",
            "source": "DevSecOps Patterns",
            "description": "Microservice communication layout mapping frontend, backend API, and database pods with cluster ingress controllers.",
            "architecture_type": "Container & Orchestration Security",
            "components": json.dumps(["NGINX Ingress Controller", "Frontend Pods", "Backend API Pods", "Redis Cache Pod", "Kubernetes NetworkPolicies"]),
            "threat_vectors": json.dumps([
                "Default-allow cluster networking permitting compromised frontend pods to access all namespaces",
                "Ingress controller running as root with access to host namespaces",
                "Cleartext transmission of sensitive data between internal microservices",
                "Lack of resource limits leading to denial-of-service via resource exhaustion"
            ]),
            "mitigations": json.dumps([
                "Apply default-deny NetworkPolicies at the namespace level and explicitly whitelist connections",
                "Run Ingress Controller under rootless security contexts",
                "Implement mutual TLS (mTLS) using a service mesh like Istio or Linkerd",
                "Define CPU and memory requests and limits for all container manifests"
            ])
        }
    ]
    
    # Check if we already have records
    cursor.execute("SELECT COUNT(*) FROM diagrams")
    count = cursor.fetchone()[0]
    
    if count == 0:
        for row in mock_data:
            cursor.execute("""
                INSERT INTO diagrams (title, source, description, architecture_type, components, threat_vectors, mitigations)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (row["title"], row["source"], row["description"], row["architecture_type"], row["components"], row["threat_vectors"], row["mitigations"]))
        print(f"Pre-populated database with {len(mock_data)} security architecture diagrams.")
    else:
        print("Database already contains data. Skipping pre-population.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
