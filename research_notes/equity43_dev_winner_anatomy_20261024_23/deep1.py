import json, statistics as st
from collections import Counter
from datetime import datetime

d = json.load(open('/tmp/anat/trade_ledger.json'))
def pt(s): return datetime.fromisoformat(s)

closed_taken = [r for r in d if r['taken_4bps'] and not r['censored']]
closed_taken.sort(key=lambda r: -r['net_r_4bps'])
assert len(closed_taken) == 187
top5, rest = closed_taken[:5], closed_taken[5:]
tot_net = sum(r['net_r_4bps'] for r in closed_taken)
tot_gross = sum(r['gross_r'] for r in closed_taken)
print(f"TAKEN CLOSED 187: net4 sum {tot_net:+.4f}R gross sum {tot_gross:+.4f}R")
print(f"top5 net {sum(r['net_r_4bps'] for r in top5):+.4f} rest net {sum(r['net_r_4bps'] for r in rest):+.4f}")

print("\n== (A) census: reason x tp1_hit (taken closed 187) ==")
for reason in sorted(set(r['reason'] for r in closed_taken)):
    for tp in (True, False):
        g = [r for r in closed_taken if r['reason']==reason and r['tp1_hit']==tp]
        if g: print(f"  {reason:12s} tp1={tp!s:5s} n={len(g):3d} net4 {sum(r['net_r_4bps'] for r in g):+.4f} gross {sum(r['gross_r'] for r in g):+.4f} pos {sum(1 for r in g if r['net_r_4bps']>0)}")
print("reason totals:", Counter(r['reason'] for r in closed_taken))
print("tp1_hit totals:", Counter(r['tp1_hit'] for r in closed_taken))

print("\n== hold_bars / stop width / realized-vs-planned ==")
def stats(g, name):
    hb=[r['hold_bars'] for r in g]; sw=[(r['entry']-r['stop'])/r['entry']*100 for r in g]
    print(f"  {name}: hold med {st.median(hb)} range {min(hb)}..{max(hb)} | stopwidth% med {st.median(sw):.2f} range {min(sw):.2f}..{max(sw):.2f}")
stats(closed_taken,'ALL187'); stats(top5,'TOP5'); stats(rest,'REST182')
losers=[r for r in closed_taken if r['gross_r']<0]
print(f"  gross losers: {len(losers)}; gross < -1.0R: {sum(1 for r in losers if r['gross_r']<-1.0)}; < -1.1R: {sum(1 for r in losers if r['gross_r']<-1.1)}; worst gross {min(r['gross_r'] for r in closed_taken):+.4f}")
stop_exits=[r for r in closed_taken if r['reason']=='stop']
print(f"  stop exits gross range {min(r['gross_r'] for r in stop_exits):+.4f}..{max(r['gross_r'] for r in stop_exits):+.4f}; stop exits with tp1_hit (protected path): {sum(1 for r in stop_exits if r['tp1_hit'])}")
print(f"  net4 by year: {Counter(r['entry_time'][:4] for r in closed_taken)}")
for y in ('2024','2025','2026'):
    g=[r for r in closed_taken if r['entry_time'][:4]==y]
    if g: print(f"    {y}: n={len(g)} net4 {sum(r['net_r_4bps'] for r in g):+.4f}")

print("\n== (B) winner timelines + matched counterexamples ==")
for w in top5:
    print(f"  WIN {w['symbol']:5s} sig {w['signal_time'][:16]} entry {w['entry_time'][:16]} @ {w['entry']:.2f} stop {w['stop']:.2f} tp1 {w['tp1']:.2f} exit {str(w['exit_time'])[:16]} synth {w['exit_synth']:.2f} hold {w['hold_bars']} reason {w['reason']} tp1hit {w['tp1_hit']} rs {w['rs']:.4f} sector {w['sector']} gross {w['gross_r']:+.4f} net4 {w['net_r_4bps']:+.4f}")
    cands=[r for r in rest if r['sector']==w['sector'] and r['net_r_4bps']<0]
    if not cands: cands=[r for r in rest if r['net_r_4bps']<0]
    m=min(cands, key=lambda r: abs(r['rs']-w['rs']))
    print(f"    MATCHED CX {m['symbol']:5s} sig {m['signal_time'][:16]} entry @ {m['entry']:.2f} rs {m['rs']:.4f} (d={abs(m['rs']-w['rs']):.4f}) sector {m['sector']} reason {m['reason']} tp1hit {m['tp1_hit']} hold {m['hold_bars']} net4 {m['net_r_4bps']:+.4f}")

print("\n== sector counts ==")
print("  top5:", Counter(r['sector'] for r in top5), "| rest182:", Counter(r['sector'] for r in rest))
print("  SEMIS in rest182:", sum(1 for r in rest if r['sector']=='SEMIS'))

print("\n== (D) skip census recompute ==")
closed_all=[r for r in d if not r['censored']]
print("  closed candidates:", len(closed_all), Counter(r['disposition_4bps_c1'] for r in closed_all))
for thr in (2.0,):
    exc=[r for r in closed_all if r['gross_r']>=thr]
    print(f"  exceptional >=+{thr}R gross standalone: {len(exc)}", Counter(r['disposition_4bps_c1'] for r in exc))
