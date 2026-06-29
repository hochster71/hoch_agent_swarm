#!/usr/bin/env python3
"""
ingest_public_feed.py

Fetches CISA cybersecurity advisories RSS feed from https://www.cisa.gov/cybersecurity-advisories/all.xml,
parses the XML to extract the advisory title, pubDate, description (cleaned of HTML tags), and URL,
and populates new rows in the SQLite database 'cybersecurity_diagrams.db' in 'PENDING' status.

Uses python built-ins only (urllib.request and xml.etree.ElementTree).
"""

import os
import sys
import re
import html
import json
import urllib.request
import xml.etree.ElementTree as ET
import email.utils
import sqlite3
from datetime import datetime

FEED_URL = "https://www.cisa.gov/cybersecurity-advisories/all.xml"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "cybersecurity_diagrams.db")

def clean_html(raw_html):
    """
    Decodes HTML entities and strips HTML tags from description text.
    """
    if not raw_html:
        return ""
    # Unescape HTML entities (e.g., &lt; -> <, &quot; -> ")
    txt = html.unescape(raw_html)
    # Strip HTML tags
    clean_tag = re.compile(r'<.*?>')
    cleantext = re.sub(clean_tag, '', txt)
    # Replace multiple spaces/newlines with a single space
    cleantext = re.sub(r'\s+', ' ', cleantext).strip()
    return cleantext

def parse_date(pub_date_str):
    """
    Parses RFC 2822 pubDate string and formats it for SQLite (YYYY-MM-DD HH:MM:SS).
    """
    if not pub_date_str:
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    try:
        dt = email.utils.parsedate_to_datetime(pub_date_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error parsing date '{pub_date_str}': {e}", file=sys.stderr)
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def main():
    print(f"Fetching CISA advisories RSS feed from: {FEED_URL}")
    req = urllib.request.Request(
        FEED_URL,
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Failed to fetch RSS feed: {e}", file=sys.stderr)
        sys.exit(1)
        
    print("Parsing feed XML...")
    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"Failed to parse XML: {e}", file=sys.stderr)
        sys.exit(1)
        
    items = root.findall('.//item')
    print(f"Found {len(items)} items in the feed.")
    
    if not items:
        print("No items to ingest.")
        return

    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file does not exist at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted_count = 0
    skipped_count = 0
    
    for item in items:
        title = item.findtext('title')
        link = item.findtext('link')
        raw_description = item.findtext('description')
        pub_date_str = item.findtext('pubDate')
        
        if not title or not link:
            continue
            
        title = title.strip()
        link = link.strip()
        description = clean_html(raw_description)
        created_at = parse_date(pub_date_str)
        
        # Check if the advisory already exists based on source (link)
        cursor.execute("SELECT 1 FROM diagrams WHERE source = ?", (link,))
        if cursor.fetchone():
            skipped_count += 1
            continue
            
        # JSON serialized lists as per schema
        components_json = json.dumps([])
        threat_vectors_json = json.dumps([description])
        
        # Insert a new row in 'PENDING' status
        cursor.execute("""
            INSERT INTO diagrams (
                title, source, description, architecture_type,
                components, threat_vectors, mitigations, created_at,
                status, analyzed_at, quality_score, artifact_links
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,               # title
            link,                # source
            description,         # description
            None,                # architecture_type
            components_json,     # components
            threat_vectors_json, # threat_vectors
            None,                # mitigations
            created_at,          # created_at
            'PENDING',           # status
            None,                # analyzed_at
            None,                # quality_score
            None                 # artifact_links
        ))
        inserted_count += 1
        
    conn.commit()
    conn.close()
    
    print(f"Success! Ingested {inserted_count} new advisories, skipped {skipped_count} existing ones.")

if __name__ == "__main__":
    main()
