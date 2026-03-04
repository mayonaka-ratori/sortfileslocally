import json
import os
import sys

def get_keys(data, prefix=""):
    keys = set()
    for k, v in data.items():
        if isinstance(v, dict):
            keys.update(get_keys(v, prefix + k + "."))
        else:
            keys.add(prefix + k)
    return keys

def check_i18n(base_lang="ja", languages=["en"]):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    messages_dir = os.path.join(project_root, "web", "messages")
    
    base_file = os.path.join(messages_dir, f"{base_lang}.json")
    if not os.path.exists(base_file):
        print(f"Error: Base language file {base_file} not found.")
        return False
        
    with open(base_file, 'r', encoding='utf-8') as f:
        base_data = json.load(f)
        
    base_keys = get_keys(base_data)
    all_pass = True
    
    for lang in languages:
        lang_file = os.path.join(messages_dir, f"{lang}.json")
        if not os.path.exists(lang_file):
            print(f"Error: Language file {lang_file} not found.")
            all_pass = False
            continue
            
        with open(lang_file, 'r', encoding='utf-8') as f:
            lang_data = json.load(f)
            
        lang_keys = get_keys(lang_data)
        
        missing_in_lang = base_keys - lang_keys
        extra_in_lang = lang_keys - base_keys
        
        if missing_in_lang:
            print(f"❌ Missing keys in {lang}.json:")
            for k in sorted(missing_in_lang):
                print(f"  - {k}")
            all_pass = False
            
        if extra_in_lang:
            print(f"⚠️ Extra keys in {lang}.json (not in {base_lang}.json):")
            for k in sorted(extra_in_lang):
                print(f"  - {k}")
            # Extra keys are just warnings, not failures for now
            
        if not missing_in_lang:
            print(f"✅ {lang}.json is complete (matches {base_lang}.json).")
            
    return all_pass

if __name__ == "__main__":
    if check_i18n():
        print("\nAll i18n checks passed!")
        sys.exit(0)
    else:
        print("\ni18n checks failed.")
        sys.exit(1)
