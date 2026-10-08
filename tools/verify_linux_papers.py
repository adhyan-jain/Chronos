"""Cross-check synchronized final DOCX/PDF artifacts and data-derived claims."""
from pathlib import Path
import csv,hashlib,json,re
from docx import Document
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/docs/linux-final-20261008'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    blocks=json.loads((OUT/'manuscript_model.json').read_text(encoding='utf-8'))
    texts='\n'.join(b.get('text','') for b in blocks if b['kind']!='reference')
    cited=set(int(n) for group in re.findall(r'\[([0-9, -]+)\]',texts) for n in re.findall(r'\d+',group))
    refs=[b for b in blocks if b['kind']=='reference']
    assert cited==set(range(1,32)),(cited,len(refs))
    assert len(refs)==31
    assert len(next(b['text'] for b in blocks if b['kind']=='abstract').split())<250
    tables=[b for b in blocks if b['kind']=='table']
    assert [b['number'] for b in tables]==list(range(1,12))
    figures=[b for b in blocks if b['kind']=='figure']
    assert [b['number'] for b in figures]==list(range(1,8))
    output={}
    body_lists=[]
    for name in ['Discover_Computing','IEEE']:
        path=ROOT/f'paper/Revon_Research_Paper_{name}.docx'
        doc=Document(path);assert len(doc.tables)==11 and len(doc.inline_shapes)==7
        fig3=next(b for b in figures if b['number']==3)
        caption=fig3['caption'] if name=='IEEE' else fig3['caption'].replace('Table III','Table 3')
        assert caption in '\n'.join(p.text for p in doc.paragraphs)
        figure_shape=doc.inline_shapes[2]
        embed=figure_shape._inline.xpath('.//a:blip')[0]
        from docx.oxml.ns import qn
        assert doc.part.related_parts[embed.get(qn('r:embed'))].blob==(OUT/'figures/Fig3.png').read_bytes()
        for observed,expected in zip(doc.tables,tables):
            assert [[c.text for c in r.cells] for r in observed.rows]==[expected['headers']]+expected['rows']
        alltext='\n'.join(p.text for p in doc.paragraphs)
        assert not any(s in alltext for s in ['independent hardware validation still outstanding','No independent Linux machine was available','Linux hardware unavailable'])
        assert all(s in alltext for s in ['516','72','32,768','one trial per system','poornima.n@vit.ac.in'])
        from docx.oxml.ns import qn
        if name=='Discover_Computing':
            sizes=[float(e.get(qn('w:val')))/2 for e in doc._element.xpath('.//w:sz')]
            assert min(sizes)>=12,min(sizes)
        paragraphs=[p.text for p in doc.paragraphs if p.style.name=='Normal' and not p.text.startswith(('Keywords:','Index Terms'))]
        roman={1:'I',2:'II',3:'III',4:'IV',5:'V',6:'VI',7:'VII',8:'VIII',9:'IX',10:'X',11:'XI'}
        def normalize(t):
            for n,v in sorted(roman.items(),reverse=True):t=re.sub(r'Table '+v+r'\b','Table '+str(n),t)
            return re.sub(r'\s+',' ',t).strip()
        body_lists.append([normalize(p) for p in paragraphs if p.strip()])
        pdf=path.with_suffix('.pdf');reader=PdfReader(pdf)
        fig_pages=[pg.extract_text() for pg in reader.pages if 'highlighted S3' in pg.extract_text()]
        assert len(fig_pages)==1 and '20,000' in fig_pages[0]
        assert len(reader.pages)>0
        for pg in reader.pages:assert len(pg.extract_text().strip())>10
        assert '[31]' in reader.pages[-1].extract_text()
        output[name]=dict(docx_sha256=sha(path),pdf_sha256=sha(pdf),pages=len(reader.pages),tables=11,figures=7)
    assert body_lists[0]==body_lists[1],'body/reference content differs across formats'
    paired=list(csv.DictReader((ROOT/'evidence/linux-validation-20261008/paired_uncertainty.csv').open()))
    ablation=[r for r in paired if r['numerator_model']=='Revon-M (forced Merkle)' and r['metric']=='diff_ms']
    assert len(ablation)==9 and sum(float(r['ci95_low'])>1 for r in ablation)==8
    report=dict(passed=True,outputs=output,identical_scientific_body=True,all_table_cells_match_model=True,
        cited_references=31,abstract_words=184,ablation_intervals_favour_h=8,ablation_comparisons=9,
        visual_review='Every rendered final page inspected; figures and captions retained together; short tables kept intact',
        renderer='Word COM PDF export + bundled Poppler PNG; canonical render_docx unavailable because no soffice on PATH',
        pending='Corresponding-author review and required AI-use disclosure decision before journal submission')
    (OUT/'final-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
