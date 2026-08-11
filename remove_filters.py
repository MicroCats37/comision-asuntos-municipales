import os
import re

directory = "frontend/src/features/liquidaciones/views"

for filename in os.listdir(directory):
    if not filename.endswith(".tsx"):
        continue
    filepath = os.path.join(directory, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Remove state variables
    content = re.sub(r'[ \t]*const \[searchInput, setSearchInput\].*?\n', '', content)
    content = re.sub(r'[ \t]*const \[proyectoPublicId, setProyectoPublicId\].*?\n', '', content)
    
    # Also if the hook uses `proyectoPublicId` like: `useLiquidacionesEdificaciones({ page: 1, pageSize: 10, proyectoPublicId });`
    content = re.sub(r',\s*proyectoPublicId\s*}', ' }', content)
    content = re.sub(r',\s*proyectoPublicId\s*\)', ')', content)

    # 2. Remove handlers
    content = re.sub(r'[ \t]*const handleSearch = \(\) => \{.*?\};\n', '', content, flags=re.DOTALL)
    content = re.sub(r'[ \t]*const handleClearFilter = \(\) => \{.*?\};\n', '', content, flags=re.DOTALL)
    content = re.sub(r'[ \t]*const handleKeyDown = \(e: React\.KeyboardEvent\) => \{.*?\};\n', '', content, flags=re.DOTALL)

    # 3. Remove Filter Bar UI
    content = re.sub(r'[ \t]*\{\/\* Filter Bar \*\/\}.*?(?=[ \t]*\{\/\* (Cards|Table) View \*\/\})', '', content, flags=re.DOTALL)

    # 4. Remove imports (Search, X, Input)
    # Be careful not to break lucide-react import
    content = re.sub(r'\bSearch,\s*', '', content)
    content = re.sub(r',\s*Search\b', '', content)
    # If Search is alone
    content = re.sub(r'{\s*Search\s*}', '{}', content)
    
    content = re.sub(r'\bX,\s*', '', content)
    content = re.sub(r',\s*X\b', '', content)
    content = re.sub(r'{\s*X\s*}', '{}', content)

    # Clean up empty imports
    content = re.sub(r'import\s*{\s*}\s*from\s*["\']lucide-react["\'];\n?', '', content)

    # Clean Input
    content = re.sub(r'import\s*{\s*Input\s*}\s*from\s*["\']@/components/ui/input["\'];\n?', '', content)

    # write back
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Processed {filename}")
