#!/usr/bin/env python3
"""
prepare.py — Prepare a LaTeX article folder for Elseiver submission or review.

Usage:
    python prepare.py <source_folder> review      # anonymise + flatten
    python prepare.py <source_folder> submission  # flatten only

Produces: <source_folder>/<basename>_review_ready/
       or <source_folder>/<basename>_submission_ready/
"""

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

# Sections to clear in review mode.
# Each entry: (title_pattern, replacement_header, label)
# title_pattern is matched case-insensitively against the text inside \section{...}
SECTIONS_TO_CLEAR = [
    {
        "pattern": r"Acknowledge",
        "body": """% Acknowledgements have been partly removed for blind review.""",
        "label": "Acknowledgements",
    },
    {
        "pattern": r"Credit authorship",
        "body": """% Author contributions have been removed for blind review.""",
        "label": "Credit authorship contribution statement",
    },
]

# Keywords to redact in review mode.
# Each occurrence is replaced by a run of ▮ characters whose length is
# len(keyword) + random offset in [-5, +5], with a minimum of 1.
REDACT_KEYWORDS = [
    # "My University",
    # "John Doe",
]

# ─────────────────────────────────────────────

import glob
import os
import random
import re
import shutil
import sys

REDACT_CHAR = "▮"


def anonymise_authors(content):
    """Replace \\author[inst]{name} with \\author[institution]{Author X}."""
    author_counter = [0]

    def replace_author(m):
        author_counter[0] += 1
        return f"\\author[institution]{{Author {author_counter[0]}}}"

    content = re.sub(r"\\author\[[^\]]*\]\{(?:[^{}]|\{[^}]*\})*\}", replace_author, content)
    return content, author_counter[0]


def anonymise_eads(content, num_authors):
    """Replace \\ead{email} with \\ead{authorX@anonymous.com}."""
    ead_counter = [0]

    def replace_ead(m):
        ead_counter[0] += 1
        idx = min(ead_counter[0], num_authors)
        return f"\\ead{{author{idx}@anonymous.com}}"

    content = re.sub(r"\\ead\{[^}]*\}", replace_ead, content)
    return content


