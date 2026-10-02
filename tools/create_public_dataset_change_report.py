"""Create a complete change record for the completed Comment 1 revision."""
from pathlib import Path
import csv
import hashlib
import json
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'evidence/public-tlc-combined-20261002'
OUTPUT = ROOT / 'output/pdf/Revon_Comment_1_Complete_Change_Report.pdf'
NAVY = colors.HexColor('#17354B')
TEAL = colors.HexColor('#007D83')
GRAY = colors.HexColor('#52616B')
PALE = colors.HexColor('#F0F5F7')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle', fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=NAVY, spaceAfter=16))
styles.add(ParagraphStyle(name='SectionTitle', fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=NAVY, spaceAfter=12))
styles.add(ParagraphStyle(name='Subhead', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=TEAL, spaceBefore=10, spaceAfter=5, keepWithNext=True))
styles.add(ParagraphStyle(name='ReportBody', fontName='Helvetica', fontSize=9.5, leading=13.3, textColor=NAVY, spaceAfter=7))
styles.add(ParagraphStyle(name='SmallText', fontName='Helvetica', fontSize=8, leading=10.8, textColor=GRAY, spaceAfter=5))
styles.add(ParagraphStyle(name='CellText', fontName='Helvetica', fontSize=8, leading=10.5, textColor=NAVY))
styles.add(ParagraphStyle(name='CellHead', fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=colors.white))
styles.add(ParagraphStyle(name='CodeText', fontName='Courier', fontSize=7.5, leading=10.3, textColor=NAVY, spaceAfter=7, wordWrap='CJK'))


def p(text, style='ReportBody'):
    return Paragraph(text, styles[style])


def plain(text, style='ReportBody'):
    return p(escape(str(text)), style)


def bullets(items):
    return [p('<b>' + escape(title) + '.</b> ' + escape(detail)) for title, detail in items]


def grid(headers, rows, widths):
    data = [[plain(x, 'CellHead') for x in headers]]
    data += [[plain(x, 'CellText') for x in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, 0), .6, NAVY),
        ('LINEBELOW', (0, -1), (-1, -1), .5, colors.HexColor('#CFD9DF')),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(colors.HexColor('#CFD9DF'))
    canvas.line(42, h - 37, w - 42, h - 37)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(42, h - 29, 'REVON | COMMENT 1 CHANGE RECORD')
    canvas.drawString(42, 26, '2 October 2026 | Public dataset and larger-scale evaluation')
    canvas.drawRightString(w - 42, 26, str(doc.page))
    canvas.restoreState()


