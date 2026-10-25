# K0.5 edge spike: is there a calibration edge on Kalshi after fees?

**Verdict: NO-GO.** On the held-out test part, none of the six pre-registered deciding segments had an after-fee edge whose corrected lower bound was above zero, and every deciding segment had the 300 events the rule asks for. The two exploratory Economics segments did not clear zero either. The test part was opened once, under pre-registration digest `465b8e2823a8…`, on 2026-10-25.

This is a result about the hypotheses that were tested, not a proof that no edge exists. Section 6 says what the study could and could not rule out.

## 1. The question and the rule

Does a price-based calibration edge exist on Kalshi's non-combo markets after fees, large enough to trade? The go rule (PLAN.md §6.9, strict, owner 2026-10-21) is: GO only if, on a later test period, the lower bound of the after-fee edge is above zero in at least one segment named before the test is looked at, over at least 300 independent events; for a maker the edge must hold under the pessimistic fill rule with the conservative maker fee (D13); and the bound is corrected for the number of segments named (D11, Bonferroni, 0.025 divided by the deciding segments). Otherwise no-go, or inconclusive (widen the data once, D15).

## 2. Data snapshot

| | |
|---|---|
| Source | Kalshi public API, production, GET only, no key: `/historical/*` for older days and the live endpoints for the newest. |
| Trade days | 2026-08-07 to 2026-10-22 (77 days, 773,545,156 trades, 18.08 GB), integrity checked by `verify` (0 problems, 6,013,382 of 6,013,382 checkable market volumes equal to the sum of their trades). |
| Markets | 63 live market days (5,139,170) plus 13,708,709 historical; the `markets` step was re-run on 2026-10-25 after the trades finished. |
| Combo markets | Skipped and counted (113,302,525 trades). |
| Window | Events opened on or after 2026-08-07 and closed before 2026-10-19, ending where the share of trades with no market record returns to its baseline (1.11% baseline, limit 1.61%; D17 as amended). 696,249,187 usable trades. |
| Split (fixed UTC dates, by event close time) | fit before 2026-09-29, validate before 2026-10-10, test after. Events: fit 15,999, validate 4,660, test 3,947, 1,260 dropped. |
| Sample | Stratified by category (D16 as amended): base share 0.0366 (Sports), Crypto 0.0441, Commodities 0.1321, Climate and Weather 0.3385, Financials 0.4627, every other category 1.0. 40,005,622 trades loaded. Pooled figures are weighted by one over the category's share. |
| Config digest | `250624cea865` (settings), pre-registration digest `465b8e2823a88cfae0b42d64349d6a0b3a5cf3d1bc26ee96248877c3736f81cf` (settings and segments). |

## 3. Method in brief

- Trades are grouped by **event**, the independent unit; intervals are a studentized cluster bootstrap over events (10,000 resamples).
- The **taker edge** is the outcome minus the price minus the taker fee, for the side the taker bought. The **maker edge** takes the other side of the same trades under two fill rules (optimistic: every trade fills the resting order, as if it were first in the queue every time; pessimistic: a trade fills it only if a later second saw the price trade strictly through its level, so the queue ahead of it must have been cleared) with the maker fee at the conservative share (D13). Fees follow the series' fee type and multiplier in force at each trade's time.
- The segments were chosen on the **validate part only**, listed with reasons, approved by the owner, and locked by hash before the test part was read. The test part was read once.

## 4. The benchmark ladder (fitted on the fit part)

| Step | Validate Brier | Test Brier | Test log loss |
|---|---|---|---|
| Raw price | 0.15837 | 0.12799 | 0.39252 |
| Price plus the price band's average miss | 0.15838 | 0.12789 | 0.39209 |

| Naive maker, conservative fee | Optimistic fill | Pessimistic fill |
|---|---|---|
| Validate part | +0.78 cents a contract | -0.34 |
| Test part | +0.91 | -0.32 |

The band correction improves the Brier score on the test part by 0.0001, which is negligible, and does nothing on the validate part. A naive maker earns under the optimistic fill rule and loses under the pessimistic one, in both parts. The two parts agree, so the pooled picture is stable: **the price is already close to the probability, and the gap between the two fill rules is larger than any edge.**

## 5. The segments

Six deciding segments, each at a one-sided tail of 0.00417; two exploratory (D18), reported at the same tail but not deciding. Edges are in cents a contract after fee, with the lower bound in brackets. "Validate" is what the segment looked like when it was chosen.

| # | Segment | Test events | Taker (lower) | Maker pessimistic (lower) | Maker optimistic | Validate, as chosen |
|---|---|---|---|---|---|---|
| 1 | Financials, yes at or under 30¢, taker buys NO | 924 | -1.67 (-10.60) | +0.07 (-8.44) | +1.16 | taker +6.39 (+1.05) |
| 2 | Financials, yes at or over 70¢, taker buys NO | 795 | +0.31 (-7.46) | -6.28 (-20.24) | -1.11 | maker +4.69 (-3.52) |
| 3 | Climate and Weather, yes at or under 30¢, taker buys NO | 390 | -0.40 (-13.89) | -1.39 (-6.15) | -0.10 | taker +1.49 (-0.71) |
| 4 | Climate and Weather, yes at or under 30¢, taker buys YES | 389 | -1.23 (-3.75) | -0.06 (-12.59) | +0.87 | maker +1.93 (-1.95) |
| 5 | Sports, all prices | 782 | -2.49 (-5.48) | +0.31 (-1.95) | +1.35 | no lower bound above zero |
| 6 | Crypto, all prices | 442 | -1.39 (-2.21) | -0.81 (-1.90) | +0.61 | no lower bound above zero |
| 7 | Economics, yes at or over 70¢, taker buys YES (exploratory) | 390 | +0.11 (-6.33) | -3.25 (-7.17) | -0.27 | taker +2.36 (+1.75) |
| 8 | Economics, yes at or over 70¢, taker buys NO (exploratory) | 261 | -0.81 (-4.93) | -2.79 (-29.61) | +0.44 | maker +5.82 (+2.06) |

