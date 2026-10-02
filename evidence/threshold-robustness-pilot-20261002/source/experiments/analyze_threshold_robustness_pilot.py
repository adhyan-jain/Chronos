"""Assess the isolated pilot without changing manuscripts or selecting a default."""
from __future__ import annotations
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def median(values):
    return statistics.median(values)


def quartiles(values):
    values=sorted(values)
    def q(f):
        x=(len(values)-1)*f;i=int(x);j=min(i+1,len(values)-1)
        return values[i]*(1-(x-i))+values[j]*(x-i)
    return q(.25),q(.75)


def main(directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    results=json.loads((directory/'results.json').read_text())
    manifest=json.loads((directory/'manifest.json').read_text())
    audit=json.loads((directory/'audit.json').read_text())
    failures=json.loads((directory/'failures.json').read_text())
    protected=json.loads((directory/'protected_after.json').read_text())
    summaries=[]
    for case in results:
        groups=defaultdict(list)
        for row in case['records']+case['fresh_records']:
            if row['trial_kind']=='measured':groups[(row['cache_condition'],row['strategy'],row['threshold'])].append(row)
        for (cache,strategy,threshold),records in groups.items():
            values=[r['diff_ms'] for r in records];p25,p75=quartiles(values)
            summaries.append(dict(case=case['spec']['name'],rows=case['spec']['rows'],commits=case['spec']['commits'],
                locality=case['spec']['locality'],seed=case['spec']['seed'],operations=case['spec']['operations'],
                cache_condition=cache,strategy=strategy,threshold=threshold,n_queries=len(records),
                median_ms=median(values),p25_ms=p25,p75_ms=p75,decision_probe_median_ms=median(r['decision_probe_ms'] for r in records),
                open_verify_median_ms=median(r['open_verify_ms'] for r in records) if cache=='fresh-process-reopened' else '',
                nodes_compared=records[0]['nodes_compared'],matching_subtrees_skipped=records[0]['matching_subtrees_skipped'],
                leaf_entries_examined=records[0]['leaf_entries_examined'],log_operations_examined=records[0]['log_operations_examined'],
                distinct_keys_touched=case['distinct_keys_touched'],final_diff_entries=case['final_diff_entries'],
                operations_per_distinct_key=case['operations_per_distinct_key'],output_bytes=case['final_diff_bytes']))
    if not summaries:
        (directory/'ASSESSMENT.md').write_text('# Threshold robustness pilot\n\nD. Resource-limited: no complete cases. See failures.json.\n')
        return
    with (directory/'summary.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    lookup={(r['case'],r['cache_condition'],r['strategy'],r['threshold']):r for r in summaries}
    ratios=[]
    for case in results:
        for cache in ('warmed-built','fresh-process-reopened'):
            if (case['spec']['name'],cache,'log',0) not in lookup:continue
            log=lookup[(case['spec']['name'],cache,'log',0)]
            merkle=lookup[(case['spec']['name'],cache,'merkle',0)]
            all_records=case['records'] if cache=='warmed-built' else case['fresh_records']
            blocks=sorted({r['block'] for r in all_records if r['trial_kind']=='measured'})
            paired=[]
            for block in blocks:
                l=next(r['diff_ms'] for r in all_records if r['trial_kind']=='measured' and r['block']==block and r['strategy']=='log')
                m=next(r['diff_ms'] for r in all_records if r['trial_kind']=='measured' and r['block']==block and r['strategy']=='merkle')
                paired.append(l/m)
            candidates={str(t):lookup[(case['spec']['name'],cache,'hybrid',t)]['median_ms']/log['median_ms'] for t in (4096,16384,32768,65536,131072)}
            ratios.append(dict(case=case['spec']['name'],rows=case['spec']['rows'],commits=case['spec']['commits'],
                locality=case['spec']['locality'],seed=case['spec']['seed'],operations=case['spec']['operations'],cache_condition=cache,
                log_ms=log['median_ms'],merkle_ms=merkle['median_ms'],log_over_merkle=log['median_ms']/merkle['median_ms'],
                paired_block_ratios=paired,median_paired_block_ratio=median(paired),
                hybrid_over_always_log=candidates,
                gain_H131072_vs_H16384=1-lookup[(case['spec']['name'],cache,'hybrid',131072)]['median_ms']/lookup[(case['spec']['name'],cache,'hybrid',16384)]['median_ms'],
                log_iqr_ms=[log['p25_ms'],log['p75_ms']],merkle_iqr_ms=[merkle['p25_ms'],merkle['p75_ms']],
                distinct_keys_touched=case['distinct_keys_touched'],final_diff_entries=case['final_diff_entries']))
    (directory/'paired_ratios.json').write_text(json.dumps(ratios,indent=2))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140,'savefig.dpi':220})
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
    palette=['#0072B2','#D55E00','#009E73']
    for ax,locality in zip(axes,('repeated-key','spread')):
        for seed,color in zip(manifest['seeds'],palette):
            points=sorted([r for r in ratios if r['cache_condition']=='warmed-built' and r['locality']==locality and r['seed']==seed],key=lambda r:r['operations'])
            ax.plot([r['operations']/1024 for r in points],[r['log_over_merkle'] for r in points],marker='o',color=color,label=f'Seed {seed}')
        ax.axhline(1,color='#444444',linestyle='--',linewidth=1)
        ax.axhspan(.95,1/.95,color='#888888',alpha=.12)
        ax.set_title('10k rows / 256 commits / repeated keys' if locality=='repeated-key' else '100k rows / 64 commits / spread keys',fontsize=10)
        ax.set_xticks([32,64,128],['32,768','65,536','131,072'])
        ax.set_xlabel('Accumulated operations');ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Forced log / forced Merkle median latency')
    axes[1].legend(fontsize=8)
    fig.suptitle('Independent pilot histories: warmed queries',fontsize=13)
    fig.text(.5,.01,'Below 1: log faster. Above 1: Merkle faster. Shading is a 5% practical screen, not a confidence interval.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(directory/'forced_path_ratios.png');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
    labels=['Log','Merkle','H 4k','H 16k','H 32k','H 65k','H 131k']
    for ax,locality in zip(axes,('repeated-key','spread')):
        for seed,color in zip(manifest['seeds'],palette):
            case=next((c for c in results if c['spec']['locality']==locality and c['spec']['seed']==seed and c['spec']['operations']==65536),None)
            if not case:continue
            cache='warmed-built';log=lookup[(case['spec']['name'],cache,'log',0)]['median_ms']
            ys=[lookup[(case['spec']['name'],cache,s,t)]['median_ms']/log for s,t in manifest['configs']]
            ax.plot(range(7),ys,marker='o',color=color,label=f'Seed {seed}')
        ax.axhline(1,color='#444444',linestyle='--');ax.set_xticks(range(7),labels,rotation=35,ha='right')
        ax.set_title('Repeated keys' if locality=='repeated-key' else 'Spread keys');ax.set_xlabel('Strategy / threshold');ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Median latency / always-log latency')
    axes[1].legend(fontsize=8);fig.suptitle('Does a larger threshold beat always-log? 65,536 operations',fontsize=13)
    fig.tight_layout();fig.savefig(directory/'selector_vs_always_log.png');plt.close(fig)
    fresh=[r for r in ratios if r['cache_condition']=='fresh-process-reopened']
    if fresh:
        fig,axes=plt.subplots(1,2,figsize=(9,4),sharey=True)
        for ax,locality in zip(axes,('repeated-key','spread')):
            for seed,color in zip(manifest['seeds'],palette):
                pair=[next((r for r in ratios if r['locality']==locality and r['seed']==seed and r['operations']==65536 and r['cache_condition']==cache),None) for cache in ('warmed-built','fresh-process-reopened')]
                if all(pair):ax.plot([0,1],[r['log_over_merkle'] for r in pair],marker='o',color=color,label=f'Seed {seed}')
            ax.axhline(1,color='#444444',linestyle='--');ax.set_xticks([0,1],['Warmed built','Fresh process\nreopened'])
            ax.set_title('Repeated keys' if locality=='repeated-key' else 'Spread keys');ax.grid(axis='y',alpha=.2)
        axes[0].set_ylabel('Forced log / forced Merkle median latency');axes[1].legend(fontsize=8)
        fig.suptitle('Fresh-process sensitivity at 65,536 operations',fontsize=13)
        fig.text(.5,.01,'Diff time only. Reopen eagerly loads and verifies all objects; OS filesystem cache is not cleared.',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(directory/'cache_sensitivity.png');plt.close(fig)
    resource=[r for c in results for r in c['resources']]
    total_seconds=sum(c['total_wall_seconds'] for c in results)
    peak=max(r['peak_rss_bytes'] for r in resource)
    lines=['# Isolated threshold robustness pilot assessment','',
        '**Exploratory pilot only. No paper, production source, default threshold or prior evidence was changed.**','',
        '## Execution and scope','',
        f"Completed {audit['completed_cases']}/{audit['planned_cases']} independent repositories; {audit['warm_measured']} measured warmed queries and {audit['fresh_queries']} measured fresh-process queries. Two warm-up blocks and five measured warmed blocks per configuration; three fresh-process blocks at 65,536 operations. Three seeds per condition are repository replications; query repetitions are nested observations.",
        f"Failures: {audit['failures']}; not run: {audit['not_run']}. All completed queries matched the common semantic oracle: {audit['all_correct']}. Completed case wall time: {total_seconds/60:.1f} min; maximum sampled worker RSS: {peak/1024**2:.0f} MiB.",'',
        f"Environment: {manifest['platform']}; Python {manifest['python'].split()[0]}; psutil {manifest['psutil_version']}; {manifest['physical_cpus']} physical/{manifest['logical_cpus']} logical CPUs; {manifest['ram']['total']/1024**3:.2f} GiB RAM. Physical hardware is the existing Windows host. No Linux/cloud replication.",'',
        '## Forced paths: every seed shown','',
        'Log/Merkle below 1 favours log; above 1 favours Merkle. These are ratios of within-repository medians. Query IQRs are timing dispersion, not across-history confidence intervals. Full block-paired ratios are in paired_ratios.json.','',
        '| Profile | Operations | Seed | Cache | Log ms [IQR] | Merkle ms [IQR] | Log/Merkle | H131k gain vs H16k |',
        '|---|---:|---:|---|---|---|---:|---:|']
    for row in sorted(ratios,key=lambda r:(r['locality'],r['operations'],r['cache_condition'],r['seed'])):
        lines.append(f"| {row['locality']} | {row['operations']:,} | {row['seed']} | {row['cache_condition']} | {row['log_ms']:.2f} [{row['log_iqr_ms'][0]:.2f}, {row['log_iqr_ms'][1]:.2f}] | {row['merkle_ms']:.2f} [{row['merkle_iqr_ms'][0]:.2f}, {row['merkle_iqr_ms'][1]:.2f}] | {row['log_over_merkle']:.3f} | {100*row['gain_H131072_vs_H16384']:+.1f}% |")
    lines += ['', '## Selector versus always-log', '', '| Profile | Operations | Seed | Cache | H4k/log | H16k/log | H32k/log | H65k/log | H131k/log |', '|---|---:|---:|---|---:|---:|---:|---:|---:|']
    for row in sorted(ratios,key=lambda r:(r['locality'],r['operations'],r['cache_condition'],r['seed'])):
        values=' | '.join(f"{row['hybrid_over_always_log'][str(t)]:.3f}" for t in (4096,16384,32768,65536,131072))
        lines.append(f"| {row['locality']} | {row['operations']:,} | {row['seed']} | {row['cache_condition']} | {values} |")
    groups=defaultdict(list)
    for row in ratios:groups[(row['locality'],row['operations'],row['cache_condition'])].append(row)
    lines += ['', '## Practical interpretation', '', 'The 5% screen was frozen as an exploratory investigation criterion. It is not statistical significance or a certificate of robustness.']
    resolved_locality_difference=False
    robust_benefit=False
    for (locality,operations,cache),rows in sorted(groups.items()):
        winners=['log' if r['log_over_merkle']<.95 else 'Merkle' if r['log_over_merkle']>1/.95 else 'within 5% screen' for r in rows]
        gains=[r['gain_H131072_vs_H16384'] for r in rows]
        if len(rows)==3 and all(g>.05 for g in gains):robust_benefit=True
        lines.append(f"- {locality}, {operations:,}, {cache}: seed outcomes = {', '.join(winners)}; H131k versus H16k gains = {', '.join(f'{100*g:+.1f}%' for g in gains)}.")
    for o in (32768,65536,131072):
        a=groups.get(('repeated-key',o,'warmed-built'),[]);b=groups.get(('spread',o,'warmed-built'),[])
        if len(a)==len(b)==3 and ((all(r['log_over_merkle']<.95 for r in a) and all(r['log_over_merkle']>1/.95 for r in b)) or (all(r['log_over_merkle']>1/.95 for r in a) and all(r['log_over_merkle']<.95 for r in b))):resolved_locality_difference=True
    recommendation='D. The pilot was inconclusive or resource-limited.' if audit['failures'] or audit['not_run'] else 'B. A workload-sensitive selector deserves separate investigation.' if resolved_locality_difference else 'A. A larger replicated study is justified.' if robust_benefit else 'C. No convincing practical improvement appeared in this pilot.'
    lines += ['', '**Conclusion: '+recommendation+'**','',
        'The existing one-seed diagnostic ratios at 32,768 / 65,536 / 131,072 were 1.108 / 0.921 / 1.396. Compare these with the independent seed outcomes above; no old measurements are pooled into this pilot. Different seed, hash order, process state and resource conditions can contribute to differences.', '',
        'Distinct touched keys, final output sizes, mutation mix and traversal counters are recorded. The two profiles change both repository size and history length as well as locality. Therefore profile contrasts do not causally isolate locality or prove a better predictor. Any explanatory association remains a hypothesis.', '',
        '## Correctness, cache and limitations','',
        'Every timed output is compared with a common canonical oracle. Warm workers also verify reverse/identity diffs, three historical states and full repository integrity. Reopened workers verify persistent objects and their first diff before later correctness work. Canonical output materialization is included in diff timing; construction, opening, integrity, correctness and standalone decision probes are separate.',
        'The implementation eagerly decodes all persistent objects and verifies integrity on open. Fresh-process measurements therefore begin with a populated object model. They test new process/allocation state, not true cold filesystem IO. open_verify_ms and open_plus_diff_ms are retained; the latter excludes process startup.',
        'No default change, threshold selection, held-out validation, cross-machine replication or population confidence interval is claimed. Seven selector/path timings on each seed share a repository; they are not seven independent histories. No timing outliers are removed. Resource failures remain visible.', '',
        '## Follow-up recommendation and resource planning','',
        'If pursuing a larger study, first orthogonally vary locality while holding row count/history length constant; vary output size independently where feasible. Allocate fresh calibration and validation seeds, freeze selection before validation, and include always-log and forced-Merkle baselines. Use seed/repository-level paired uncertainty; use pilot dispersion to set replication targets rather than assuming three seeds suffice.',
        f'A 10-seed version of this exact scope would cost approximately {total_seconds/60*10/3:.1f} minutes on this host if resources and timings scale similarly, plus failures and setup; this is a rough planning estimate, not a guarantee. Peak sampled RSS was {peak/1024**2:.0f} MiB; additional free RAM is needed for the operating system and transient allocations. Follow-up Linux hardware testing must use a separate physical/cloud host and documented comparable conditions. It has not been launched.', '',
        '## Reproduction','', 'Run from C:\\Users\\admin\\Desktop\\Revon with the recorded interpreter. Resume only this frozen directory; a fresh run requires capturing a new protected_before.json baseline using the provided prepare script before creating its manifest.','',
        '```powershell', f"& '{manifest['python_executable']}' -m experiments.threshold_robustness_pilot --output '{directory}'", f"$env:PYTHONPATH = 'C:/Users/admin/AppData/Local/Temp/revon-revision-deps'", f"& 'C:/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m experiments.analyze_threshold_robustness_pilot --output '{directory}'", '```', '',
        'The run-local prepare_reproduction.py captures a fresh protected baseline for a new output directory. The archived source snapshot and SHA-256 manifest establish the exact experiment code. Do not rerun against changed sources and call it the same frozen experiment.', '',
        '## Files and protection','', f"Protected baseline recheck: {protected['passed']}; {protected['protected_files']} existing files checked; commits unchanged: {protected['commits_unchanged']}. New tracked-tree candidates are only the two experimental Python files; other new outputs remain in this local ignored directory. No commit, push or paid resources.", '',
        'See files_created.txt for the exact new output inventory, summary.csv for medians/IQRs and counters, raw_results.csv for all complete-case warm-up/measured queries, per-case queries.jsonl for resumable partial records, failures.json for incomplete/skipped cases, and source/ for frozen code.', '',
        '![Forced path ratios](forced_path_ratios.png)', '', '![Selector versus always-log](selector_vs_always_log.png)']
    if fresh:lines += ['', '![Cache sensitivity](cache_sensitivity.png)']
    if failures:lines += ['', '## Failure records', '', '```json', json.dumps(failures,indent=2), '```']
    (directory/'ASSESSMENT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (directory/'interpretation.json').write_text(json.dumps(dict(recommendation=recommendation,
        larger_threshold_consistent_gain=robust_benefit,profile_dependent_path_winner=resolved_locality_difference,
        independent_seeds_per_condition=3,total_case_seconds=total_seconds,peak_worker_rss_bytes=peak),indent=2))
    print(recommendation)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output.resolve())
