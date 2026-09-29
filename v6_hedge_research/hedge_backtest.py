"""Hedge overlay backtests per HEDGE_SPEC.md (frozen). Four hedges on $100k QQQ B&H proxy.

Puts: Black-Scholes estimated (documented approximation). SH: exact prices.
All signals at close t execute at open t+1. No lookahead.
"""
import os, pickle, json, math
import numpy as np
import pandas as pd
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")

# ---- pre-specified params (HEDGE_SPEC.md) ----
R = 0.04          # risk-free
Q = 0.006         # QQQ dividend yield
PUT_T = 30 / 365  # 30 calendar days
OTM = 0.95        # ~5% OTM strike
PUT_BUDGET = 0.005   # 0.5% of portfolio per roll
SH_ALLOC = 0.10       # 10% of portfolio
COST = 0.0004         # 4 bps each way (SH + initial QQQ buy)
SIGMA_SCALE = 1.0     # primary; sensitivity run at 1.15

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bs_put(S, K, T, sigma, r=R, q=Q):
    """European put. T in years; if T<=0 returns intrinsic."""
    if T <= 0:
        return max(K - S, 0.0)
    if sigma <= 0 or S <= 0:
        return max(K - S, 0.0)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * math.exp(-q * T) * norm_cdf(-d1)

def load():
    with open(os.path.join(CACHE, "data.pkl"), "rb") as f:
        d = pickle.load(f)
    for k in ("qqq", "spy", "sh", "vix"):
        for col in ("Open", "Close"):
            d[k][col] = d[k][col].ffill()
        d["vix"]["Close"] = d["vix"]["Close"].ffill()
    return d

def year_of(ts): return ts.year

