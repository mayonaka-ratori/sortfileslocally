import os
import re

def analyze_logs():
    log_files = ["error.log", "diag_output.log"]
    found_errors = []
    
    for log in log_files:
        if not os.path.exists(log): continue
        
        with open(log, "r", encoding="utf-8") as f:
            content = f.read()
            # Basic regex to find paths associated with errors
            matches = re.findall(r"(?:Failed to process|Error at)\s+([^\s\n]+)", content)
            found_errors.extend(matches)
            
    if not found_errors:
        print("✅ No pipeline errors found in logs.")
    else:
        print(f"🚨 Identified {len(found_errors)} problematic files:")
        for path in set(found_errors):
            print(f"- {path}")

if __name__ == "__main__":
    analyze_logs()
