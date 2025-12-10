import os

IGNORE_FOLDERS = {
    "__pycache__",
    "venv",
    ".venv",
    ".git",
    ".idea",
    ".vscode",
    "env",
    "node_modules"
}

IGNORE_FILES = {
    ".env",
    ".gitignore"
}

def generate_tree(root, indent=""):
    result = ""
    entries = sorted(os.listdir(root))

    for index, entry in enumerate(entries):
        path = os.path.join(root, entry)

        # Skip ignored folders/files
        if entry in IGNORE_FOLDERS or entry in IGNORE_FILES:
            continue

        # Skip hidden system files like .DS_Store
        if entry.startswith(".") and entry not in IGNORE_FILES:
            continue

        connector = "├── " if index < len(entries) - 1 else "└── "
        result += f"{indent}{connector}{entry}\n"

        if os.path.isdir(path):
            extension = "│   " if index < len(entries) - 1 else "    "
            result += generate_tree(path, indent + extension)

    return result


root_dir = "."  # Your project directory
output = generate_tree(root_dir)

with open("structure.md", "w", encoding="utf-8") as f:
    f.write("```\n" + output + "```")

print("Generated structure.md (clean version)")
