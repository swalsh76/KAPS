# KAPS web design (K6.0)

The web UI is where KAPS is used every day, so it has to be pleasant to look at and to work in. This is the design system and the five key screens that K6 builds from. It follows PLAN.md §6.8 and decision 38 (one user). The clickable mock-ups were made as a private page; this folder holds what the code needs from them.

## The look

A quiet instrument panel: dense where the numbers are, calm everywhere else. Dark is the default and light uses the same token names (`tokens.css`). One blue accent. Every number is set in tabular figures, so columns line up and a changing price does not shift its neighbours.

- **Nothing is only a colour.** Gain and loss are teal and orange, and each always carries an arrow and a sign. State is a word and a dot. The palette is chosen to read for colour-blind users in both themes.
- **Production is never ambiguous.** Coral red appears nowhere else. A persistent banner names the environment on every screen (production, paper or demo), and a production order needs the owner's passkey over the exact order.
- **Confidence is drawn.** A recommendation shows the price against the model's interval on one scale, and a risk limit is a meter with its figure.
- **Elevation is a hairline and a surface step**, not a shadow, so dense screens stay flat and legible.
- **Motion is subtle and optional.** A changed price highlights briefly, panels slide, and `prefers-reduced-motion` removes all of it.

## Screens designed

1. **Foundations:** tokens in both themes, type, buttons, chips, gain and loss, the confidence bar, the limit meter, environment banners, inputs and status.
2. **Recommendations:** a feed with price, model interval, edge after fees and a suggested size on every card, and a panel explaining the selected one.
3. **Market detail:** price chart with the model's interval, an order-book ladder with depth, recent trades and the owner's position.
4. **Order ticket and passkey:** side, order type, price and size steppers; the exact fee, maximum loss and gain; limit checks; a review of the exact order; and, in production, a passkey signing sheet.
5. **Rules and replays:** a rule read as sentences (when, then, limits), its replay as an equity curve with the drawdown switch-off marked, and its latest triggers.
6. **Status:** every service against its target, the data-gap log, the trading controls with the stop-all button, and recent alerts.

All figures in the mock-ups are invented sample data.

## Fonts and licences

| Item | Licence |
|---|---|
| Inter (text) | SIL Open Font License 1.1 |
| JetBrains Mono (tickers, ids) | SIL Open Font License 1.1 |
| Icons | drawn inline as strokes; no icon set is used |

The chart library, the UI kit (if any) and the passkey library are chosen and licence-checked in the K6 build plan. The mock-ups draw charts as plain paths so that choice stays open.

## Quality bar for K6

Visual regression tests of every key screen in both themes, an automated accessibility check (axe), WCAG 2.2 AA contrast, keyboard use with a visible focus ring, real buttons and labels, text alternatives for charts, targets of at least 44 px, and a first screen under 2 seconds on the LAN.
