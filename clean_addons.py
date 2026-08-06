
import os
import codecs

root_dir = r"c:\D\crm\custom_addons"
extensions = ('.xml', '.js', '.css', '.scss', '.html', '.py', '.csv', '.json')

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

for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file.lower().endswith(extensions):
            remove_bom(os.path.join(root, file))
