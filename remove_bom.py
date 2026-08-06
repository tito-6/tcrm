
import os
import codecs

def remove_bom(filepath):
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            
        if content.startswith(codecs.BOM_UTF8):
            print(f"Removing BOM from: {filepath}")
            with open(filepath, 'wb') as f:
                f.write(content[3:])
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return False

root_dir = r"c:\D\crm\tcrm-src"
count = 0
extensions = ('.xml', '.js', '.css', '.scss', '.html', '.py', '.csv', '.json')

for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file.lower().endswith(extensions):
            if remove_bom(os.path.join(root, file)):
                count += 1

print(f"Total files cleaned: {count}")