def build():
    audit = json.loads((BUNDLE / 'evidence_audit.json').read_text())
    qa = json.loads((BUNDLE / 'paper_verification.json').read_text())
    source_qa = json.loads((BUNDLE / 'independent_source_verification.json').read_text())
    manifest = json.loads((BUNDLE / 'manifest.json').read_text())
    with (BUNDLE / 'summary.csv').open(newline='') as f:
        lookup = {(r['scenario'], r['model']): r for r in csv.DictReader(f)}
    assert audit['passed'] and qa['passed'] and source_qa['passed'] and qa['visual_review']['passed']
    for item in qa['manuscripts']:
        assert hashlib.sha256(Path(item['pdf']).read_bytes()).hexdigest() == item['pdf_sha256'], 'Manuscript PDF changed since QA'
    flow = []
    def title(n, text):
        if flow:
            flow.append(PageBreak())
        flow.extend([p(f'{n:02d} / {text}', 'SectionTitle')])
    def sub(text):
        flow.append(plain(text, 'Subhead'))
    def body(text):
        flow.append(plain(text))

    flow.extend([p('Revon<br/>Complete change report', 'ReportTitle'),
        p('Comment 1: Add a public dataset and larger-scale evaluation', 'Subhead'),
        plain('Prepared on 2 October 2026. This records the completed Comment 1 work and its supporting implementation, evidence and manuscript changes. It is not a record of every revision since the first rejection, nor a declaration that all supervisor comments are resolved.'),
        Spacer(1, 12)])
    flow.append(grid(['What changed', 'Why it matters'], [
        ('Public structured records', 'Added 1,000,000 retained NYC TLC records with eleven original fields, instead of relying solely on synthetic payloads.'),
        ('Larger and separate sweeps', 'Measured scale, history length and update density through six workloads and six workflows.'),
        ('Reproducible evidence', 'Retained acquisition checksums, raw attempts, exact execution source, verification hashes and audited summaries.'),
        ('Bounded paper claims', 'Reported the achieved scale, generated histories and unfavorable commit/storage results explicitly.'),
        ('Four synchronized manuscripts', 'Updated IEEE, final, single-column and BERT Word/PDF variants, including new tables and a three-panel figure.'),
        ('Verification and layout repairs', 'Checked source records, semantic outputs, paper values and 49 rendered pages; removed the duplicate BERT abstract and repaired table pagination.'),
    ], [150, 361]))
    sub('Completion and actual outcome')
    body(f"The study retained {audit['executions']} attempts: 72 successful warm-ups, 252 successful measured executions and one interrupted failed attempt. A fresh recovery supplied the seventh valid Revon-M measurement at one million records. All 36 configurations have seven valid measured trials.")
    body('The new evidence strengthens dataset coverage, but reveals substantial costs. At one million records, Revon-H commits are slower than Snapshot, Log-only and both Dolt workflows, and its directory footprint is about 10.90 times Dolt SQL. These findings are included in the paper.')
    body('Scope status: the requested Comment 1 measurements and integration are complete. The other seven supervisor comments remain outside this work.')

    title(2, 'Dataset acquisition and adapter')
    sub('Dataset choice and suitability')
    body('January 2024 NYC TLC yellow-taxi trip records are freely downloadable Parquet records with several meaningful typed fields. The source contains 2,964,624 rows; the frozen study retains exactly 1,000,000. A record maps naturally to a key and a canonical structured JSON value in Revon.')
    flow.append(p('Authoritative source: <link href="https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page" color="#007D83">NYC TLC Trip Record Data</link>', 'SmallText'))
    flow.append(plain('Download: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet', 'CodeText'))
    flow.append(plain('SHA-256: ' + manifest['dataset']['download_sha256'], 'CodeText'))
    flow.append(plain('Prepared JSONL SHA-256: ' + manifest['dataset']['prepared_sha256'], 'CodeText'))
    sub('Fields, identity and preprocessing')
    flow += bullets([
        ('Eleven retained fields', 'VendorID; tpep_pickup_datetime; tpep_dropoff_datetime; passenger_count; trip_distance; PULocationID; DOLocationID; payment_type; fare_amount; tip_amount; total_amount.'),
        ('Deterministic keys', 'Month + first 16 source-checksum hex digits + zero-based physical row ordinal. Identical field contents remain separate rows. Keys identify rows within this frozen release, not natural trip IDs or cross-release identities.'),
        ('Canonical serialization', 'Compact sorted-key UTF-8 JSON; source timestamps use timezone-free ISO text. Missing and nonfinite values become JSON null. Domain anomalies such as negative fares remain in the records.'),
        ('Missing and malformed values', '47,277 retained passenger counts are null; no other retained field is null. All selected records serialize successfully. The checks verify storage mapping, not validity of taxi activity.'),
        ('Nested sampling', 'Seed 20261001; ordinal = (996110 + rank * 1344731) mod 2964624. Prefixes of 10k, 100k and 1M ranks form nested subsets. This dispersed affine permutation is not a uniformly random permutation.'),
        ('Usage and redistribution', 'Authoritative provenance and applicable NYC terms are documented; no invented Creative Commons license is asserted. Raw Parquet and prepared JSONL are local downloads excluded from Git.'),
    ])
    sub('Generated version histories')
    body('Monthly trip files contain different trips, so they are not treated as successive versions of the same records. Each generated commit selects a distinct seeded set of existing keys, increases fare and total by 0.01 and rounds those fields to two decimal places. Other fields stay unchanged; keys may repeat across commits. These are synthetic correction histories over public records.')

    title(3, 'Experimental matrix and protocol')
    rows = []
    for s in manifest['workloads']:
        rows.append((f"{s['rows']:,}", str(s['commits']), f"{s['changes_per_commit']:,}", f"{100*s['changes_per_commit']/s['rows']:.2g}%", f"1 to {s['commits']+1}"))
    flow.append(grid(['Initial records', 'Commits', 'Changes/commit', 'Density', 'Diff endpoints'], rows, [112, 72, 123, 76, 128]))
    sub('Systems and fixed configuration')
    body('Snapshot, Log-only, forced-Merkle Revon-M, hybrid Revon-H, Dolt SQL import and Dolt CSV import. The two Dolt workflows use the same engine for subsequent operations. Existing adapters and output contracts are reused. Trie b=8, d=4 and the 4,096-operation selector remain fixed.')
    sub('Measurement changes')
    flow += bullets([
        ('Pilot before the matrix', 'Small and scale pilots established feasibility. Their timings are excluded from the repeated performance evidence.'),
        ('Isolated repeated trials', 'Two warm-ups and seven measured trials per configuration, with recorded counterbalanced execution order. The overlapping 100k baseline is executed once.'),
        ('Timing boundaries', 'Initial import ends at the first durable state. Each trial reports the median of H incremental commit intervals. Diff and checkout include canonical output materialization; setup, oracle checks and cleanup are outside operation latency.'),
        ('Correctness coverage', 'Every successful trial checks initial/final states and semantic diff. The first measured trial per system/configuration checks every historical version outside timing. Per-trial reports retain observed and oracle hashes, changed-key counts and commit intervals.'),
        ('Storage and resources', 'Whole repository directory measured before close or compaction. Process-tree sampling runs externally every 10 ms; worker RSS includes workload/oracle state. Public payload_bytes is null because record values have variable size.'),
    ])
    sub('Interruption, recovery and environment')
    body('The original million-record Revon-M measured trial 5 lost its worker during an interrupted run. Its error, wall duration and abnormal commit intervals remain preserved; no usable timing was recovered or imputed. One fresh measured recovery used the same frozen source and workload, without additional warm-up. It ran after the matrix, outside the original counterbalanced block.')
    body('Public evaluation: Python 3.12.14, Dolt 2.3.1, pyarrow 25.0.1, psutil 7.2.2; Windows 11, 12 logical CPUs, 15.64 GiB visible RAM and 4.14 GiB available at launch. Available memory was not held constant. Earlier synthetic evidence used Python 3.14.3 and also includes WSL2 on the same physical computer.')
    body('A 900-second worker wall-clock resource limit covers setup and verification as well as operations. The interrupted attempt does not establish an algorithmic or memory scale limit.')

    title(4, 'Measured findings added to the paper')
    body('One million initial records, ten generated commits and 1,000 changed records per commit. Values are median [25th percentile, 75th percentile] across seven valid measured trials. Commit and diff are in milliseconds; footprint is in MiB.')
    model_names = [('Snapshot','Snapshot'), ('Log-only','Log-only'), ('Revon-M (forced Merkle)','Revon-M'), ('Revon-H','Revon-H'), ('Dolt','Dolt SQL'), ('Dolt (bulk import)','Dolt CSV')]
    def fmt(r, metric, divisor=1):
        return f"{float(r[metric+'_median'])/divisor:.2f}\n[{float(r[metric+'_p25'])/divisor:.2f}, {float(r[metric+'_p75'])/divisor:.2f}]"
    results = []
    for model, label in model_names:
        r = lookup[('tlc-n1000000-h10-c1000', model)]
        results.append((label, fmt(r,'initial_import_ms'), fmt(r,'incremental_commit_ms'), fmt(r,'diff_ms'), fmt(r,'storage_bytes',2**20)))
    flow.append(grid(['Workflow', 'Import ms', 'Commit ms', 'Diff ms', 'Footprint MiB'], results, [87, 106, 106, 106, 106]))
    sub('What the results support')
    flow += bullets([
        ('Commit cost', 'Revon-H has a 4,764.26 ms median commit, compared with 1,175.64 ms for Dolt SQL, 937.17 ms for Dolt CSV and 10.84 ms for Log-only. Snapshot also has a lower commit median at this scale.'),
        ('Diff tradeoff', 'Revon-H has a 651.01 ms median diff, below both Dolt workflows and Snapshot, but above Log-only at 148.16 ms. This is a workflow comparison and does not isolate tree algorithms.'),
        ('Storage weakness', 'Revon-H occupies 1,446.69 MiB, versus 132.76 MiB for Dolt SQL: a 10.90 ratio of median directory footprints. Serialization, indexes and compression are included; this is not pure metadata overhead.'),
        ('Selector change', 'Revon-H uses log diff at 10k/100k records and Merkle diff at 1M. The scale curve combines increased state size with a policy change. The 100k, 50-commit and 1%-density cases also cross the frozen threshold.'),
        ('Uncertainty', 'IQRs describe repeated fixed workloads on one host. They are not confidence intervals over datasets or machines. No failed observation is extrapolated and no threshold is retuned to improve results.'),
    ])
    body('Figure 7 adds three labeled panels for record count versus commit latency, diff latency and repository footprint, with medians and IQRs. Table V adds the 100k history/density medians. Complete results for all 36 configurations, including import, checkout and uncertainty, remain in summary.csv and PUBLIC_DATASET_RESULTS.md.')

    title(5, 'Manuscript changes and output files')
    changes = [
        ('Abstract', 'Added the measured public-data scale of one million records and generated-history qualifier; scoped the earlier latency ratios to synthetic experiments.'),
        ('Related Work', 'Replaced the obsolete statement excluding public-dataset evidence with the actual one-release/generated-history boundary.'),
        ('Methodology D / 4.4', 'Added provenance, schema, preprocessing, key/value mapping, sampling, correction rules, N/H/C sweeps, repetitions, timing boundaries and environment.'),
        ('Dataset Table III', 'Added source citation, original/retained counts, eleven-field mapping, identity construction, scale/history/density settings and generated histories.'),
        ('Results E / 5.5', 'Added measured import, commit, diff and footprint results, IQR interpretation, failed-attempt retention and the recovery deviation.'),
        ('Figure 7 and Table V', 'Added the three-panel scale plot and compact history/density results. Original diff Table III became Table IV; cross-references follow the new order.'),
        ('Discussion', 'Added unfavorable commit/storage costs, public contents versus generated histories, fixed-depth leaf occupancy and the selector change in the scale sweep.'),
        ('Limitations / future / conclusion', 'Removed obsolete no-public-data/no-million-record exclusions after successful runs; retained dataset diversity, observed history, host, memory and untested-feature limits.'),
        ('References / data availability', 'Added authoritative TLC reference 31 in numbered variants and (NYC TLC, 2024) in BERT, with acquisition/preparation/evaluation instructions and evidence paths.'),
        ('Formatting corrections', 'Sized new assets to each column, prevented inherited exact-line-height clipping, kept figures/captions paired, removed duplicate BERT abstract and kept its existing tables/captions together.'),
    ]
    flow.append(grid(['Location', 'Change and reason'], changes, [145, 366]))
    sub('Synchronized deliverables (repository-relative paths)')
    for item in qa['manuscripts']:
        flow.append(plain(str(Path(item['docx']).relative_to(ROOT)).replace('\\','/'), 'CodeText'))
        flow.append(plain(str(Path(item['pdf']).relative_to(ROOT)).replace('\\','/') + f"  ({item['pages']} pages)", 'CodeText'))
    body('Approved title preserved: Revon: Git-Inspired Merkle Hash Trie Versioning for Structured Data. Author text, the original thirty references and six approved image assets are preserved. Existing formatting conventions remain in the four variants; this task does not convert the manuscript to a Springer template.')

    title(6, 'Implementation and repository changes')
    inventory = [
        ('experiments/public_dataset.py', 'New checksum-pinned Parquet preparation, deterministic nested subsets, canonical record values and seeded corrections. Lazy historical-state reconstruction avoids holding H full-state copies.'),
        ('experiments/public_dataset_study.py', 'New isolated study runner, pilots, recorded counterbalanced order, identical-settings resume, manifests, raw trials, verification, archived execution source, source-change guard and audit.'),
        ('experiments/final_benchmark.py', 'Added public-workload dispatch, optional per-trial verification reports, state/diff hashes, all-history versus endpoint verification and resource timeout. Released decoded endpoint copies before large history checks.'),
        ('Timeout/failure handling', 'After execution finished, hardened cleanup against vanished workers and exit races; failed worker reports are quarantined automatically. Exact earlier execution code remains archived. Successful timing logic was not changed by this repair.'),
        ('tests/test_public_dataset.py', 'New preparation/schema/null fixtures, nested subset checks, repeatable mutation histories and lazy-state correctness checks.'),
        ('tests/test_experiment_harness.py', 'Added a regression for a worker that exits before timeout cleanup, preserving the resource error rather than masking it with a missing-process error.'),
        ('Dataset dependencies', 'Added pyarrow 25.0.1 to requirements.txt. New experiments/requirements-public-dataset.txt pins pyarrow 25.0.1 and psutil 7.2.2 used by the public study. Pre-existing plot/render pins were preserved.'),
        ('.gitignore / .gitattributes', 'Ignored data/public/ and .codex_tmp/; preserved exact evidence file bytes under evidence/public-tlc-*/ so line-ending conversion cannot invalidate hashes.'),
        ('tools/check_final_paper.py', 'Finds the original results table by shape/header instead of a fixed index; validates contiguous linked references while supporting the new 31st entry.'),
    ]
    flow.append(grid(['File or area', 'Implementation change'], inventory, [169, 342]))
    sub('New analysis and publication tools')
    flow += bullets([
        ('tools/combine_public_dataset_evidence.py', 'Validates the original/recovery inputs and creates the pooled analysis with run-ID uniqueness, retained failure, seven valid trials per configuration and independently recomputed medians/IQRs.'),
        ('tools/verify_public_dataset_source.py', 'Independently traces source records and replays mutations, checking workload digests and retained state/diff hashes.'),
        ('tools/integrate_public_dataset_paper.py', 'Builds the new figure/tables and synchronized targeted text additions from audited evidence, preserving original backups.'),
        ('tools/verify_public_dataset_paper.py', 'Checks new values, citations, original image bytes, abstract claims, caption pairing and table pagination; renders the PDFs for inspection.'),
        ('tools/report_public_dataset_results.py', 'Creates the detailed results, findings, change list and reproduction report from retained evidence.'),
    ])

    title(7, 'Evidence, validation and remaining limits')
    evidence_rows = [
        ('public-tlc-pilot-20261001', 'Small pilot; six successful resource-estimate runs, excluded from performance summaries.'),
        ('public-tlc-scale-pilot-20261001', 'Scale pilot; twelve successful resource-estimate runs, excluded from performance summaries.'),
        ('public-tlc-evaluation-20261001', 'Original 324 attempts: 323 successful and one interrupted failed attempt. Retains frozen source, trial verification, source provenance and interruption record.'),
        ('public-tlc-recovery-20261002', 'One fresh successful million-record Revon-M measured execution under the same frozen source/workload.'),
        ('public-tlc-combined-20261002', 'Pooled 325-attempt analysis, 324 successful executions, summary.csv, raw CSV/JSONL, elapsed records, manifests, plots and verification reports.'),
    ]
    body('The following directories are under evidence/. Original evidence bundles remain preserved; pilot results are not pooled with the repeated study.')
    flow.append(grid(['New evidence directory', 'Contents and role'], evidence_rows, [220, 291]))
    sub('Checks completed')
    flow += bullets([
        ('Code regression', 'Sixteen targeted tests passed, including actual Dolt-backed checks and the vanished-worker cleanup case.'),
        ('Source and semantics', 'All 1,000,000 prepared rows traced to Parquet; schema, null counts, deterministic keys/subsets and workload digests checked independently. Successful state checks total 1,221 hash comparisons; semantic diff outputs agree with the oracle.'),
        ('Statistics and paper values', 'Audits reproduce summaries and reject incorrect/duplicate rows. All 54 plotted point inputs and 72 new table values match retained evidence; numerical narrative and imports match summaries.'),
        ('Document verification', 'All 49 final PDF pages were manually inspected after Word export and 144 dpi rendering: IEEE 10, final 10, single-column 16, BERT 13. New figures/captions and complete tables are paired, with readable labels. References and original image assets passed checks.'),
        ('Existing evidence disclosures', 'Final manuscript validator also passed the retained 405-row Windows telemetry audit, including 315 measured rows and 31 linked references.'),
    ])
    sub('Reproduction and documentation')
    body('docs/experiments/PUBLIC_DATASET_EVALUATION.md documents download, checksums, schema, updates, protocol, acquisition and run commands. docs/experiments/PUBLIC_DATASET_RESULTS.md contains all configuration results and changes. The pooled manifest points to exact archived execution sources; a fresh uninterrupted matrix needs no recovery/pooling step.')
    flow.append(plain('Verification records: evidence_audit.json, independent_source_verification.json and paper_verification.json in evidence/public-tlc-combined-20261002/. Repository root: C:/Users/admin/Desktop/Revon', 'SmallText'))
    sub('Remaining limitations and closure')
    body('One monthly file, one affine sample/seed, generated update-only histories and one physical host remain the boundaries. Available RAM varied, paging costs were not isolated, and recovery ran outside the original balanced block. No observed revision histories, relational queries, multiple tables, schema evolution, concurrency, independent hardware or scale beyond one million records were evaluated.')
    body('The requested Comment 1 evidence and manuscript integration are complete. These limitations remain explicit. Other review comments and overall publication readiness require separate work. All Comment 1 changes are local; no new commit or push was made in that task.')

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=55, bottomMargin=47,
        title='Revon - Comment 1 Complete Change Report', author='Revon project', subject='Public dataset, larger-scale experiments and manuscript revision record')
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(OUTPUT)
    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    for expected in ('1,000,000', '325', '252', '1,221', '54', '72', '49', '4,764.26', '10.90', 'PUBLIC_DATASET_RESULTS.md', 'BERT'):
        assert expected in text, expected
    assert len(reader.pages) == 7, f'Unexpected overflow: {len(reader.pages)} pages'
    print(json.dumps({'output': str(OUTPUT), 'pages': len(reader.pages), 'text_checks': 'passed', 'sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    build()
