# prepare.py — LaTeX article submission helper

A single-file Python script that gets your LaTeX article folder ready for journal submission or blind review (e.g. Elsevier / elsarticle). Perfect if you like keeping your project clean with folders and subfolders—and don’t feel like giving up that civilized way of life just because Editorial Manager force you to.
## Features

| | `submission` | `review` |
|---|:---:|:---:|
| Flatten `\includegraphics` paths | ✅ | ✅ |
| Copy images flat into output folder | ✅ | ✅ |
| Copy `.bib`, `.cls`, `.sty` files | ✅ | ✅ |
| Anonymise `\author`, `\ead`, `\address` | | ✅ |
| Clear configurable sections | | ✅ |
| Redact keywords with ▮ blocks | | ✅ |

## Requirements

Python 3.6+ — no external dependencies (stdlib only).

## Usage

```bash
python prepare.py <source_folder> review|submission
```

**Examples:**
```bash
python prepare.py ./my_article review      # blind review → my_article_review_ready/
python prepare.py ./my_article submission  # final submission → my_article_submission_ready/
```

The output folder is created **inside** the source folder and overwritten on each run.

## What it does

### Both modes — flattening

All `\includegraphics` references with subdirectory paths are flattened:

```latex
% Before
\includegraphics[width=\linewidth]{figures/results/speed.pdf}

% After
\includegraphics[width=\linewidth]{speed.pdf}
```

The image files are located recursively in the source folder and copied flat into the output folder. Name conflicts are resolved automatically with a numeric suffix.

Support files (`.bib`, `.cls`, `.sty`) at the source root are copied as-is.

### Review mode — anonymisation

**Authors & emails**
```latex
% Before
\author[unil]{Jane Doe}
\ead{jane.doe@university.ch}

% After
\author[institution]{Author 1}
\ead{author1@anonymous.com}
```

**Addresses** — all `\address` entries are collapsed into one:
```latex
\address[institution]{Anonymous Institution}
```

**Sections** — configured sections have their body replaced by a comment while preserving the `\section{}` header and any `\label{}`:
```latex
% Before
\section*{Acknowledgements}\label{sec:ack}
We thank our colleagues...

% After
\section*{Acknowledgements}\label{sec:ack}
% Acknowledgements have been removed for blind review.
```

**Keyword redaction** — each configured keyword is replaced by a block of `▮` characters with a randomised length (±5 chars, minimum 1).

## Configuration

All options live at the top of `prepare.py`:

```python
# Sections to clear (body replaced, header & \label preserved)
SECTIONS_TO_CLEAR = [
    {
        "pattern": r"Acknowledge",   # matched case-insensitively inside \section{...}
        "body": "% Acknowledgements have been removed for blind review.",
        "label": "Acknowledgements", # used in log messages only
    },
    {
        "pattern": r"Credit authorship",
        "body": "% Author contributions have been removed for blind review.",
        "label": "Credit authorship contribution statement",
    },
    # Add more sections as needed
]

# Keywords to redact with ▮ blocks
REDACT_KEYWORDS = [
    # "My University",
    # "Jane Doe",
]
```

## Output structure

```
my_article/
├── main.tex
├── references.bib
├── figures/
│   └── results/
│       └── speed.pdf
└── my_article_review_ready/   ← output (flat)
    ├── main.tex
    ├── references.bib
    └── speed.pdf
```
