"""Render an explicitly non-institutional AI/similarity review for Revon."""
from pathlib import Path
from html import escape
import hashlib,json,re,shutil
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/pdf/revon-integrity-review-20261008'
OUT=ROOT/'output/pdf/Revon_AI_and_Similarity_Review.pdf'
INK=colors.HexColor('#182C3B');TEAL=colors.HexColor('#006D77')
GRAY=colors.HexColor('#526471');LIGHT=colors.HexColor('#EDF3F5')
AMBER=colors.HexColor('#9A5C0B');LINE=colors.HexColor('#D7E1E6')
for name,filename in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf'),('Arial-Italic','ariali.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/filename)))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
S=getSampleStyleSheet()
for name,size,leading,color in [('Body',10,14.3,INK),('Small',8.5,11.5,GRAY),('H1',23,27,INK),
    ('H2',15,20,INK),('H3',11,15,TEAL),('Label',8.6,12,TEAL),('Quote',10.4,15.3,INK)]:
    S.add(ParagraphStyle(name,fontName='Arial-Bold' if name in ['H1','H2','H3','Label'] else 'Arial',
        fontSize=size,leading=leading,textColor=color,spaceAfter=7))
W=507
story=[]
def p(text,style='Body'):
    return Paragraph(text,S[style])
def add(text,style='Body'):story.append(p(text,style))
def gap(h=8):story.append(Spacer(1,h))
def heading(k,title):
    add(k,'Label');add(title,'H1');gap(8)
def box(title,text,color=TEAL):
    t=Table([[p(title,'H3')],[p(text)]],colWidths=[W-24])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),.6,LINE),
        ('LINEBEFORE',(0,0),(0,-1),3,color),('LEFTPADDING',(0,0),(-1,-1),12),
        ('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,0),10),
        ('BOTTOMPADDING',(0,-1),(-1,-1),11)]))
    story.append(t);gap(11)
