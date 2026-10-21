# KAPS

**Kalshi Analytics and Probability System.** KAPS records [Kalshi](https://kalshi.com)'s market data, analyses it and estimates probabilities. From these it recommends buys and sells in non-combo markets, with manual and condition-based automated trading behind a risk layer. It is a recommendation system, not a high-frequency trading system.

**Status:** K0 is done (direction, assessment, an empty Python workspace). K0.5, an edge test on Kalshi's historical data, is in progress; the platform (K1a) follows only if it shows an edge. See:
- [docs/PLAN.md](docs/PLAN.md) for the plan;
- [docs/ASSESSMENT.md](docs/ASSESSMENT.md) for the hardware, data and literature assessment;
- [docs/LESSONS.md](docs/LESSONS.md) for what the earlier .NET line measured;
- [docs/BUILD-LOG.md](docs/BUILD-LOG.md) for how each step was built and verified.

**Stack:** Python, PostgreSQL 18 + TimescaleDB on Ubuntu (database, ingest and web), analytics and trading on macOS.

No real order is ever sent without the owner's go-ahead, and demo is the default environment.

License: MIT.
