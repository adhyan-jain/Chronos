"""A clearer Figure 3 preview, with unchanged audited statistics."""
from pathlib import Path
import csv,json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT/'.codex_tmp/dataset_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator,FuncFormatter,NullLocator
from matplotlib.lines import Line2D
import numpy as np

def read(p):return list(csv.DictReader(p.open(encoding='utf-8',newline='')))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

CAPTION=('Linux Revon-M and Revon-H diff comparison. (a) Median latency with interquartile ranges on a logarithmic axis; paired medians are connected within each workload. '
    '(b) Median matched-trial M/H latency ratio with paired percentile bootstrap 95% intervals (20,000 resamples); the dashed line denotes parity. '
    'Each workload has seven measured trials. The highlighted S3 dense case has an interval containing parity; the other eight favour H. '
    'Ratios are medians of matched-trial ratios, not ratios of the two latency medians. Workload definitions are in Table III. '
    'These intervals concern repeated timings for fixed histories on one VM, not independent datasets or machines')

def main(folder=None, stem='Fig3_Redesigned', preview_only=True):
    folder=Path(folder) if folder is not None else ROOT/'output/figures/revon_diff_comparison_preview'
    folder.mkdir(parents=True,exist_ok=True)
    source=ROOT/'evidence/linux-validation-20261008'
    summary=read(source/'summary.csv');paired=read(source/'paired_uncertainty.csv')
    scenarios=['small-sparse','medium-sparse','medium-dense','large-sparse',
        'large-application-key-local','large-range-local','large-repeated-key',
        'large-hash-route-local','linux-tlc-n100000-h10-c100']
    labels=['S1  Small sparse','S2  Medium sparse','S3  Medium dense','S4  Large sparse',
        'S5  Application-key local','S6  Range local','S7  Repeated key',
        'S8  Hash-route local','P1  TLC public records']
    M='Revon-M (forced Merkle)';H='Revon-H'
    lookup={(r['scenario'],r['model']):r for r in summary}
    ratios={r['scenario']:r for r in paired if r['numerator_model']==M and r['denominator_model']==H and r['metric']=='diff_ms'}
    records=[]
    for scenario,label in zip(scenarios,labels):
        m,h,r=lookup[scenario,M],lookup[scenario,H],ratios[scenario]
        assert m['trials']==h['trials']==r['paired_trials']=='7'
        assert m['all_correct']==h['all_correct']=='True'
        record=dict(scenario=scenario,label=label,H_path=h['strategy_selected'])
        for key,row in [('M',m),('H',h)]:
            for statistic in ['median','p25','p75']:record[f'{key}_{statistic}']=float(row['diff_ms_'+statistic])
        record.update(ratio=float(r['median_paired_ratio']),ci_low=float(r['ci95_low']),ci_high=float(r['ci95_high']))
        records.append(record)
    assert len(records)==9 and sum(r['ci_low']>1 for r in records)==8
    plt.rcParams.update({'font.family':'Arial','font.size':9,'axes.labelsize':9,
        'xtick.labelsize':8.2,'ytick.labelsize':8.5,'axes.spines.top':False,
        'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#6C7A83',
        'text.color':'#233744','axes.labelcolor':'#233744','pdf.fonttype':42,'ps.fonttype':42,
        'svg.fonttype':'none','savefig.facecolor':'white'})
    f,(lat,ratio)=plt.subplots(1,2,figsize=(7.35,4.55),sharey=True,
        gridspec_kw={'width_ratios':[1.3,1],'wspace':.28})
    f.subplots_adjust(left=.245,right=.982,top=.80,bottom=.16)
    teal='#007C83';orange='#B75D36';gray='#6B747B'
    for ax in [lat,ratio]:
        ax.set_ylim(8.55,-.55)
        ax.tick_params(axis='y',length=0)
        ax.set_axisbelow(True)
        ax.grid(axis='x',color='#E3E9EB',linewidth=.65)
        for y in [0,2,4,6,8]:ax.axhspan(y-.47,y+.47,color='#F5F8F9',zorder=-2)
        ax.axhspan(1.53,2.47,color='#FFF2DB',zorder=-1)
    for i,r in enumerate(records):
        lat.plot([r['M_median'],r['H_median']],[i-.09,i+.09],color='#AAB9C0',linewidth=1.2,zorder=1)
        for key,dy,col,marker in [('M',-.09,orange,'o'),('H',.09,teal,'s')]:
            med=r[f'{key}_median'];lo=r[f'{key}_p25'];hi=r[f'{key}_p75']
            lat.errorbar(med,i+dy,xerr=[[med-lo],[hi-med]],fmt=marker,color=col,
                markersize=4.5,markeredgecolor='white',markeredgewidth=.5,
                elinewidth=1.15,capsize=2.3,zorder=3)
        inconclusive=r['ci_low']<=1<=r['ci_high'];col=gray if inconclusive else teal
        ratio.errorbar(r['ratio'],i,xerr=[[r['ratio']-r['ci_low']],[r['ci_high']-r['ratio']]],
            fmt='D' if inconclusive else 'o',color=col,markersize=4.7,
            markeredgecolor='white',markeredgewidth=.5,capsize=2.6,elinewidth=1.3,zorder=3)
        ratio.text(r['ci_high']+.12,i,f"{r['ratio']:.2f}×",ha='left',va='center',fontsize=8.4,color=col)
    lat.set_xscale('log');ticks=[.5,1,5,10,50,100]
    lat.xaxis.set_major_locator(FixedLocator(ticks));lat.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:g}'))
    lat.xaxis.set_minor_locator(NullLocator());lat.set_xlim(.45,100)
    lat.set_yticks(range(9),labels);lat.set_xlabel('Diff latency (ms, log scale)')
    ratio.tick_params(axis='y',labelleft=False)
    ratio.set_xlim(.72,6.25);ratio.set_xticks([1,2,3,4,5,6]);ratio.set_xlabel('Paired latency ratio (M/H)')
    ratio.axvline(1,color='#7E8B94',linestyle=(0,(3,3)),linewidth=1.0,zorder=2)
    lat.set_title('(a) Median and IQR',loc='left',fontsize=9.7,pad=10,fontweight='bold')
    ratio.set_title('(b) Paired ratio and 95% interval',loc='left',fontsize=9.7,pad=10,fontweight='bold')
    legend=[Line2D([0],[0],marker='o',color=orange,lw=0,markersize=5,label='Revon-M (forced Merkle)'),
        Line2D([0],[0],marker='s',color=teal,lw=0,markersize=5,label='Revon-H')]
    f.legend(handles=legend,frameon=False,ncols=2,loc='upper center',bbox_to_anchor=(.58,.975),fontsize=9)
    f.text(.245,.047,'Seven measured trials per workload',fontsize=8.5,color='#526471')
    f.text(.982,.047,'M/H > 1 favours Revon-H',ha='right',fontsize=8.5,color=teal)
    for ext in ['png','pdf','svg','eps']:f.savefig(folder/f'{stem}.{ext}',dpi=300)
    plt.close(f)
    with (folder/'plotted_data.csv').open('w',encoding='utf-8',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    caption='Fig. 3 '+CAPTION.replace('Table III','Table 3')+'.'
    (folder/'caption.md').write_text(caption+'\n',encoding='utf-8')
    report=dict(preview_only=preview_only,workloads=9,measured_trials_each=7,
        intervals_favour_H=8,dense_case_includes_parity=True,
        summary_sha256=sha(source/'summary.csv'),paired_summary_sha256=sha(source/'paired_uncertainty.csv'),
        ratios='exact retained paired medians and intervals; not recomputed from separate medians',
        figure_pdf_sha256=sha(folder/f'{stem}.pdf'))
    (folder/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
