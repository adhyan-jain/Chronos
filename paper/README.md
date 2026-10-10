# Revon publication files

The current manuscript is **Revon Research Paper Springer**:

- [PDF](Revon%20Research%20Paper%20Springer.pdf) — the reference layout for submission.
- [DOCX](Revon%20Research%20Paper%20Springer.docx) — the editable companion. Word pagination differs from the PDF.
- [Reproducibility archive](Revon_Linux_Reproducibility_Supplement.zip) — source snapshots, protocols, manifests, raw observations, semantic verification and internal audits.

The manuscript links to the current [GitHub repository](https://github.com/atharvasheersh/Revon)
and the archive on `main`. It does not identify a fixed repository commit.
The executed source snapshots and collection manifests remain inside each evidence
bundle; updates to the repository do not replace those experiment records.
The ZIP is available on GitHub. Its presence here does not establish journal upload
or independent timing reproduction.

## Earlier versions

The [previous versions](previous%20versions/) directory retains the earlier
Discover Computing and IEEE DOCX/PDF exports. They are historical artifacts,
not the current submission. Their original model and evidence checks remain in
the publication gate. Older review sources are retained separately under
[`older versions/`](older%20versions/README.md).

## Validation and editing

From the repository root:

```bash
python -m pip install -r requirements-publication.txt
python -m unittest discover -s tools/tests -v
python tools/check_final_paper.py
```

These checks read the committed artifacts and recorded evidence. They do not
repeat the experiments or certify the paper's scientific conclusions, journal
eligibility, plagiarism status or AI-detector score. Exported manuscript changes
also require visual inspection. The manuscript still requires author review
before submission.

When revising the current paper, update its PDF and DOCX together. The archived
builders target earlier manuscript versions and must not overwrite this pair.