def anonymise_addresses(content):
    """Replace all \\address[...]{...} with a single anonymous address."""
    address_counter = [0]

    def replace_address(m):
        address_counter[0] += 1
        if address_counter[0] == 1:
            return "\\address[institution]{Anonymous Institution}"
        return ""

    content = re.sub(r"\\address\[[^\]]*\]\{[^}]*\}", replace_address, content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


def clear_section(content, section_config):
    """
    Clear the body of a section while preserving its \\section{} header and any \\label{}.
    Replaces body up to the next \\section or \\end{document}.
    """
    title_pattern = section_config["pattern"]
    new_body = section_config["body"]
    label = section_config["label"]

    pattern = re.compile(
        r"(\\section\*?\{" + title_pattern + r"[^}]*\})"  # group 1: original \section{...}
        r"(\s*\\label\{[^}]*\})?"                          # group 2: optional \label{...}
        r".*?(?=\\section|\\end\{document\})",             # body to replace
        re.DOTALL | re.IGNORECASE,
    )

    def replacer(m):
        header = m.group(1)
        tex_label = m.group(2) or ""
        return f"{header}{tex_label}\n{new_body}\n"

    new_content, count = pattern.subn(replacer, content)
    if count == 0:
        print(f"  [info] No '{label}' section found.")
    return new_content


def clear_configured_sections(content):
    """Clear all sections listed in SECTIONS_TO_CLEAR."""
    for section in SECTIONS_TO_CLEAR:
        content = clear_section(content, section)
    return content


def redact_keywords(content):
    """Replace each keyword in REDACT_KEYWORDS with a run of ▮ characters."""
    for keyword in REDACT_KEYWORDS:
        if not keyword:
            continue
        length = max(1, len(keyword) + random.randint(-5, 5))
        replacement = REDACT_CHAR * length

        def make_replacer(r):
            return lambda m: r

        content = re.sub(re.escape(keyword), make_replacer(replacement), content, flags=re.IGNORECASE)
        print(f"  [redact] '{keyword}' → {replacement}")
    return content


def flatten_graphics(content, source_folder, images_to_copy):
    """
    Replace \\includegraphics paths that contain subdirectories with bare filenames.
    Schedules found files for copying into images_to_copy dict {dest_name: src_path}.
    Returns updated content.
    """

    def replace_graphic(m):
        options = m.group(1) or ""
        path = m.group(2)

        if "/" not in path and "\\" not in path:
            return m.group(0)

        filename = os.path.basename(path)

        matches = glob.glob(
            os.path.join(source_folder, "**", filename), recursive=True
        )
        matches = [p for p in matches if "_review_ready" not in p and "_submission_ready" not in p]

        if not matches:
            print(f"  [warn] Could not find '{filename}' — path left unchanged.")
            return m.group(0)

        src_path = matches[0]

        dest_name = filename
        if dest_name in images_to_copy and images_to_copy[dest_name] != src_path:
            stem, ext = os.path.splitext(filename)
            counter = 2
            while True:
                candidate = f"{stem}_{counter}{ext}"
                if candidate not in images_to_copy:
                    print(f"  [warn] Filename conflict: '{filename}' renamed to '{candidate}'")
                    dest_name = candidate
                    break
                counter += 1

        images_to_copy[dest_name] = src_path
        return f"\\includegraphics{options}{{{dest_name}}}"

    pattern = re.compile(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}")
    return pattern.sub(replace_graphic, content)


def process_tex_file(tex_path, source_folder, images_to_copy, mode):
    """Process a single .tex file according to mode. Returns modified content."""
    with open(tex_path, encoding="utf-8") as f:
        content = f.read()

    print(f"  Processing {os.path.basename(tex_path)} ...")

    if mode == "review":
        content, num_authors = anonymise_authors(content)
        content = anonymise_eads(content, num_authors)
        content = anonymise_addresses(content)
        content = clear_configured_sections(content)
        content = redact_keywords(content)

    content = flatten_graphics(content, source_folder, images_to_copy)
    return content


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("review", "submission"):
        print("Usage: python prepare.py <source_folder> review|submission")
        sys.exit(1)

    source_folder = os.path.abspath(sys.argv[1])
    mode = sys.argv[2]

    if not os.path.isdir(source_folder):
        print(f"Error: '{source_folder}' is not a directory.")
        sys.exit(1)

    basename = os.path.basename(source_folder.rstrip("/"))
    output_folder = os.path.join(source_folder, f"{basename}_{mode}_ready")

    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    print(f"Mode   : {mode}")
    print(f"Source : {source_folder}")
    print(f"Output : {output_folder}")
    print()

    tex_files = glob.glob(os.path.join(source_folder, "*.tex"))
    if not tex_files:
        print("[warn] No .tex files found at the root of the source folder.")

    images_to_copy = {}

    for tex_path in tex_files:
        new_content = process_tex_file(tex_path, source_folder, images_to_copy, mode)
        dest = os.path.join(output_folder, os.path.basename(tex_path))
        with open(dest, "w", encoding="utf-8") as f:
            f.write(new_content)

    print()
    print("Copying images ...")
    for dest_name, src_path in images_to_copy.items():
        shutil.copy2(src_path, os.path.join(output_folder, dest_name))
        print(f"  {src_path}  →  {dest_name}")

    print()
    print("Copying support files ...")
    for ext in ("*.bib", "*.cls", "*.sty"):
        for src_path in glob.glob(os.path.join(source_folder, ext)):
            dest = os.path.join(output_folder, os.path.basename(src_path))
            shutil.copy2(src_path, dest)
            print(f"  {os.path.basename(src_path)}")

    print()
    print("Done.")
    print(f"Output folder: {output_folder}")


if __name__ == "__main__":
    main()
