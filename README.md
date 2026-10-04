# IWM Overnight Reversal

## Research question

Does buying IWM at the official closing auction following a substantial decline in the previous completed trading session, then selling at the next official opening auction, produce an economically meaningful and statistically defensible advantage?

This repository documents a historical investigation of that question using Alpaca market data.

**Research status: Exploratory. The strategy is not statistically validated.**

## Trading hypothesis

The hypothesis is that substantial declines may create temporary selling pressure or overnight repricing opportunities that subsequently benefit a closing-auction purchase.

The proposed strategy is mechanical:

1. Calculate IWM's close-to-close return for the previous completed trading session.
2. If that return was -0.66555% or worse, buy IWM at today's official closing auction.
3. Sell the position at the next trading session's official opening auction.
4. Otherwise, remain in cash.

The signal deliberately excludes today's unfinished trading session. Its inputs must be available before the closing-auction order deadline.

The -0.66555% threshold was derived from historical exploration. It was not independently specified before examining the data.

## Historical investigation

**Sample:** January 2021 through October 2, 2026.

**Instrument:** IWM.

**Prices:** Official closing and opening auction prices obtained through Alpaca.

**Return treatment:** Overnight returns incorporate dividends associated with the overnight holding period. Historical prices were corrected for splits.

**Transaction costs:** The principal comparisons assume 2 basis points per completed overnight trade. This is a modeling assumption, not a verified estimate of achievable execution costs.

All reported results are historical simulations. Actual auction fills have not been demonstrated.

## Strategy performance

At an assumed 2-basis-point round-trip cost:

| Metric | Every-night benchmark | Prior-decline strategy |
|---|---:|---:|
| Historical observations | 1,428 | 1,428 |
| Trades | 1,428 | 432 |
| Overnight exposure | 100.0% | 30.3% |
| Compounded return | 50.50% | 37.09% |
| Annualized return | 7.48% | 5.72% |
| Maximum drawdown | -22.82% | -12.34% |
| Sharpe ratio | 0.601 | 0.742 |

The filtered strategy earned a lower absolute return but exhibited a smaller historical maximum drawdown and higher Sharpe ratio.

### Performance by historical period

| Metric | 2021-2023 | 2024-2026 |
|---|---:|---:|
| Filtered trades | 249 | 183 |
| Filtered compounded return | +15.53% | +18.66% |
| Filtered maximum drawdown | -12.34% | -7.33% |
| Filtered Sharpe ratio | 0.655 | 0.837 |

These periods should not be interpreted as pristine training and testing samples. The research process involved repeated examination of historical results.

## Exposure-matched comparison

To investigate whether the apparent improvement simply reflected reduced exposure, the filtered strategy was compared with an every-night benchmark holding approximately 30.25% of capital overnight.

| Metric | Prior-decline strategy | Exposure-matched benchmark |
|---|---:|---:|
| Annualized return | 5.724% | 2.405% |
| Maximum drawdown | -12.336% | -7.275% |
| Sharpe ratio | 0.742 | 0.601 |

The filter achieved a higher historical return and Sharpe ratio at comparable average exposure, although its maximum drawdown was also larger.

This comparison is descriptive, not proof of predictive information.

## Threshold sensitivity

Neighboring thresholds were evaluated at the same assumed 2-basis-point transaction cost.

| Previous-session decline | 2021-2023 return | 2024-2026 return |
|---|---:|---:|
| -0.30% | +7.03% | +31.98% |
| -0.50% | +12.67% | +25.72% |
| -0.66555% | +15.53% | +18.66% |
| -0.80% | +13.45% | +14.26% |
| -1.00% | +16.17% | +2.69% |

Positive historical returns across neighboring thresholds reduce concern about dependence on one exact cutoff. They do not eliminate selection bias or establish a statistically significant advantage.

## Statistical test

The central statistical question is whether overnight returns following substantial previous-session declines exceed overnight returns on excluded nights.

A comparison of selected and excluded nights used five-lag Newey-West standard errors.

| Period | Selected nights | Excluded nights | Mean advantage | Two-sided p-value |
|---|---:|---:|---:|---:|
| 2021-2023 | 249 | 496 | +6.163 bp | 0.3336 |
| 2024-2026 | 183 | 500 | +7.279 bp | 0.2960 |
| Full sample | 432 | 996 | +6.437 bp | 0.1716 |

The estimated advantage was positive in both periods, but none of the comparisons achieved conventional statistical significance.

Furthermore, the reported p-values are unadjusted for previous feature screening and threshold selection. They must not be treated as confirmatory evidence.

## Profit concentration

Removing the five largest winning trades from each period reduced the filtered strategy's compounded return:

| Period | Original return | Without five largest winners |
|---|---:|---:|
| 2021-2023 | +15.53% | +1.95% |
| 2024-2026 | +18.66% | +5.91% |

A relatively small number of exceptionally profitable nights contributed substantially to historical performance. This creates sensitivity to missed trades and execution quality.

Removing winning trades is a diagnostic stress test, not an implementable trading rule.

## Limitations

The investigation has several important limitations:

- Historical feature and threshold selection introduce data-snooping risk.
- The statistical advantage over excluded nights remains unproven.
- Exceptional winning nights account for a substantial portion of profits.
- Transaction costs are assumed rather than established through actual execution.
- Official auction prices do not guarantee that hypothetical orders would have received those fills.
- Dividends are incorporated into historical overnight returns, but taxes and operational cash-flow effects are not modeled.
- Historical performance does not establish future profitability.

## Research disposition

**IWM Prior Decline V1: FROZEN — EXPLORATORY, NOT VALIDATED.**

The frozen signal is a previous completed session's close-to-close return of -0.66555% or worse.

The historical findings justify preserving the candidate, but they do not justify claiming a demonstrated trading edge.

No further threshold optimization is authorized by this research disposition.

## Data policy

Raw and processed market data are intentionally excluded from this public repository. Alpaca credentials, account information, local environments, and private research files must not be committed.

This repository documents research findings; it does not distribute the underlying proprietary market data or represent an independently reproducible public-data backtest.

## Disclaimer

This repository contains experimental quantitative research, not investment advice or a production trading system. Historical simulated returns are not evidence of achievable live trading performance.
