import sys
import re
from html.parser import HTMLParser

class SimpleHTMLAnalyzer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.title = None
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        id_val = attrs_dict.get("id")
        class_val = attrs_dict.get("class", "")
        
        if tag == "title":
            self.in_title = True
            
        if id_val or any(x in class_val for x in ["panel", "container", "theater", "dashboard"]):
            self.elements.append((tag, id_val, class_val))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title = data

def analyze(filepath, label):
    print(f"\n=== Analyzing {label} ({filepath}) ===")
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
    except Exception as e:
        print(f"Error opening file: {e}")
        return
    
    if "truncated" in html.lower():
        print("WARNING: File contains truncation placeholder!")
        
    parser = SimpleHTMLAnalyzer()
    parser.feed(html)
    
    print("Title:", parser.title)
    print(f"Total elements: {len(parser.elements)}")
    print("Top 25 elements:")
    for tag_name, id_val, class_val in parser.elements[:25]:
        print(f"  <{tag_name} id='{id_val}' class='{class_val}'>")

analyze("/Users/michaelhoch/.gemini/antigravity-ide/brain/7f65b745-70f5-46eb-a19b-b8e52bc08b23/scratch/user_request_extracted.html", "V4 Snippet")
analyze("has_live_project_tracker/ui/hoch_pods_liftoff.html", "V6 Theater")
