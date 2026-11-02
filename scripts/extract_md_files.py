import os


def extract_files_from_md(md_path):
    with open(md_path) as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("## File: "):
            file_path = line[9:].strip()
            i += 1
            if i < len(lines) and lines[i].strip().startswith("```"):
                code = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code.append(lines[i])
                    i += 1
                if i < len(lines):
                    # write to file
                    dir_path = os.path.dirname(file_path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                    with open(file_path, "w") as out:
                        out.writelines(code)
                    print(f"Extracted {file_path}")
        i += 1


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        extract_files_from_md(sys.argv[1])
    else:
        # process all .md
        for root, _dirs, files in os.walk("."):
            for file in files:
                if file.endswith(".md"):
                    md_path = os.path.join(root, file)
                    extract_files_from_md(md_path)
