# KAPS

**Kalshi Analytics and Probability System.** KAPS records [Kalshi](https://kalshi.com)'s market data, analyses it and estimates probabilities. From these it recommends buys and sells in non-combo markets, with manual and condition-based automated trading behind a risk layer. It is a recommendation system, not a high-frequency trading system.

**Status:** K0. The direction, the assessment and an empty Python workspace are done; the platform (K1) is next. See:
- [docs/PLAN.md](docs/PLAN.md) for the plan;
- [docs/ASSESSMENT.md](docs/ASSESSMENT.md) for the hardware, data and literature assessment;
- [docs/LESSONS.md](docs/LESSONS.md) for what the earlier .NET line measured;
- [docs/BUILD-LOG.md](docs/BUILD-LOG.md) for how each step was built and verified.

**Stack:** Python, PostgreSQL 18 + TimescaleDB on Ubuntu (database, ingest and web), analytics and trading on macOS.

No real order is ever sent without the owner's go-ahead, and demo is the default environment.

License: MIT.
