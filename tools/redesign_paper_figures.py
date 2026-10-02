"""Redraw six manuscript figures from frozen evidence, changing images only.

Requires matplotlib, Pillow, python-docx and PyMuPDF. No benchmark is rerun.
DOCX XML (including extents, captions, references and tables) is byte-preserved.
PDF image objects are replaced in place: text, links and page geometry stay put.
Run with --apply to update the four current DOCX/PDF pairs after inspecting assets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter, NullLocator
from docx import Document
from PIL import Image
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".codex_tmp" / "figure_redesign"
EVIDENCE = ROOT / "evidence/paper-corrected-issues13-17-counterbalanced-final-20260923"
SENSITIVITY = ROOT / "evidence/trie-sensitivity-issues8-20260923/summary.csv"
PAPERS = [
    ROOT / "paper/Revon_Final_Research_Paper.docx",
    ROOT / "paper/Revon_Research_Paper_IEEE_Pagination_Fixed.docx",
    ROOT / "paper/Revon_Research_Paper_Single_Column.docx",
    ROOT / "output/docs/Revon_Research_Paper_BERT.docx",
]
SCENARIOS = ["small-sparse", "medium-sparse", "medium-dense", "large-sparse",
             "large-application-key-local", "large-range-local", "large-repeated-key",
             "large-hash-route-local"]
LABELS = ["Small sparse", "Medium sparse", "Medium dense", "Large sparse",
          "App-key local", "Range local", "Repeated key", "Hash-route local"]
MODELS = ["Snapshot", "Log-only", "Revon-M (forced Merkle)", "Revon-H", "Dolt"]
COLORS = ["#687989", "#C98A13", "#8767A2", "#007F87", "#C75632"]
INK, MUTED, GRID = "#182C3D", "#526575", "#E2E8ED"
BLUE, TEAL, ORANGE = "#296C9E", "#007F87", "#C75632"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def setup(width, height):
    # Actual document dimensions, never an image squeezed into a mismatched box.
    scale = max(1.0, width / 3.4)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 6.2 * scale,
        "axes.labelsize": 6.3 * scale, "xtick.labelsize": 5.9 * scale,
        "ytick.labelsize": 6.0 * scale, "text.color": INK,
        "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": "#A3B1BB", "axes.linewidth": .45,
        "pdf.fonttype": 42, "svg.fonttype": "none"})
    return plt.figure(figsize=(width, height), facecolor="white"), scale


def heading(fig, text, subtitle, scale):
    fig.text(.015, .974, text, va="top", fontsize=8.0 * scale, weight="bold")
    fig.text(.015, .884, subtitle, va="top", fontsize=5.9 * scale, color=MUTED)


def clean(ax, axis="x"):
    ax.set_axisbelow(True)
    ax.grid(axis=axis, color=GRID, lw=.45)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=2, width=.4, pad=2)


def box(ax, x, y, w, h, text, color=BLUE, fill="#EFF5FA", fs=6.4, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.007,rounding_size=0.02",
                              linewidth=.7, edgecolor=color, facecolor=fill))
    ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs,
            linespacing=1.2, weight="bold" if bold else "normal")


def arrow(ax, start, end, color=BLUE):
    ax.annotate("", xy=end, xytext=start,
                arrowprops={"arrowstyle": "->", "lw": .75, "color": color,
                            "shrinkA": 1, "shrinkB": 1, "mutation_scale": 7})


def architecture(fig, scale):
    heading(fig, "Revon-H architecture", "Service interface, versioning core and persistence", scale)
    ax = fig.add_axes([.015, .025, .97, .76]); ax.set(xlim=(0,1), ylim=(0,1)); ax.axis("off")
    # Two rows allow readable labels without compressing the letterforms.
    box(ax,.02,.66,.26,.24,"Frontend\nmetrics",fs=6.5*scale)
    box(ax,.37,.66,.26,.24,"REST API",fs=6.5*scale)
    box(ax,.72,.66,.26,.24,"SQLite store\nobjects, commits\nHEAD",ORANGE,"#FCF1EC",6.2*scale)
    arrow(ax,(.29,.78),(.36,.78))
    box(ax,.02,.03,.96,.46,"",TEAL,"#F0F8F7")
    ax.text(.04,.43,"Revon-H core  |  research contribution",color=TEAL,weight="bold",fontsize=6.6*scale,va="top")
    ax.text(.04,.32,"commit / checkout / diff",color=MUTED,fontsize=6*scale)
    for x,t in zip([.045,.37,.695],["Fixed-depth\nhash trie","Incremental\npath rewriting","Adaptive\nlog / Merkle diff"]):
        box(ax,x,.065,.26,.185,t,TEAL,"white",6.1*scale)
    arrow(ax,(.5,.65),(.5,.5),TEAL)
    arrow(ax,(.85,.50),(.85,.65),ORANGE)


def workflow(fig, scale):
    heading(fig, "Incremental commit and hybrid diff", "Update changed paths; reuse unchanged hashes", scale)
    ax=fig.add_axes([.015,.015,.97,.77]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis("off")
    # Three stages on the first row, two on the second; arrows show exact order.
    for x,t in zip([.02,.365,.71],["1  Mutation\nbatch","2  Hash keys\nand route","3  Rewrite\nchanged leaves"]):
        box(ax,x,.71,.27,.24,t,fs=6.0*scale)
    arrow(ax,(.30,.83),(.355,.83));arrow(ax,(.645,.83),(.70,.83))
    box(ax,.71,.37,.27,.23,"4  Rewrite\nancestor paths",fs=6.0*scale)
    box(ax,.365,.37,.27,.23,"5  Persist objects\ncommit / HEAD",ORANGE,"#FCF1EC",5.8*scale)
    arrow(ax,(.845,.70),(.845,.61));arrow(ax,(.70,.485),(.645,.485))
    ax.text(.02,.56,"DIFF SELECTION",color=TEAL,weight="bold",fontsize=6.2*scale)
    ax.text(.02,.40,"Accumulated operations",fontsize=5.7*scale,color=MUTED)
    box(ax,.02,.015,.44,.25,"≤ 4,096: log path\nAggregate changesets",TEAL,"#F0F8F7",6.0*scale)
    box(ax,.54,.015,.44,.25,"> 4,096: Merkle path\nCompare unequal hashes",ORANGE,"#FCF1EC",6.0*scale)
    # Separate diff operation, not a fabricated mandatory step after commit.
    arrow(ax,(.24,.34),(.24,.275),TEAL)
    arrow(ax,(.24,.34),(.76,.275),ORANGE)


def calibration(fig, scale, rows):
    heading(fig,"Threshold calibration","Separate workloads; medians and interquartile ranges",scale)
    ax=fig.add_axes([.16,.29,.80,.43])
    logs={r['scenario']:r for r in rows if r['model']=='Revon-log calibration'}
    for model,color,marker,label in [('Revon-log calibration',TEAL,'o','Log aggregation'),
            ('Revon-M (forced Merkle)',ORANGE,'s','Merkle comparison')]:
        rs=sorted([r for r in rows if r['model']==model],key=lambda r:float(logs[r['scenario']]['work_examined_median']))
        xs=[float(logs[r['scenario']]['work_examined_median']) for r in rs]
        ys=[float(r['diff_ms_median']) for r in rs]
        ax.plot(xs,ys,color=color,marker=marker,ms=2.8,lw=.8,label=label)
        ax.fill_between(xs,[float(r['diff_ms_p25']) for r in rs],[float(r['diff_ms_p75']) for r in rs],color=color,alpha=.12,lw=0)
    ax.set(xscale='log',yscale='log',xlim=(3,6000),xlabel='Accumulated operations (log scale)',ylabel='Diff latency (ms)')
    ax.set_xticks([4,16,64,256,1024,4096],['4','16','64','256','1,024','4,096'])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x:g}'))
    ax.axvline(4096,color=MUTED,lw=.7,ls='--')
    ax.text(.98,.05,'Boundary: 4,096',ha='right',transform=ax.transAxes,fontsize=5.7*scale,color=MUTED)
    ax.xaxis.set_minor_locator(NullLocator());clean(ax,'both')
    fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.55,.008),ncol=2,frameon=False,fontsize=5.8*scale,handlelength=1.8,columnspacing=1.4)


def intervals(ax, rows, metric, ys, color, marker, label):
    med=[float(r[f'{metric}_ms_median']) for r in rows]
    low=[m-float(r[f'{metric}_ms_p25']) for m,r in zip(med,rows)]
    high=[float(r[f'{metric}_ms_p75'])-m for m,r in zip(med,rows)]
    assert min(low+high)>=0 and min(med)>0
    ax.errorbar(med,ys,xerr=[low,high],fmt=marker,color=color,ms=2.4,
                elinewidth=.65,capsize=1.3,capthick=.5,label=label,linestyle='none')


def diff_chart(fig, scale, evaluation):
    # The paper caption already gives the chart title and scope. Use that
    # redundant header space for larger labels and a taller plot.
    ax=fig.add_axes([.305,.35,.67,.59])
    for i,(model,color,marker) in enumerate(zip(MODELS,COLORS,['o','s','^','D','v'])):
        intervals(ax,[evaluation[(s,model)] for s in SCENARIOS],'diff',
                  [j+(i-2)*.14 for j in range(8)],color,marker,model.replace(' (forced Merkle)',''))
    ax.set(xscale='log',ylim=(7.6,-.6))
    ax.set_yticks(range(8),LABELS);ax.tick_params(axis='y',length=0)
    ax.set_xlim(.08,2500);ax.set_xticks([.1,1,10,100,1000],['0.1','1','10','100','1,000'])
    for y in [0,2,4,6]:ax.axhspan(y-.5,y+.5,color='#F5F8FA',zorder=-1)
    clean(ax);ax.spines['left'].set_visible(False)
    fig.text(.65,.17,'Latency (ms, log scale)',ha='center',fontsize=6.8*scale)
    fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.025),ncol=5,frameon=False,fontsize=6.0*scale,handletextpad=.2,columnspacing=.7,handlelength=1.3)


def operational(fig, scale, evaluation):
    for i,(metric,title) in enumerate([('incremental_commit','Incremental commit'),('checkout','Historical checkout')]):
        ax=fig.add_axes([.30+i*.36,.38,.325,.52])
        for model,color,marker,off in [('Revon-H',TEAL,'o',-.13),('Dolt',ORANGE,'s',.13)]:
            intervals(ax,[evaluation[(s,model)] for s in SCENARIOS],metric,
                      [j+off for j in range(8)],color,marker,model)
        ax.set(xscale='log',xlim=(.8,4000),ylim=(7.55,-.55))
        ax.set_title(title,fontsize=6.1*scale,pad=4,weight='bold')
        ax.set_xticks([1,10,100,1000],['1','10','100','1k'])
        ax.set_yticks(range(8),LABELS if i==0 else ['']*8)
        ax.tick_params(axis='y',length=0)
        for y in [0,2,4,6]:ax.axhspan(y-.5,y+.5,color='#F5F8FA',zorder=-1)
        clean(ax);ax.spines['left'].set_visible(False)
    fig.text(.65,.18,'Latency (ms, log scale)',ha='center',fontsize=6.5*scale)
    fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.6,.035),ncol=2,frameon=False,fontsize=6.3*scale,handlelength=1.4)


def sensitivity(fig, scale, rows):
    heading(fig,"Fixed-trie geometry sensitivity","10,000 rows; forced-Merkle diff; seven runs per configuration",scale)
    ax=fig.add_axes([.16,.23,.79,.52])
    offsets={'b4-d6':(8,13),'b8-d3':(8,0),'b8-d4':(8,-13),'b8-d5':(8,5),'b16-d3':(-8,-1)}
    for r in rows:
        x=float(r['storage_bytes_median'])/(1024**2); y=float(r['diff_ms_median']);name=r['config']
        c=TEAL if name=='b8-d4' else BLUE
        ax.plot(x,y,'D' if name=='b8-d4' else 'o',color=c,ms=4 if name=='b8-d4' else 3)
        dx,dy=offsets[name]
        ax.annotate(name,xy=(x,y),xytext=(dx,dy),textcoords='offset points',ha='left' if dx>0 else 'right',
                    fontsize=6.3*scale,color=c,weight='bold' if name=='b8-d4' else 'normal',
                    arrowprops={'arrowstyle':'-','lw':.4,'color':c} if abs(dy)>7 else None)
    max75=max(float(r['diff_ms_p75']) for r in rows)
    ax.set(xlim=(4,8.6),ylim=(15,max75+4),xlabel='Repository storage (MiB)',ylabel='Median diff (ms)')
    ax.set_xticks([4,5,6,7,8]);ax.set_yticks([20,30,40]);clean(ax,'both')
    fig.text(.54,.01,'b = branching factor; d = depth; default: b8-d4',ha='center',fontsize=5.9*scale,color=MUTED)


def build_assets(paper, evaluation, calibration_rows, sensitivity_rows):
    target=WORK/'assets'/paper.stem;target.mkdir(parents=True,exist_ok=True)
    shapes=Document(paper).inline_shapes;assert len(shapes)==6
    for index,shape in enumerate(shapes,1):
        width,height=shape.width/914400,shape.height/914400
        fig,scale=setup(width,height)
        if index==1:architecture(fig,scale)
        elif index==2:workflow(fig,scale)
        elif index==3:calibration(fig,scale,calibration_rows)
        elif index==4:diff_chart(fig,scale,evaluation)
        elif index==5:operational(fig,scale,evaluation)
        else:sensitivity(fig,scale,sensitivity_rows)
        # Exact canvas dimensions retained: tight cropping would change aspect ratio.
        fig.savefig(target/f'figure{index}.png',dpi=600,facecolor='white')
        fig.savefig(target/f'figure{index}.svg',facecolor='white')
        plt.close(fig)
    return target


def replace_pair(paper, assets):
    # A fresh input fingerprint prevents a later rerun from restoring stale text.
    fingerprint=hashlib.sha256(paper.read_bytes()+paper.with_suffix('.pdf').read_bytes()).hexdigest()[:16]
    backup=WORK/'backups'/fingerprint;backup.mkdir(parents=True,exist_ok=True)
    for path in [paper,paper.with_suffix('.pdf')]:
        dest=backup/path.name
        if not dest.exists():shutil.copy2(path,dest)
    original=backup/paper.name
    doc=Document(original)
    replacements={str(doc.part.related_parts[s._inline.graphic.graphicData.pic.blipFill.blip.embed].partname).lstrip('/'):
                  (assets/f'figure{i}.png').read_bytes() for i,s in enumerate(doc.inline_shapes,1)}
    temp=paper.with_suffix('.figures.tmp.docx')
    with zipfile.ZipFile(original) as src,zipfile.ZipFile(temp,'w') as dst:
        for info in src.infolist():dst.writestr(info,replacements.get(info.filename,src.read(info.filename)))
    with zipfile.ZipFile(original) as a,zipfile.ZipFile(temp) as b:
        changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
        assert set(changed)<=set(replacements),changed
        assert all(b.read(n)==data for n,data in replacements.items())
    temp.replace(paper)

    # Change only image XObjects. Page content streams/positions remain untouched.
    srcpdf=backup/paper.with_suffix('.pdf').name
    pdf=pymupdf.open(srcpdf)
    images=[(p.number,im) for p in pdf for im in p.get_image_info(xrefs=True)]
    assert len(images)==6 and len({im['xref'] for _,im in images})==6
    for i,(page,im) in enumerate(images,1):
        with Image.open(assets/f'figure{i}.png') as source:
            rgb=source.convert('RGB');w,h=rgb.size
            xref=im['xref']
            pdf.update_object(xref,f'<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace /DeviceRGB /BitsPerComponent 8 >>')
            pdf.update_stream(xref,rgb.tobytes(),compress=True)
    output=paper.with_suffix('.figures.tmp.pdf');pdf.save(output,deflate=True);pdf.close()
    with pymupdf.open(srcpdf) as old,pymupdf.open(output) as new:
        assert len(old)==len(new)
        for a,b in zip(old,new):
            assert a.get_text('words')==b.get_text('words')
            assert a.rect==b.rect and a.get_links()==b.get_links()
            assert a.read_contents()==b.read_contents()
            assert [v['bbox'] for v in a.get_image_info()]==[v['bbox'] for v in b.get_image_info()]
    with pymupdf.open(output) as checked:
        page_count=len(checked)
    output.replace(paper.with_suffix('.pdf'))
    return {'paper':str(paper.relative_to(ROOT)),'changed_docx_parts':changed,'pdf_pages':page_count,
            'non_image_docx_parts_unchanged':True,'pdf_text_links_content_streams_unchanged':True}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    audit=json.loads((EVIDENCE/'evidence_audit.json').read_text())
    assert audit['passed'] and not audit['issues']
    rows=read_csv(EVIDENCE/'summary.csv');sens=read_csv(SENSITIVITY)
    assert all(r['all_correct']=='True' and int(r['trials'])==7 for r in rows+sens)
    evaluation={(r['scenario'],r['model']):r for r in rows if r['phase']=='evaluation'}
    cal=[r for r in rows if r['phase']=='calibration']
    report=[]
    for paper in PAPERS:
        assets=build_assets(paper,evaluation,cal,sens)
        if args.apply:report.append(replace_pair(paper,assets))
        print(f"{'Updated' if args.apply else 'Rendered assets for'} {paper.name}")
    if args.apply:
        (WORK/'verification.json').write_text(json.dumps({'files':report,'sources':{
            str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [EVIDENCE/'summary.csv',SENSITIVITY]}},indent=2))


if __name__=='__main__':main()
