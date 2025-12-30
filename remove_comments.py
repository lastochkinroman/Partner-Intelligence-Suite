import os
import re

def remove_comments(content):
    # Remove docstrings (triple quotes)
    content = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
    # Remove lines where the first non-whitespace is #
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('#'):
            continue  # Remove comment lines
        new_lines.append(line)
    return '\n'.join(new_lines)

for root, dirs, files in os.walk('business-intelligence-bot/app'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content = remove_comments(content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)

print("Comments removed from all Python files.")
