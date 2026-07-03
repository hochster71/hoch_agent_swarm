import json
import re

transcript_path = "/Users/michaelhoch/.gemini/antigravity-ide/brain/7f65b745-70f5-46eb-a19b-b8e52bc08b23/.system_generated/logs/transcript_full.jsonl"
output_path = "/Users/michaelhoch/.gemini/antigravity-ide/brain/7f65b745-70f5-46eb-a19b-b8e52bc08b23/scratch/v4_extracted.html"

with open(transcript_path, "r", encoding="utf-8") as f:
    first_line = f.readline()

try:
    data = json.loads(first_line)
    content = data.get("content", "")
    print(f"Content length: {len(content)} characters")
    
    # Let's find <!DOCTYPE html>
    start_idx = content.find("<!DOCTYPE html>")
    if start_idx != -1:
        # Let's find </html> from the end
        end_idx = content.rfind("</html>")
        if end_idx != -1:
            html_content = content[start_idx:end_idx + 7]
        else:
            print("Warning: </html> not found, writing from start to end of content")
            html_content = content[start_idx:]
            
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(html_content)
        print(f"Successfully extracted v4 HTML to: {output_path}")
        print(f"Size of extracted HTML: {len(html_content)} bytes")
    else:
        print("<!DOCTYPE html> not found in first line content.")
except Exception as e:
    print(f"Error: {e}")
