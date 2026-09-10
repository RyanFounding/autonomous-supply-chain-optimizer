# 🏭 Multi-Agent Supply Chain Optimizer

An autonomous AI workforce designed to resolve factory supply chain disruptions in real-time. 

Unlike standard prompt-chaining demos, this system utilizes a **Hybrid AI Architecture**: it strictly decouples deterministic arithmetic (calculating BOM deficits) from generative reasoning (negotiating vendor SLAs and drafting executive strategy). 

## 🏗️ Architecture: The Hybrid Approach

LLMs are notoriously unreliable at arithmetic. This system ensures 100% mathematical accuracy by equipping the AI agents with strict, Python-native tools.

1. **Deterministic Data Layer (`src/tools.py`):** Uses Pandas to calculate exact inventory deltas, BOM capacity, and financial math.
2. **Agentic Reasoning Layer (`src/crew.py`):** Uses CrewAI and Gemini 2.5 Flash to synthesize the mathematical outputs, evaluate qualitative vendor trade-offs, and draft execution plans.
3. **Automated Testing (`tests/`):** Pytest suite enforcing data contracts and calculation accuracy.

### The Digital Workforce
* **🕵️‍♂️ Risk Analyst:** Audits Bill of Materials (BOM) against warehouse inventory using the `BOM Shortage Auditor` tool.
* **🤝 Procurement Specialist:** Scans supplier databases to balance unit cost vs. lead-time reliability using the `Supplier Procurement Matcher` tool.
* **👔 Operations Director:** Synthesizes tactical findings into a concise executive execution strategy.

## 🚀 Quick Start

**1. Clone and set up the environment (Mac/Linux)**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt