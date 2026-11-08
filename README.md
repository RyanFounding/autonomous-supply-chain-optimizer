# Supply Chain Disruption Analyzer

Shows how a parts shortage affects production, and which supplier to source each short part from. Inventory and sourcing math runs in Python, and a team of LLM agents turns the results into an executive briefing.

## Problem

When a component runs short, a plant needs three answers quickly: how many finished units can still be built, which parts are the bottleneck, and which supplier to order from, given that the cheapest quote is often not the fastest one. The data for this sits in the bill of materials, the inventory system and supplier quotes. Combining it by hand is slow and prone to errors.

Language models are good at weighing trade-offs and writing a clear recommendation. They are not reliable at arithmetic, so they should never be the source of a stock figure or an order cost.

## Solution

The work is split into two layers with a strict boundary between them:

1. **Deterministic engine (Python and pandas).** Validates the input tables, then calculates build capacity per product, shortages, order quantities, and cost and lead time for every supplier quote.
2. **Agent layer (CrewAI and Gemini).** Three agents (risk analyst, procurement specialist, operations director) get those results as fixed input. They prioritize risks, pick a supplier per part and write a three-bullet briefing. Each agent is told to use only the figures it was given.

The Streamlit app shows the full analysis without an API key. The agent briefing is an optional second step.

## Architecture

```
CSV inputs (BOM, inventory, supplier quotes)
    |
    v
data.py      schema and value validation -> SupplyChainData
    |
    v
engine.py    capacity per product, shortages, sourcing options -> SupplyChainAnalysis (typed)
    |
    +--> app.py     tables in Streamlit (no API key needed)
    |
    v
crew.py      analysis JSON -> risk analyst -> procurement -> operations director -> briefing
```

| Module | Responsibility |
|---|---|
| `data.py` | Loads CSVs and rejects bad input: missing columns, negative or non-numeric values, zero BOM quantities, duplicate inventory rows. |
| `engine.py` | All calculations. Pure functions over validated data. |
| `models.py` | Pydantic models for every result the engine produces. These are also what the agents receive. |
| `crew.py` | Agent and task definitions. Gets the analysis as input and holds no business logic. |
| `app.py` | Streamlit UI. Uses the sample data or uploaded CSVs. |

## Tech stack

| Choice | Why |
|---|---|
| pandas | Joins and aggregation across BOM, inventory and supplier tables. |
| Pydantic v2 | Typed results with a single JSON form, used both for display and as agent input. |
| CrewAI | Sequential multi-agent workflow where each task builds on the previous one's output. |
| Gemini 2.5 Flash | Low-cost model, sufficient for reasoning over precomputed facts. Configurable through `LLM_MODEL`. |
| Streamlit | Fast interactive front end for tabular data. Its `AppTest` harness lets the UI be tested without a browser. |
| pytest, ruff, mypy (strict) | CI runs lint, type checks and tests on every push. |

## Key technical decisions

- **Compute first, then reason.** An earlier version gave the agents calculation tools and let them pass the raw tables as tool arguments. That made correctness depend on the model copying data accurately. Now the engine runs before any agent, and the agents can't change a number.
- **Capacity per product.** A BOM can list several finished products that share parts. Capacity is calculated per product and names the parts that limit it, so the bottleneck is visible.
- **Parts missing from inventory count as shortages.** If a BOM part has no inventory record, capacity drops to zero and the part is reported with reason `not_in_inventory`. The earlier version dropped it from the shortage list, which hid the root cause.
- **Sourcing is ranked, not chosen.** For each short part, the engine lists every quote sorted by lead time, marks the cheapest and the fastest, and calculates the order cost. Picking between cost and downtime is left to the procurement agent, and to the person reading the briefing.
- **Validate at the edge.** Bad data fails with a specific message when it's loaded, instead of producing a wrong answer later.

## Data format

| File | Columns |
|---|---|
| BOM | `final_product`, `part_name`, `quantity_required_per_unit` |
| Inventory | `part_name`, `current_stock`, `reorder_threshold` |
| Supplier quotes | `part_name`, `supplier_name`, `unit_cost_usd`, `lead_time_days` |

A part is short when its stock is at or below its reorder threshold. The order quantity brings it back up to the threshold. Sample files are in `data/`.

## Running locally

Requires Python 3.11 or newer.

```bash
git clone https://github.com/RyanFounding/autonomous-supply-chain-optimizer.git
cd autonomous-supply-chain-optimizer
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
streamlit run app.py
```

The analysis loads the sample data straight away. For the agent briefing, either paste a Gemini API key into the app or set it before starting:

```bash
cp .env.example .env               # set GEMINI_API_KEY
export $(grep -v '^#' .env | xargs)
streamlit run app.py
```

## Testing

```bash
pytest           # engine, validation, agent wiring and a headless UI smoke test
ruff check .
mypy
```

None of the tests call a model or need an API key.

## Limitations

- Shortages use a reorder-point rule only. Demand forecasts and open purchase orders are not considered.
- Supplier selection doesn't account for minimum order quantities, volume pricing or supplier reliability scores.
- The agent briefing is generated text. The figures in it come from the engine, but its recommendations should be reviewed before acting on them.
