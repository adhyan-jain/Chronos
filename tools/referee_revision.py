"""Reproducible analysis and semantic edits for the October referee revision."""
from __future__ import annotations
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/referee-analysis-20261003'
PUBLIC_COMMIT='37d27d465ffc922a3881b85bb415574f956a9a09'


def rows(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def percentile(values,q):
    a=sorted(values);x=(len(a)-1)*q;i=int(x)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)


def stats(values):
    return [statistics.median(values),percentile(values,.25),percentile(values,.75)]


def interval(values,scale=1,digits=2):
    a,b,c=stats([v/scale for v in values])
    return f'{a:.{digits}f} [{b:.{digits}f}, {c:.{digits}f}]'


def analysis():
    inputs=[ROOT/'evidence/threshold-heldout-20261002/summary.csv',
            ROOT/'evidence/threshold-robustness-pilot-20261002/raw_results.csv',
            ROOT/'evidence/trie-sensitivity-issues8-20260923/summary.csv',
            ROOT/'evidence/public-tlc-combined-20261002/raw_results.csv']
    thresh,pilot,geometry,public=map(rows,inputs)
    OUT.mkdir(exist_ok=True)
    regret=[]
    for scenario in sorted({r['scenario'] for r in thresh}):
        rs=[r for r in thresh if r['scenario']==scenario]
        forced={r['strategy']:float(r['median_ms']) for r in rs if r['strategy'] in ('log','merkle')}
        best=min(forced.values())
        for r in rs:
            regret.append(dict(scenario=scenario,split=r['split'],strategy=r['strategy'],threshold=r['threshold'],
                               median_ms=float(r['median_ms']),oracle_ms=best,
                               normalized_score=float(r['median_ms'])/best,regret_ms=float(r['median_ms'])-best))
    scores={s:{split:statistics.mean(r['normalized_score'] for r in regret if r['strategy']==s and r['split']==split)
               for split in ('calibration','validation')} for s in ('log','merkle')}
    assert all(r['regret_ms']==0 for r in regret if r['strategy']=='log')
    with (OUT/'threshold_regret.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(regret[0]));w.writeheader();w.writerows(regret)
    startup=[]
    for case in sorted({r['case'] for r in pilot if r['cache_condition']=='fresh-process-reopened'}):
        rs=[r for r in pilot if r['case']==case and r['cache_condition']=='fresh-process-reopened' and r['strategy']=='merkle' and r['trial_kind']=='measured']
        assert len(rs)==3 and all(r['correctness']=='True' for r in rs)
        for r in rs:assert abs(float(r['open_plus_diff_ms'])-float(r['open_verify_ms'])-float(r['diff_ms']))<1e-5
        startup.append(dict(case=case,locality=rs[0]['locality'],seed=int(rs[0]['seed']),n=3,
                            open_ms=stats([float(r['open_verify_ms']) for r in rs]),diff_ms=stats([float(r['diff_ms']) for r in rs]),
                            total_ms=stats([float(r['open_plus_diff_ms']) for r in rs])))
    rss=[]
    for count in (10000,100000,1000000):
        scenario=f'tlc-n{count}-h10-c{count//1000}'
        for model in ('Revon-H','Revon-M (forced Merkle)','Dolt','Dolt (bulk import)','Log-only','Snapshot'):
            rs=[r for r in public if r['scenario']==scenario and r['model']==model and r['status']=='ok' and r['trial_kind']=='measured']
            assert len(rs)==7
            rss.append(dict(rows=count,model=model,n=7,MiB=stats([float(r['process_tree_peak_rss_bytes'])/2**20 for r in rs])))
    paired=[]
    for condition in ('warmed-built','fresh-process-reopened'):
        for case in sorted({r['case'] for r in pilot if r['cache_condition']==condition}):
            rs=[r for r in pilot if r['case']==case and r['cache_condition']==condition and r['trial_kind']=='measured']
            by={(int(r['block']),r['strategy'],int(r['threshold'])):r for r in rs}
            blocks=sorted({int(r['block']) for r in rs})
            forced_ratio=[float(by[(b,'log',0)]['diff_ms'])/float(by[(b,'merkle',0)]['diff_ms']) for b in blocks]
            same=[]
            for r in rs:
                if r['strategy']=='hybrid':
                    same.append(float(r['diff_ms'])/float(by[(int(r['block']),r['selected'],0)]['diff_ms']))
            paired.append(dict(case=case,condition=condition,seed=int(rs[0]['seed']),operations=int(rs[0]['operations']),
                               locality=rs[0]['locality'],n_blocks=len(blocks),log_over_merkle=stats(forced_ratio),
                               same_path_selector_over_forced=stats(same),paired_block_ratios=forced_ratio))
    result=dict(static_scores=scores,forced_log_wins=42,startup=startup,geometry=geometry,rss=rss,paired=paired)
    (OUT/'analysis.json').write_text(json.dumps(result,indent=2))
    manifest=dict(analysis_only=True,source_commit=PUBLIC_COMMIT,
                  inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                  method='Medians and linear interpolated quartiles. Threshold scores equal-weight case median/oracle. Startup totals paired per recorded row. Pilot ratios paired by case/cache/block.',
                  generated_by='python tools/referee_revision.py',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return result


def fmt(s,d=2):return f'{s[0]:.{d}f} [{s[1]:.{d}f}, {s[2]:.{d}f}]'


def revise(blocks):
    data=analysis()
    out=[]
    def p(text,kind='body'):return dict(kind=kind,text=text)
    for b in blocks:
        b=dict(b);text=b.get('text','')
        if b['kind']=='author':
            text=re.sub(r'(?<=[a-zA-Z])[12](?=,|$)','',text)
            if text.strip()=='poornima.n@vit.ac.in':text='Corresponding author: Poornima N (poornima.n@vit.ac.in)'
        if b['kind']=='abstract':
            text='Abstract: Revon is a Python prototype for durable, linear-history key/value versioning using a fixed-depth Merkle hash trie. It retains addressed changesets and selects log aggregation or hash-pruned comparison for version differences. Both paths share the same stored representation. Archived synthetic experiments favor the hybrid variant over forced Merkle in five of eight paired latency intervals; three include parity. Public NYC TLC records extend the study to one million records using generated corrections and expose substantial commit and storage costs. In a separate predefined threshold study, always-log has the lower forced-path median in all 42 calibration and validation cases. The selected threshold improves on the original setting but does not establish an adaptive advantage over always-log. Exploratory histories show profile-dependent path preferences without resolving a universal crossover. We report repository startup, resident query costs, geometry work counters and whole-worker memory separately. A subsequent correctness repair protects nested JSON values and aligns change detection with encoded identity; its bounded overhead check is separate from the archived performance results. All timings use one physical computer. The contribution is a reproducible empirical comparison of differencing choices and their trade-offs within this bounded prototype.'
        if b['kind']=='reference' and text.startswith('[25]'):
            text='[25] R. Shraga and R. J. Miller, "Explaining Dataset Changes for Semantic Data Versioning with Explain-Da-V," Proc. VLDB Endow., vol. 16, no. 6, pp. 1587-1600, 2023. https://doi.org/10.14778/3583140.3583169. Open paper: https://www.vldb.org/pvldb/vol16/p1587-shraga.pdf. Extended report: https://arxiv.org/abs/2301.13095.'
        if text.startswith('Funding:'):text='Funding: The authors received no funding for this work.'
        if text.startswith('Competing interests and author contributions:'):
            text='Competing interests: The authors declare no competing interests.'
            out.append(p(text));out.append(p('Author contributions: Atharva Sheersh Pandey carried out 80% of the research work and Adhyan Jain 20%. Poornima Nedunchezhian provided guidance and critical review. All authors reviewed and approved the manuscript.'))
            continue
        if text.startswith('Ethics:'):
            text='Ethics and consent to participate: Not applicable to participant recruitment or intervention. This computational study uses publicly released, de-identified NYC TLC records and generated modifications; it includes no newly recruited participants or human or animal experiments.'
        if text.startswith('AI assistance:'):continue  # Author explicitly requested a separate note.
        if text.startswith('Data and code availability:'):
            text=f'Data and code availability: The archived experiment bundles are publicly accessible at https://github.com/atharvasheersh/Revon/tree/{PUBLIC_COMMIT}/evidence. Appendix A identifies their exact directories and reproduction commands. TLC source trip files are downloaded separately using the acquisition/checksum procedure [31]. Generated databases are rebuilt from the retained inputs. The JSON repair and its supplemental analysis are a subsequent local revision, identified by file hashes; their public release is pending. Public access does not establish independent reproduction of timings.'
        text=text.replace('Local revision evidence is not yet a public release.',f'These archived bundles are available in public commit {PUBLIC_COMMIT}.')
        text=text.replace('Public release of this new bundle is pending; it is reported only as exploratory evidence, separate from original and held-out results.', 'This bundle is publicly available at the immutable commit identified above and remains exploratory evidence, separate from original and held-out results.')
        text=text.replace('Related work and the scope of Revon','Related-work summary')
        text=text.replace('Table I compares the related systems and the scope addressed by Revon.','Table I summarizes related systems and studies; the design section defines the implemented Revon scope.')
        if text.startswith('For RQ3'):
            text='For RQ3, the sampled geometries trade latency against storage; no universal optimum is established. Within a fixed-branching-factor depth sweep, deeper routing lowers expected occupancy and adds traversal work. At fixed bucket capacity, occupancy is unchanged and the contrast instead concerns traversal shape. The work counters and fixed-order limitation in Appendix B constrain this interpretation.'
        text=text.replace('production durability, which the Revon prototype does not','production operational capabilities beyond the atomic single-writer SQLite persistence evaluated here')
        if text.startswith('For RQ2, adaptive differencing helps'):
            text='For RQ2, access to log aggregation improves on forced Merkle in selected sparse and repeated-key cases, while dense and long histories do not consistently favor H. This answers the stated H/M comparison. It does not show that switching beats always-log: the latter has normalized score 1.000 on both splits of the main threshold supplement, below the frozen selector scores. The separate pilot motivates investigating workload-sensitive selection but does not validate a superior policy.'
        if text.startswith('Revon combines immutable objects, incremental trie updates'):
            text='Revon combines addressed objects, incremental trie updates, SQLite persistence and alternate log/Merkle diff paths in a single-writer prototype. Archived H/M comparisons show advantages for selected intervals alongside commit, storage and long-history costs. Always-log is the fastest forced policy throughout the main threshold supplement, so those results do not establish a benefit from adaptation itself. Exploratory profiles prefer different paths, with substantial timing variability and no resolved universal crossover. JSON ownership and identity defects were subsequently repaired and verified separately; historical timings remain tied to their archived code. The contribution is the measured trade-off study and reproducible prototype, with independent hardware validation still outstanding.'
        if text.startswith('Calibration selects T='):
            text+=' Across all 21 calibration and 21 validation cases, forced log has the lower forced-path median. Always-log therefore scores 1.000 on each split. The chosen selector does not outperform that static control in this supplement. Per-case normalized scores and excess latency relative to the faster forced median are retained in evidence/referee-analysis-20261003/threshold_regret.csv; observed negative excess is measurement variation, not a negative cost of selection.'
        if text.startswith('The counterbalanced primary design pairs'):
            text+=' These are pointwise exploratory intervals; neither bootstrap resampling nor multiple displayed intervals supplies extra independent trials or simultaneous 95% coverage.'
        if text.startswith('Reopening eagerly loads'):
            text+=' Appendix B reports open/verify, diff and paired open-plus-diff times from the recorded fresh-process rows. Primary workflow reads also use an already-built resident Revon model; Dolt starts a CLI process per command. These measurements do not isolate startup-inclusive engine efficiency.'
        if text.startswith('These bundles share a physical host'):
            text+=' Performance results in the main study refer to the archived pre-repair source snapshots. Appendix B identifies the subsequent JSON repair and reports its separate bounded check; the earlier timings are not measurements of that repaired revision.'
        b['text']=text if 'text' in b else b.get('text','')
        if b['kind']=='table':
            b.pop('text',None)
            if b['number']==1:b['caption']='Related-work summary'
            if b['number']==3:b['headers']=[h.replace('Changed keys','Changed keys per commit') for h in b['headers']]
            if b['number']==5:
                b['headers'][0]='Policy / threshold'
                b['rows']=list(b['rows'])+[[label,f"{data['static_scores'][mode]['calibration']:.3f}",f"{data['static_scores'][mode]['validation']:.3f}",'Static control'] for mode,label in [('log','Always-log'),('merkle','Always-Merkle')]]
            if b['number']==6:
                b['headers']=[('Median paired M/H ratio [95% CI]' if 'ratio' in h.lower() or h.strip()=='M/H' else h) for h in b['headers']]
                b['caption']+='; the median paired ratio need not equal the ratio of marginal medians'
        if b['kind']=='figure':b.pop('text',None)
        out.append(b)
        if text.startswith('The original synthetic and public workflow matrices retain'):
            out.extend(design_blocks())
        if text.startswith('For RQ1, the public-record study'):
            out.append(p('The simpler baselines expose a different trade-off. At 100k records/H10/0.1%, Log-only commits in 4.11 ms and occupies 32.93 MiB, versus H at 161.09 ms and 90.04 MiB; H has the lower diff median, 8.65 versus 29.62 ms. At H50, Log-only has lower commit, storage and diff medians (3.26 ms, 35.58 MiB, 52.11 ms) than H (141.22 ms, 137.24 MiB, 91.79 ms). Snapshot pays for materialized versions; Log-only pays replay work when reconstructing history. The measured H/M advantage alone does not justify the additional retained structures against these alternatives. A user must weigh observed reads, writes, replay distance and storage rather than assume a general winner.'))
        if text.startswith('For RQ3'):
            out.append(p('The geometry sweep uses one 10,000-row, ten-commit, 100-changes-per-commit spread workload with 32-byte values, seed 20260824 and forced Merkle. All repetitions of each configuration precede the next configuration, so time drift can affect the descriptive rankings. b4-d6, b8-d4 and b16-d3 each provide 4,096 buckets and equal expected occupancy; their contrast concerns routing/traversal shape. The b8 depth sweep changes bucket capacity. Appendix B reports the work counters, including 17,048 leaf entries for b8-d3 versus 5,682 for b4-d6 and b16-d3.'))
    idx=next(i for i,b in enumerate(out) if b.get('text','').lower()=='declarations')
    out[idx:idx]=supplement(data)
    return out


def design_blocks():
    texts=[
      ('JSON value ownership and identity','h2'),
      ('Values are JSON nulls, booleans, finite numbers, strings, lists and objects with string keys. Input containers are validated and detached before retention; read and diagnostic views export detached containers. Immutable scalars can be shared. Unsupported Python-only values, non-string nested object keys, non-finite numbers and cyclic containers are rejected before writing. Equality follows the existing v1 JSON encoding: sorted object keys, compact separators, UTF-8, no NaN. Thus true, 1, 1.0 and signed floating zero retain their encoded distinctions. This is a Python encoding contract, not a claim of compliance with a cross-language canonical-JSON standard.','body'),
      ('Algorithm 1 (batch update). Validate and own the input values; reject overlapping puts/deletes and missing deletions before interning. Read each old value and retain only encoded-identity changes. Group effective mutations by routing prefix. Rewrite each touched leaf, sort entries, hash its complete payload and rebuild affected ancestors; reuse untouched child hashes. Record the addressed changeset and commit. The ownership invariant is that callers cannot mutate retained values through supported reads or earlier inputs.','body'),
      ('Algorithm 2 (log composition). Traverse the chronological ancestor interval. For each key retain its first old existence/value and its last new existence/value. Discard the key exactly when these endpoint states have equal existence and encoded value. This cancels insert-then-delete and update-then-restore sequences. Null and absence remain distinct. Sort remaining keys; reverse requests swap endpoints and added/deleted labels.','body'),
      ('Algorithm 3 (selection). Validate versions and determine ancestry in either direction. Sum changeset operation counts along the interval. Select log when eligible and the count is at most T; otherwise select Merkle. Merkle skips equal addressed subtrees and compares values in unequal leaves. Both paths apply the same encoded-identity rule and return detached outputs.','body'),
      ('Cost model. Let N be records, d depth, b branching factor, m batch keys, h interval length, p accumulated operations, u distinct interval keys and s serialized output bytes. Under uniform routing, expected leaf occupancy is N/(b^d), but worst-case occupancy is N. Batch work includes input validation/copying, m routed old-value lookups, scans of their occupied leaves, sorting and serialization of touched leaves, and copying affected internal child maps. It is not a dataset-independent O(d) bound.','body'),
      ('Log composition takes ancestry traversal plus O(p + u log u), encoded-value comparisons and output copying/serialization. Merkle work depends on visited node pairs, child-slot sorting and examined leaf entries, plus value comparisons and sorted output. Both public version-pair modes perform ancestry work; a reverse query can first traverse to genesis in the unsuccessful direction. Output costs are at least proportional to s. Larger JSON payloads add comparison/copying costs that scalar-only benchmarks do not characterize.','body'),
      ('The SQLite repository eagerly loads historical nodes, changesets and commits into memory. It is a durable resident object model; retained history must fit the available memory. Open/verification scales with retained payloads, and no disk-page cache or eviction policy is implemented. Atomic SQLite persistence is distinct from untested production concurrency and operational guarantees.','body'),
    ]
    return [dict(kind=k,text=t) for t,k in texts]


def supplement(data):
    out=[]
    def p(t,k='body'):out.append(dict(kind=k,text=t))
    def tab(n,c,h,r,w):out.append(dict(kind='table',number=n,caption=c,headers=h,rows=r,widths=w))
    p('APPENDIX B. ADDITIONAL ANALYSES AND CORRECTNESS REVISION','h1')
    p('Tables XII-XV report additional analyses of archived measurements. They do not represent reruns on repaired code. Supporting values, paired ratios and source checksums are in evidence/referee-analysis-20261003. Quartiles use linear interpolation. Main threshold scores retain equal case weighting and the original frozen selection.')
    tab(12,'Fresh-process forced-Merkle startup and diff; milliseconds, median [Q1, Q3], three blocks per seed. Total is computed per recorded open-plus-diff row',
        ['Profile / seed suffix','Open / verify ms','Diff ms','Total ms'],
        [[('Repeated key' if r['locality']=='repeated-key' else 'Spread')+' / '+str(r['seed'])[-2:],fmt(r['open_ms'],1),fmt(r['diff_ms'],1),fmt(r['total_ms'],1)] for r in data['startup']], [.24,.26,.24,.26])
    p('Seed suffixes 21-23 denote 20261021-20261023. These cases use 65,536 operations; repeated-key histories have 10k rows/H256 and spread histories 100k/H64. Open/verify occurs before diff and the filesystem cache was not cleared. Adding separate open and diff medians would not produce the median total shown here.')
    g=data['geometry']
    tab(13,'Fixed-geometry work and costs on the single 10k-row workload; seven measured trials, exploratory fixed execution order',
        ['b / d; buckets; E[leaf]','Diff ms [Q1, Q3]','MiB','Node pairs / leaf entries'],
        [[f"{r['branching_factor']} / {r['tree_depth']}; {int(r['leaf_buckets']):,}; {float(r['expected_leaf_occupancy']):.2f}",
          fmt([float(r['diff_ms_'+a]) for a in ('median','p25','p75')]),f"{float(r['storage_bytes_median'])/2**20:.2f}",
          f"{float(r['nodes_compared_median']):.0f} / {float(r['leaf_entries_examined_median']):.0f}"] for r in g],[.28,.30,.12,.30])
    tab(14,'Whole-worker process-tree peak RSS by public dataset scale; MiB, median [Q1, Q3], seven measured trials; H10 with 0.1% changes per commit',
        ['Model','10k records','100k records','1M records'],
        [[{'Revon-M (forced Merkle)':'Revon-M','Dolt':'Dolt SQL','Dolt (bulk import)':'Dolt CSV'}.get(m,m)]+[fmt(next(r['MiB'] for r in data['rss'] if r['model']==m and r['rows']==n),1) for n in (10000,100000,1000000)] for m in ('Revon-H','Revon-M (forced Merkle)','Dolt','Dolt (bulk import)','Log-only','Snapshot')],[.19,.27,.27,.27])
    p('The 10 ms RSS sampler covers the worker process tree, including setup, workload/oracle state and adapter children. These are not isolated product-memory measurements. Page faults and paging were not measured; available RAM at launch cannot establish their contribution to latency growth.')
    tab(15,'Seed-specific warmed log/Merkle paired block ratios and same-path selector/forced controls; median [Q1, Q3], five blocks per history',
        ['Profile / operations / seed','Log / Merkle','Same-path H / forced'],
        [[('Repeat' if r['locality']=='repeated-key' else 'Spread')+f" / {r['operations']:,} / {str(r['seed'])[-2:]}",fmt(r['log_over_merkle'],3),fmt(r['same_path_selector_over_forced'],3)] for r in data['paired'] if r['condition']=='warmed-built'],[.38,.30,.32])
    p('Each same-path summary pools the five selectors within a single history and measured block set; these correlated ratios are diagnostics, not independent samples. Fresh-process paired ratios and every block value remain in the analysis file. The original ratios of marginal medians are distinct from these paired summaries. No causal benefit is inferred from a selector appearing faster than the forced path it invokes.')
    p('Evidence synthesis. Original T4096 workflows compare H with forced Merkle on shared representations. The cached threshold study selects T16384 among predefined candidates, yet always-log has the lower score on both splits. The single-seed extension has a non-monotonic ordering. The separate three-history pilot shows different path preferences across confounded profiles and does not validate a replacement policy. Query blocks are nested within histories; none of these studies supplies independent Linux hardware replication.')
    p('Correctness repair and compatibility','h2')
    p('The archived general JSON API retained mutable aliases and used Python equality, allowing historical mutation and suppressing transitions such as true to 1. The reported benchmark adapters used immutable string payloads, so these counterexamples do not demonstrate corruption of their retained measurements. The subsequent repair detaches containers and uses encoded identity. Regression checks exercise full/incremental writes, input/read/diff/diagnostic mutation, forward/reverse/cancelled transitions, null/absence, stored hashes and SQLite reopen.')
    p('The v1 encoding and on-disk schema are unchanged. A repository written by the original code reopens with unchanged root and commit identities; representative string histories produce identical roots before and after repair. New writes reject Python-only tuples and coercible non-string object keys rather than silently converting them. Existing JSON payloads remain readable. Previously discarded updates or mutations absent from persisted history cannot be reconstructed by this repair.')
    overhead_path=ROOT/'evidence/referee-repair-overhead-20261003/summary.json'
    if not overhead_path.exists():raise RuntimeError('Complete repair overhead evidence before building manuscripts')
    overhead=json.loads(overhead_path.read_text())
    tab(16,'Bounded repair check: median paired repaired/original latency ratio; five measured repository pairs per profile after one warm-up pair',
        ['String workload','Commit','Log diff','Merkle diff','H diff','Checkout'],
        [[profile]+[f"{next(r['median_paired_after_over_before'] for r in overhead if r['profile']==profile and r['metric']==m):.3f}" for m in ('commit_ms','log_ms','merkle_ms','hybrid_ms','checkout_ms')] for profile in ('10k-spread-h10','10k-repeated-h50','100k-spread-h10')],[.30,.14,.14,.14,.14,.14])
    p('The repair check alternates original/repaired order, uses b8-d4/T4096, fixed string workloads and Python hash seed 20261003, and checks canonical outputs and reopen. Timed reads include output materialization. Each variant/block builds its own SQLite repository; the five pairs share one deterministic workload and host. Ratios are descriptive and do not extrapolate to nested JSON, million-record workloads or another operating system. Source snapshots, configuration, raw timings, compatibility checks and file hashes are retained in evidence/referee-repair-overhead-20261003. Historical performance tables and figures remain explicitly measurements of their original archived revisions; they are not silently reassigned to repaired code.')
    checkout=[r['median_paired_after_over_before'] for r in overhead if r['metric']=='checkout_ms']
    hybrid=[r['median_paired_after_over_before'] for r in overhead if r['metric']=='hybrid_ms']
    p(f'The repair is not cost-free: paired checkout ratios span {min(checkout):.3f}-{max(checkout):.3f} and hybrid-diff ratios {min(hybrid):.3f}-{max(hybrid):.3f} in these three profiles. Other ratios vary in both directions. The limited check does not establish statistical equivalence or replace the original campaign; historical absolute timings should not be advertised as current-code performance.')
    return out


if __name__=='__main__':
    a=analysis();print(json.dumps(dict(static_scores=a['static_scores'],startup_cases=len(a['startup']),rss_groups=len(a['rss']),pilot_groups=len(a['paired'])),indent=2))
