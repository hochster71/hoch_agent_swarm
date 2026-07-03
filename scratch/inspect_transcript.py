import json

transcript_path = "/Users/michaelhoch/.gemini/antigravity-ide/brain/7f65b745-70f5-46eb-a19b-b8e52bc08b23/.system_generated/logs/transcript_full.jsonl"

with open(transcript_path, "r") as f:
    for idx, line in enumerate(f):
        if idx >= 5:
            break
        try:
            data = json.loads(line)
            print(f"Line {idx}: source={data.get('source')}, type={data.get('type')}, keys={list(data.keys())}")
            content_preview = data.get('content', '')[:100].replace('\n', ' ')
            print(f"  content preview: {content_preview}")
        except Exception as e:
            print(f"Error line {idx}: {e}")