def table(headers,rows,widths,font=9.2,padding=5):
    st=ParagraphStyle('cell',parent=S['Body'],fontSize=font,leading=font+3,spaceAfter=0)
    data=[[Paragraph('<b>'+escape(str(x))+'</b>',st) for x in headers]]+[[Paragraph(escape(str(x)),st) for x in r] for r in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LINEBELOW',(0,0),(-1,0),.7,TEAL),('LINEBELOW',(0,1),(-1,-1),.35,LINE),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding)]))
    story.append(t);gap(9)
def link(url,label):return f'<link href="{escape(url,quote=True)}" color="#006D77">{escape(label)}</link>'
def page():story.append(PageBreak())

def main():
    r=json.loads((DATA/'screening.json').read_text(encoding='utf-8'))
    assert len(r['matches']['6'])==3 and len(r['matches']['8'])==2
    heading('REVON / MANUSCRIPT INTEGRITY REVIEW','Similarity and AI-Assistance Review')
    add('<b>INTERNAL REVIEW - NOT A TURNITIN REPORT</b>','Label')
    add('Adaptive Merkle Trie Versioning for Efficient Structured Data Management','H2')
    add('Discover Computing version | 22 manuscript pages | Report dated 9 October 2026','Small')
    gap(8)
    table(['Assessment','Recorded result'],[
        ['Turnitin similarity percentage','Not available - Turnitin was not accessed'],
        ['AI-writing detector percentage','Not measured - no classifier was run'],
        ['Exact phrase screen','3 short maximal matches at >=6 normalized tokens'],
        ['Source coverage','29 searchable cited-source texts; 2 coverage gaps'],
        ['AI assistance','Confirmed from the project work history; extent not quantified'],
    ],[185,W-185],10)
    gap(6)
    box('Similarity finding',
        'The three flagged runs are cited technical terminology, a numeric size list and standard declaration wording. '
        'No unattributed substantive copying was identified among these runs. This is a bounded observation, not a finding that the entire paper is plagiarism-free.')
    box('AI-assistance finding',
        'AI assistance was used for experimental scripts, evidence analysis, manuscript drafting and figure-generation code. '
        'The final document cannot honestly be certified as AI-free. No percentage of AI-authored text is inferred.',AMBER)
    add('Scope at a glance','H3')
    add(f"{r['screened_paragraphs']} abstract/body paragraphs and {r['screened_tokens']:,} normalized tokens were compared with "
        f"{r['source_tokens']:,} searchable source tokens. The 31-entry bibliography was checked for citation presence. "
        'An exact phrase match is a review prompt, not proof of plagiarism.')
    add('Prepared by OpenAI Codex for author review. No institutional certification, submission receipt, examiner signature or external service score is represented.','Small')

    page();heading('01 / MATCH REVIEW','Three short overlaps')
    add('Locations refer to the final 22-page Discover Computing PDF. The six-token and eight-token results overlap; they are not five independent findings.','Small')
    gap(6)
    box('Match 1 - cited taxonomy | manuscript p. 3 | source [10]',
        '<b>Matched wording:</b> version-first, tuple-first, and hybrid<br/><br/>'
        '<b>Context:</b> the related-work paragraph describes Decibel and places citation [10] immediately after its layout summary. '
        'The six normalized tokens are established names of layouts, rather than an unattributed explanatory passage.<br/><br/>'
        '<b>Assessment:</b> attributed technical terminology. Retain accurate citation; no cosmetic rewrite is required.')
    add(link('https://www.vldb.org/pvldb/vol9/p624-maddox.pdf','Source: Maddox et al., Decibel, PVLDB 2016'),'Small')
    gap(6)
    box('Match 2 - number list | manuscript p. 9 | source [29]',
        '<b>Matched wording:</b> 10,000, 100,000 and 1,000,000<br/><br/>'
        '<b>Context:</b> Revon describes prepared TLC subset sizes. Git4Data lists update-set sizes. '
        'Those are different experimental quantities. Splitting commas makes this list eight alphanumeric tokens.<br/><br/>'
        '<b>Assessment:</b> coincident round numbers, not distinctive borrowed prose. The Revon sizes must be supported by its own dataset records, as they are in the manuscript.')
    add(link('https://arxiv.org/abs/2609.02106','Source: Gou et al., Git4Data, 2026 preprint'),'Small')
    gap(6)
    box('Match 3 - declaration | manuscript p. 19 | source [27]',
        '<b>Matched wording:</b> Competing interests: The authors declare no competing interests.<br/><br/>'
        '<b>Context:</b> an eight-token match to standard declaration wording on a Scientific Data article page.<br/><br/>'
        '<b>Assessment:</b> conventional disclosure language. Its truth is the authors\' responsibility. '
        'No citation to another paper is needed simply to use the standard declaration.')
    add(link('https://www.nature.com/articles/s41597-024-03153-y','Source: Gonzalez-Cebrian et al., Scientific Data 2024'),'Small')

    page();heading('02 / SCOPE AND METHOD','What was actually checked')
    add('Input and exclusions','H3')
    add('The final Discover Computing DOCX was checked against the manuscript model, and match locations were mapped to its PDF. '
        'Screening includes the abstract and body paragraphs, including declarations. It excludes the title, author block, keywords, headings, '
        'bibliography, table cells, captions and text within figures. Quoted prose was not automatically excluded.')
    add('Reproducible exact-text screen','H3')
    add('Text was normalized with Unicode NFKC, lowercased and split into ASCII alphanumeric tokens. URLs and bracketed numeric citations were removed. '
        'Runs cannot cross manuscript paragraphs. All maximal contiguous matches of at least six tokens were listed; an eight-token threshold was also checked. '
        'Overlapping windows were collapsed, and no stemming, fuzzy matching or semantic plagiarism classifier was applied.')
    table(['Threshold','Maximal runs','Manual classification'],[
        ['>=6 normalized tokens','3','Cited taxonomy; numbers; standard declaration'],
        ['>=8 normalized tokens','2','The same number-list and declaration matches'],
    ],[135,90,W-225])
    add('Corpus coverage','H3')
    add('The retained public-source texts were acquired on 2 October 2026 and screened anew against this final revision. '
        'Twenty-nine texts have usable content. Source [4], Merkle\'s scanned PDF, has no usable extracted text. '
        'Source [17], scientific-array versioning, has only metadata/abstract text after full-text access failed. '
        'Neither is counted as a screened full source. The source inventory appears on page 5.')
    add('Citation-presence check','H3')
    add('The manuscript contains 31 bibliography entries, and each reference number [1]-[31] appears in the screened prose. '
        'This establishes linkage, not that every cited proposition has been independently verified or every citation is necessary. '
        'Bibliography strings were excluded from overlap counts to avoid mistaking paper titles for copied prose.')
    box('What this cannot determine',
        'The screen cannot find unattributed paraphrases or ideas reliably, compare with private student repositories, inspect every paywalled source, '
        'judge figure reuse or establish authorship. PDF extraction artifacts can hide similarities. Short matches below six tokens are omitted. '
        'No overall similarity percentage, plagiarism clearance or universal originality claim follows.',AMBER)
    add('Turnitin itself distinguishes text similarity from a plagiarism decision. Its database and algorithms were not used here; these local counts cannot be translated into a Turnitin percentage. See official guidance on page 6.','Small')

    page();heading('03 / AI ASSISTANCE','Known use, without a detector score')
    add('Basis of assessment','H3')
    add('This section uses the visible project work history, not stylistic guesses. The assistant helped write experimental and audit scripts, '
        'summarize evidence, revise manuscript prose and generate plotting code. It also helped format and check the documents. '
        'These facts establish AI assistance; they do not identify a measurable percentage of AI-authored sentences.')
    table(['Work area','Observed assistance','Required author oversight'],[
        ['Experiments and evidence','Script generation, audits and result summaries','Check protocols, raw outputs and every scientific conclusion'],
        ['Manuscript prose','Drafting and revision support','Read and approve wording, attribution and limitations'],
        ['Figures and formatting','Plotting code and document layout','Verify plotted values, captions and legibility'],
        ['This report','Automated phrase screen and interpretation','Treat as an internal aid, not independent certification'],
    ],[103,192,W-295],9.5)
    add('Detector status','H3')
    add('No AI-writing detector was run. No predicted Turnitin AI score or human-authorship percentage is supplied. '
        'The absence of a text match does not demonstrate human authorship. Turnitin states that its AI report is separate from similarity '
        'and may misidentify both human and AI text; its output should not be the sole basis for adverse action.')
    add('Journal disclosure remains pending','H3')
    add('Discover\'s current AI policy requires oversight, verification and disclosure for evaluative or interpretive assistance, including '
        'suggested analytical approaches and extensive writing support. The work in this revision falls within that description. '
        'The manuscript currently omits an AI-use declaration pending the author\'s decision. Institutional rules may impose additional requirements.')
    box('Suggested declaration - approve only after author review',
        'AI tools (OpenAI Codex) assisted experimental scripting, evidence analysis, figure-generation code and manuscript drafting. '
        'The authors reviewed the outputs and remain responsible for the work.',AMBER)
    add('The second sentence must be true before it is used. This report does not certify that all authors have reviewed the final Linux revision. '
        'The manuscript has not been changed by this review.','Small')

    page();heading('04 / SOURCE COVERAGE','Cited-source inventory')
    add('Snapshot acquired 2 October 2026; current phrase screening performed 8 October 2026. Token counts describe extracted text, not proof of extraction completeness.','Small')
    names=['Git Objects','Dolt Block Store','Dolt Storage Engine','Merkle digital signature','Making data structures persistent',
        'IPFS','Merkle Search Trees','LBFS','DataHub','Decibel','OrpheusDB','Principles of Dataset Versioning','Delta Lake',
        'Noms technical overview','ForkBase','Stratified B-trees','Scientific array versioning','TimeArr','Fully persistent B-trees',
        'Replicated versioned structures','TardisDB','Why and Where provenance','Differential dataflow','Archivable reproducibility',
        'Explain-Da-V','To Store or Not to Store','FAIR dataset versioning','DSLog array lineage','Git4Data','Baseline','NYC TLC source page']
    rows=[]
    for s,name in zip(r['sources'],names):
        status='Text screened' if s['included'] else ('No text' if s['number']==4 else 'Metadata only')
        rows.append([f"[{s['number']}]",name,f"{s['extracted_tokens']:,}",status])
    table(['Ref.','Source (short label)','Tokens','Coverage'],rows,[31,280,71,125],8.5,padding=3)
    add('Full source URLs, extraction hashes, manuscript paragraph locations and raw match records are retained in the accompanying screening.json audit file. '
        'The inventory is not a live availability certificate.','Small')

    page();heading('05 / ACTIONS AND RECORD','Use this as a review aid')
    add('Recommended next steps','H3')
    for t in [
        '<b>1. Author review:</b> approve the final results, attribution and declarations. Do not present this assistant-generated review as an independent examiner\'s assessment.',
        '<b>2. Resolve AI disclosure:</b> add a truthful statement after author approval, consistent with journal and institutional policy.',
        '<b>3. Institutional check:</b> if a formal report is needed, ask your supervisor to run the exact final file through an authorized Turnitin/iThenticate account. Review individual matches and record exclusions.',
        '<b>4. No detector-targeted edits:</b> improve accuracy, citation and clarity where warranted. The three recorded short matches do not justify rewriting technical terms or truthful declarations simply to lower a score.',
    ]:add(t)
    gap(5);add('Official interpretation and policy sources','H3')
    official=[
        ('Turnitin: Understanding the similarity score','https://guides.turnitin.com/hc/en-us/articles/23435833938701-Understanding-the-similarity-score',
         'Explains that matches and similarity percentages require human interpretation; similarity is not a plagiarism verdict.'),
        ('Turnitin: Using the AI Writing Report','https://guides.turnitin.com/hc/en-us/articles/22774058814093-Using-the-AI-Writing-Report',
         'Explains that AI detection is separate from similarity and may produce incorrect classifications.'),
        ('Springer Nature Discover: Editorial policies / Artificial Intelligence','https://link.springer.com/brands/discover/policies',
         'Sets disclosure and human-accountability requirements for evaluative or interpretive AI use.'),
    ]
    for title,url,desc in official:
        add(link(url,title));add(desc+' Accessed 8 October 2026.','Small')
    gap(5);add('Document identity','H3')
    add('Reviewed file: Revon_Research_Paper_Discover_Computing.docx','Small')
    add('DOCX SHA-256:<br/>'+r['docx_sha256'][:32]+'<br/>'+r['docx_sha256'][32:],'Small')
    add('PDF SHA-256:<br/>'+r['pdf_sha256'][:32]+'<br/>'+r['pdf_sha256'][32:],'Small')
    add('Reproduction: run tools/review_manuscript_originality.py against the same manuscript model and retained public-source texts. '
        'Machine-readable findings: output/pdf/revon-integrity-review-20261008/screening.json. '
        'Only selected short phrases were used in public web searches; the full manuscript was not uploaded to a similarity or AI-checking service.','Small')
    box('Final assessment',
        'The bounded exact-text review found only the three explained short overlaps. AI assistance is known and must not be represented as absent. '
        'A formal similarity score and any AI-detector result remain unmeasured. This report is not a submission clearance certificate.')

    def footer(c,doc):
        c.saveState();c.setStrokeColor(LINE);c.line(44,43,551,43)
        c.setFont('Arial',8);c.setFillColor(GRAY)
        c.drawString(44,29,'REVON | INTERNAL REVIEW - NOT A TURNITIN REPORT')
        c.drawRightString(551,29,f'{doc.page} / 6');c.restoreState()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(OUT),pagesize=(595,842),leftMargin=44,rightMargin=44,topMargin=42,bottomMargin=57,
        title='Revon - Similarity and AI-Assistance Review',author='OpenAI Codex - Internal author review',
        subject='Bounded source overlap screen and known AI-assistance review; no Turnitin or detector score')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    reader=PdfReader(OUT);assert len(reader.pages)==6,len(reader.pages)
    for pg in reader.pages:assert 'NOT A TURNITIN REPORT' in pg.extract_text()
    assert '5363' not in reader.pages[0].extract_text() or '5,363' in reader.pages[0].extract_text()
    dest=Path('C:/Users/admin/Downloads')/OUT.name
    shutil.copy2(OUT,dest)
    assert hashlib.sha256(dest.read_bytes()).digest()==hashlib.sha256(OUT.read_bytes()).digest()
    report=dict(pdf=str(OUT),download_copy=str(dest),pages=6,pdf_sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
        source_docx_sha256=r['docx_sha256'],source_pdf_sha256=r['pdf_sha256'],turnitin_access=False,ai_detector_run=False)
    (DATA/'report-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
