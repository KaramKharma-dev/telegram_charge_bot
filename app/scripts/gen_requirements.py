import os
import ast

# مكتبات بايثون الافتراضية (ما بدنا ياها بـ requirements.txt)
stdlib = {
    "os", "sys", "re", "math", "decimal", "datetime", "pathlib", "functools",
    "itertools", "subprocess", "threading", "asyncio", "json", "typing",
    "unittest", "http", "logging", "argparse", "shutil", "tempfile",
    "collections", "dataclasses", "contextlib", "time", "traceback",
    "enum", "copy", "pprint", "inspect", "uuid", "base64", "hashlib",
    "email", "queue", "statistics", "socket", "csv", "glob", "importlib",
    "types"
}

def find_imports_in_file(filepath):
    """يرجع أسماء المكتبات المستوردة من ملف واحد"""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports

def find_all_imports(root_dir="app"):
    """يمرّ على كل ملفات المشروع ويلقط المكتبات"""
    all_imports = set()
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                all_imports |= find_imports_in_file(os.path.join(subdir, file))
    return all_imports

if __name__ == "__main__":
    imports = find_all_imports("app")
    external_libs = sorted(i for i in imports if i not in stdlib and not i.startswith("app"))
    
    print("📦 المكتبات المستعملة بمشروعك:")
    for lib in external_libs:
        print(lib)

    # إنشاء requirements.txt
    with open("requirements.txt", "w", encoding="utf-8") as f:
        for lib in external_libs:
            f.write(lib + "\n")

    print("\n✅ تم إنشاء ملف requirements.txt")
