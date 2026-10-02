from pathlib import Path
import hashlib
import os
import shutil
import zipfile


DOCX = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Cover_Letter_Computing.docx")
BACKUP = Path(r"C:\Users\admin\Desktop\Revon\.codex_tmp\cover_letter_before_humanize.docx")
TEMP = DOCX.with_suffix(".editing.docx")

REPLACEMENTS = {
    (
        "The manuscript also isolates the effect of hybrid diff selection through an ablation "
        "and reports the sensitivity of trie geometry to latency and storage objectives."
    ): (
        "The manuscript also uses an ablation to show the effect of hybrid diff selection and "
        "examines how trie geometry affects latency and storage."
    ),
    (
        "All authors have approved the manuscript and its submission. We confirm that the "
        "manuscript is original, has not been published previously, and is not under consideration "
        "by another journal. The source code, benchmark harness, and audited evidence are identified "
        "in the manuscript to support reproducibility."
    ): (
        "All authors have reviewed and approved the manuscript and agree to its submission. We "
        "confirm that the work is original, has not been published before, and is not currently "
        "under consideration by another journal. The manuscript identifies the source code, "
        "benchmark harness, and audited evidence used in the study so readers can reproduce the results."
    ),
    "Thank you for considering our manuscript.": "Thank you for your time and consideration.",
}


BACKUP.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(DOCX, BACKUP)

with zipfile.ZipFile(DOCX, "r") as source:
    members = [(info, source.read(info.filename)) for info in source.infolist()]

document_name = "word/document.xml"
original_by_name = {info.filename: data for info, data in members}
xml = original_by_name[document_name].decode("utf-8")

for old, new in REPLACEMENTS.items():
    count = xml.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one occurrence, found {count}: {old[:80]}")
    xml = xml.replace(old, new, 1)

updated_document = xml.encode("utf-8")

with zipfile.ZipFile(TEMP, "w") as output:
    for info, data in members:
        output.writestr(info, updated_document if info.filename == document_name else data)

with zipfile.ZipFile(TEMP, "r") as revised:
    revised_by_name = {info.filename: revised.read(info.filename) for info in revised.infolist()}

changed_non_document_parts = [
    name
    for name, data in original_by_name.items()
    if name != document_name and hashlib.sha256(data).digest() != hashlib.sha256(revised_by_name[name]).digest()
]
if changed_non_document_parts:
    raise RuntimeError(f"Unexpected changes outside document.xml: {changed_non_document_parts}")

os.replace(TEMP, DOCX)
print(f"Updated: {DOCX}")
print(f"Replacements: {len(REPLACEMENTS)}")
print("Changed non-document parts: 0")