What this shows:

- **Every segment that looked good on the validate part fell back to noise on the test part.** Financials taker-NO went from +6.39 (lower bound +1.05) to -1.67; Economics taker-YES from +2.36 (lower bound +1.75) to +0.11. This is what selecting from many cells looks like, and it is the reason the test part was held out.
- **The earlier "spectacular" cells were small-sample artefacts.** With the first 4% uniform sample, some Weather cells read z 13 to 65 on a few dozen events, and a Crypto favourite cell read +4.1 cents (z 3.2); with a sample large enough to hold 300 events they fell to z 2.6 to 3.1 and then, on the validate part of the final window, below zero. Nothing in this study should be quoted from a cell with fewer than about 300 events.
- **Sports and Crypto are well measured and show nothing.** Their taker lower bounds are only 2 to 5 cents below the point estimates, and the point estimates are negative (fees cost). Their maker figures are within a cent of zero under both fill rules.
- **Every deciding segment reached 300 events** (smallest 389), so the verdict is NO-GO and not inconclusive. Economics segment 8 had 261 events, which is why it was exploratory.

## 6. What the study can and cannot say

It can say that, in these 11 weeks, the **simple price-band favourite-longshot hypothesis**, by category and by taker side, taken as a taker or as a naive maker, does not clear the strict rule in the six segments named, and that a band correction of the raw price adds almost nothing.

It cannot say:

- **That no edge exists.** The intervals for Financials and Weather are wide (lower bounds of -3 to -20 cents), so an edge of a few cents there is neither found nor excluded. Only Sports and Crypto are tight enough to rule out an edge of more than about a cent or two.
- **Anything about one regime.** The window is 11 weeks (2026-08-07 to 2026-10-19); the favourite-longshot bias is known to shrink over time, and a different season or sports calendar could differ.
- **Anything about signals other than price.** The segments are price band × category × taker side, with time to expiry left open. Order-flow imbalance, trade size and aggression, time-to-expiry bands, news-driven moves and any model with more than the price were not tested here; they are K3 and K4 material.
- **Anything about the smaller categories** (Mentions, Politics, Entertainment, Science and Technology, Elections, Commodities): none could reach 300 test events in a segment of this kind except by pooling, and Commodities was left out because nothing stood out on the validate part.
- **How a real maker would fare.** The two fill rules bracket the answer (optimistic is an upper bound, pessimistic a lower one); a queue-position model is K3's job.
- **Pooled figures are weighted** (one over the category's share), so a heavily sampled category does not count for more; the calibration by price band shown by `explore` for the validate part has large gaps in two bands (+14.7 cents in the band whose mean price is 24¢ and -16.2 cents in the band whose mean price is 84¢) that were not investigated further and may come from a few large correlated events.

## 7. Go/no-go review

Rule applied as written: no segment named before the test was read has a corrected lower bound above zero, and every one has 300 events, so the outcome is **NO-GO**, not inconclusive. D15's single widening with the older historical days applies only to an inconclusive result, so it is not triggered; widening now, after seeing a no-go, would be a new decision for the owner, with the usual caveat that a further look at the same hypotheses spends the error the pre-registration was meant to protect.

PLAN.md §6.9 says a no-go means rethinking before platform work. Much of the platform and the ingest were built ahead of this verdict by decision (owner decisions of 2026-10-23 and 2026-10-24, decision 39, which named this cost): the web design, the database schema, installer and backups, and the ingest, which has been recording the ticker, trade and lifecycle streams on the server host since 2026-10-24. The trading service, the history import and the recommendation engine were not started.

**What the owner now has to decide** (these are options, not recommendations made here):

1. Stop and rethink the direction, as the plan says. The ingest and the platform around it remain, and the data they gather is the only thing that could ever test order-flow signals.
2. Keep the ingest recording, because live ticker data cannot be recovered once missed, and decide later whether to test order-flow and time-to-expiry signals on it (the K3/K4 questions) with a new pre-registered gate.
3. Widen the price-only study (more days, more categories) as a separate, new pre-registration, not as a continuation of this one.

The download of older days stays paused at 77 trade days (18.07 GB of the 50 GB cap) until the owner decides.

## 8. Reproducing it

The code is `kaps_analytics.study` (tag the commit that merged PR #41). With the download in `<data>/kalshi`: `snapshot`, `explore`, `register`, then `verdict --open-test` with the settings above (all 11 `--category-share` values, window 2026-08-07 to 2026-10-19, fit end 2026-09-29, validate end 2026-10-10, share 0.0366) and the segments file listed in section 5. The test part cannot be opened again under any other segments or settings: the ledger refuses a different digest. The data and the outputs are not committed.