class PutHedge:
    """Hedge A (regime-timed) or B (always-on). BS-estimated QQQ puts."""
    def __init__(self, timed, sigma_scale=SIGMA_SCALE, name=""):
        self.timed = timed; self.sigma_scale = sigma_scale; self.name = name
        self.reset()

    def reset(self):
        self.cash = 0.0            # cumulative hedge cash flow (negative = spent)
        self.contracts = 0; self.K = 0.0; self.buy_date = None; self.expiry = None
        self.premium_paid = 0.0; self.payouts = 0.0
        self.buys = 0; self.rolls = 0; self.sells = 0; self.skips = 0
        self.mtm = []              # daily mark-to-market value of open position

    def _put_price(self, S, K, date, vix_close, T=None):
        if T is None:
            T = max((self.expiry - date).days, 0) / 365.0
        return bs_put(S, K, T, vix_close / 100.0 * self.sigma_scale) * 100  # per contract

    def _buy(self, i, df, port_val, is_roll=False):
        S = float(df["qqq"]["Open"].iloc[i])
        vix = float(df["vix"]["Close"].iloc[i - 1])
        K = round(OTM * S, 2)
        px = bs_put(S, K, PUT_T, vix / 100.0 * self.sigma_scale) * 100
        n = int((PUT_BUDGET * port_val) // px)
        if n < 1 or px <= 0:
            self.skips += 1; return False
        cost = n * px
        self.cash -= cost; self.premium_paid += cost
        self.contracts = n; self.K = K
        self.buy_date = df["qqq"].index[i].date()
        self.expiry = self.buy_date + timedelta(days=30)
        if is_roll: self.rolls += 1
        else: self.buys += 1
        return True

    def _sell(self, i, df):
        S = float(df["qqq"]["Open"].iloc[i])
        vix = float(df["vix"]["Close"].iloc[i - 1])
        date = df["qqq"].index[i].date()
        T = max((self.expiry - date).days, 0) / 365.0
        px = bs_put(S, self.K, T, vix / 100.0 * self.sigma_scale) * 100
        proceeds = self.contracts * px
        self.cash += proceeds; self.payouts += proceeds
        self.sells += 1
        self.contracts = 0; self.K = 0.0; self.buy_date = None; self.expiry = None

    def run(self, df, long_equity):
        self.reset()
        n = len(df["qqq"]); idx = df["qqq"].index
        regime = df["regime"]
        mtm = np.zeros(n); cash_ts = np.zeros(n)
        for i in range(n):
            date = idx[i].date()
            port_val = long_equity[i] + self.cash + (mtm[i-1] if i > 0 else 0.0)
            if i > 0:  # execute decisions made at close i-1
                if self.contracts > 0:
                    days_held = (date - self.buy_date).days
                    if self.timed and regime.iloc[i-1] != "RISK-OFF":
                        self._sell(i, df)                       # regime exit
                    elif days_held >= 30:
                        self._sell(i, df)                       # roll: sell old...
                        pv = long_equity[i] + self.cash
                        self._buy(i, df, pv, is_roll=True)      # ...buy new
                    # else hold
                else:
                    # no position: (re)try every day — timed only while RISK-OFF,
                    # always-on every day (a skip just delays, never abandons)
                    if self.timed and regime.iloc[i-1] != "RISK-OFF":
                        pass
                    else:
                        pv = long_equity[i] + self.cash
                        self._buy(i, df, pv)
            # mark to market at close
            if self.contracts > 0:
                S = float(df["qqq"]["Close"].iloc[i]); vix = float(df["vix"]["Close"].iloc[i])
                T = max((self.expiry - date).days, 0) / 365.0
                mtm[i] = self.contracts * bs_put(S, self.K, T, vix/100.0*self.sigma_scale) * 100
            cash_ts[i] = self.cash
        self.mtm = mtm
        return cash_ts + mtm

class SHHedge:
    """Hedge C (regime-timed) or D (always-on, monthly rebalance). Exact prices."""
    def __init__(self, timed, name=""):
        self.timed = timed; self.name = name; self.reset()

    def reset(self):
        self.shares = 0.0; self.cash = 0.0
        self.buys = 0; self.sells = 0; self.rebals = 0

    def run(self, df, long_equity):
        self.reset()
        n = len(df["qqq"]); idx = df["qqq"].index
        regime = df["regime"]; sh = df["sh"]
        mtm = np.zeros(n); cash_ts = np.zeros(n)
        for i in range(n):
            if i > 0:
                px = float(sh["Open"].iloc[i])
                port_val = long_equity[i] + self.cash + self.shares * float(sh["Close"].iloc[i-1])
                if self.timed:
                    if self.shares > 0 and regime.iloc[i-1] != "RISK-OFF":
                        self.cash += self.shares * px * (1 - COST); self.shares = 0.0; self.sells += 1
                    elif self.shares == 0 and regime.iloc[i-1] == "RISK-OFF" and (i < 2 or regime.iloc[i-2] != "RISK-OFF"):
                        target = SH_ALLOC * port_val
                        self.shares = target * (1 - COST) / px
                        self.cash -= target; self.buys += 1
                else:
                    if i == 1:
                        target = SH_ALLOC * port_val
                        self.shares = target * (1 - COST) / px
                        self.cash -= target; self.buys += 1
                    else:
                        # month-end rebalance: signal at last trading day of month
                        prev_month = idx[i-1].month
                        if idx[i].month != prev_month:
                            cur = self.shares * px
                            tgt = SH_ALLOC * port_val
                            diff = tgt - cur
                            if abs(diff) > 1.0:
                                self.shares += diff * (1 - COST) / px
                                self.cash -= diff; self.rebals += 1
            mtm[i] = self.shares * float(sh["Close"].iloc[i])
            cash_ts[i] = self.cash
        self.mtm = mtm
        return cash_ts + mtm

def max_dd(equity):
    eq = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return float(dd.min()), int(np.argmin(dd))

def main():
    df = load()
    idx = df["qqq"].index
    n = len(idx)
    q = df["qqq"]
    # long leg: $100k QQQ B&H at first open, 4bps
    shares = 100000 * (1 - COST) / float(q["Open"].iloc[0])
    long_equity = shares * q["Close"].values

    results = {}
    hedges = [
        PutHedge(timed=True, name="A_regime_puts"),
        PutHedge(timed=False, name="B_always_puts"),
        SHHedge(timed=True, name="C_regime_SH"),
        SHHedge(timed=False, name="D_always_SH"),
    ]
    for h in hedges:
        hedge_eq = h.run(df, long_equity)
        combined = long_equity + hedge_eq
        dd_c, _ = max_dd(combined); dd_l, _ = max_dd(long_equity)
        # year splits: cash-flow years + mtm change attribution
        by_year = {}
        for y in sorted(set(year_of(t) for t in idx)):
            mask = np.array([year_of(t) == y for t in idx])
            # approximate: hedge P&L in year = end-start of hedge equity within year
            he = hedge_eq[mask]
            by_year[str(y)] = round(float(he[-1] - he[0]), 2)
        res = {
            "net_pnl": round(float(hedge_eq[-1]), 2),
            "ann_drag_pct": round(float(hedge_eq[-1]) / 100000 / (n / 252) * 100, 3),
            "by_year": by_year,
            "max_dd_combined_pct": round(dd_c * 100, 2),
            "max_dd_longonly_pct": round(dd_l * 100, 2),
            "end_combined": round(float(combined[-1]), 2),
            "end_longonly": round(float(long_equity[-1]), 2),
            "trades": {"buys": h.buys, "sells": h.sells,
                       "rolls": getattr(h, "rolls", 0), "rebalances": getattr(h, "rebals", 0),
                       "skips": getattr(h, "skips", 0)},
        }
        if isinstance(h, PutHedge):
            res["premium_paid"] = round(h.premium_paid, 2)
            res["payouts"] = round(h.payouts, 2)
        results[h.name] = res
        print(f"{h.name}: net={res['net_pnl']:+.0f} drag={res['ann_drag_pct']:+.3f}%/yr "
              f"DD {res['max_dd_longonly_pct']:.1f}%->{res['max_dd_combined_pct']:.1f}% trades={res['trades']}")

    # sensitivity: puts at 1.15x VIX (spec) + sweep to locate breakeven
    for timed, nm in [(True, "A_regime_puts_sens115"), (False, "B_always_puts_sens115")]:
        h = PutHedge(timed=timed, sigma_scale=1.15, name=nm)
        hedge_eq = h.run(df, long_equity)
        combined = long_equity + hedge_eq
        dd_c, _ = max_dd(combined)
        results[nm] = {"net_pnl": round(float(hedge_eq[-1]), 2),
                       "premium_paid": round(h.premium_paid, 2),
                       "payouts": round(h.payouts, 2),
                       "max_dd_combined_pct": round(dd_c*100, 2),
                       "trades": {"buys": h.buys, "sells": h.sells, "rolls": h.rolls, "skips": h.skips}}
        print(f"{nm}: net={results[nm]['net_pnl']:+.0f} prem={h.premium_paid:.0f} pay={h.payouts:.0f}")
    sweep = {}
    for sc in [1.05, 1.10]:
        h = PutHedge(timed=False, sigma_scale=sc, name="sweep")
        he = h.run(df, long_equity)
        sweep[str(sc)] = {"net_pnl": round(float(he[-1]), 2),
                          "premium_paid": round(h.premium_paid, 2),
                          "payouts": round(h.payouts, 2)}
    results["_sweep_sigma_B"] = sweep
    print("sigma sweep B:", sweep)

    # regime stats
    reg = df["regime"]
    results["_meta"] = {
        "test_days": n,
        "riskoff_days": int((reg == "RISK-OFF").sum()),
        "regime_counts": reg.value_counts().to_dict(),
        "window": f"{idx[0].date()}->{idx[-1].date()}",
        "sigma_scale_primary": SIGMA_SCALE,
    }
    with open(os.path.join(HERE, "hedge_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("wrote hedge_results.json")

if __name__ == "__main__":
    main()
