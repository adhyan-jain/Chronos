# Revon manuscripts

Current title: **Adaptive Merkle Trie Versioning for Efficient Structured Data Management**.

The two authoritative outputs in the parent `paper/` directory have identical scientific content. This directory contains archived versions, compatibility copies, earlier review summaries and the reviewed starting source:

| Format | Editable source | Export |
| --- | --- | --- |
| Discover Computing | `Revon_Research_Paper_Discover_Computing.docx` | `Revon_Research_Paper_Discover_Computing.pdf` |
| IEEE two-column | `Revon_Research_Paper_IEEE.docx` | `Revon_Research_Paper_IEEE.pdf` |

`Revon_Final_Research_Paper`, `Revon_Research_Paper_Single_Column` and the pagination-fixed DOCX are archived compatibility copies. Current builds generate only the Discover Computing and IEEE manuscripts in the parent directory. Earlier BERT documents are archival and are not synchronized by this revision. Historical revision tools that refer to these former top-level names are not the current manuscript build pipeline.

The journal version follows the official Discover Computing Word guidance checked on 2 October 2026: a consistent Arial font of at least 12 pt, an abstract below 250 words, embedded figures/tables, Arabic figure/table numbering and numbered citations. The IEEE version uses Times New Roman, two-column body text and full-width displays. Both contain 31 cited references, 10 tables and 11 figures.

## Evidence and reproducibility

The original synthetic and TLC workflow studies retain their frozen 4,096-operation threshold. New held-out calibration selects 16,384 within the predefined candidate set. A separate long-history diagnostic is excluded from calibration; its non-monotonic medians do not establish a universal crossover. See `../../docs/experiments/THRESHOLD_VALIDATION.md` and `../../docs/experiments/PUBLIC_DATASET_EVALUATION.md`.

`sources/Revon_Reviewed_Public_Dataset_Manuscript.docx` preserves the reviewed starting manuscript, including the completed public-dataset extension (SHA-256 `22b8c68e42f2f305c1c43d095dbe719556ababa95c38722fed184c85d871b8d3`). It is an archival source, not the submission document. From the repository root, `python tools/revise_discover_manuscripts.py` builds the current DOCX files and figures from `paper/older versions/sources/Revon_Reviewed_Public_Dataset_Manuscript.docx` and audited evidence. It requires `requirements.txt`; public-reference downloading additionally requires `requests` and `beautifulsoup4`. Export the resulting DOCX files with Word or LibreOffice and inspect the rendered PDFs before replacing the final exports. `python tools/check_final_paper.py` checks the final artifacts and evidence without rerunning timings.

## Submission status

The final IEEE PDF was exported with Microsoft Word on Windows. The tested LibreOffice export left excess blank space at some continuous column changes. Run `powershell -File tools/export_ieee_word.ps1` from the repository root to produce a review export under `.codex_tmp/seven_revisions/render-ieee-word`; Microsoft Word must be installed. The Discover Computing manuscript and internal reports were exported with LibreOffice. Export pagination can differ between applications, so inspect a newly generated PDF before replacing the reviewed release.

**Further revision is required before journal submission.** Independent Linux hardware replication is blocked; WSL used the same physical computer. Funding, contributions, competing interests, applicable ethics and complete AI-use accountability require author confirmation. Public release of the new evidence is pending. General efficiency across structured-data management is not established, despite the requested title. Source-grounded originality review is not institutional plagiarism clearance.

The internal one-page review and detailed audit are under `output/docs/` and ignored by Git. No commits or push were made for this revision.
