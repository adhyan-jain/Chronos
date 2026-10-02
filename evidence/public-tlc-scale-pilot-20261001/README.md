# Scale resource pilot

One measured trial and no warm-ups for each of the six existing adapters at 100,000 and 1,000,000 public records. All twelve executions and 132 historical-state checks passed. This established that one-million-record workflows were feasible within the 900-second worker limit on this host.

Do not pool these timings with the repeated evaluation or plot them as repeated results. Verification/memory-retention code was refined during this pilot; the 100k pilot overlapped briefly with harness regression checks. These pilot timings are therefore resource estimates, not final comparison evidence. The repeated study runs sequentially with frozen, archived source and no concurrent regression runs. The internal spec's payload_bytes=8 in pilot records is a validation placeholder, not an actual fixed record length.
