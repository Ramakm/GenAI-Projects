# Customer Support Agent

An intelligent customer support agent built using LangGraph that categorizes customer queries, analyzes sentiment, and provides appropriate responses or escalates issues when necessary.

## How It Works

The agent uses a LangGraph state machine with the following pipeline:

```
Customer Query
      |
      v
+------------------+
| Categorize Query |  Classifies into: billing, technical_support,
+------------------+  account_management, product_inquiry, complaint, general
      |
      v
+--------------------+
| Analyze Sentiment  |  Detects: positive, neutral, negative, angry
+--------------------+  Produces a score from -1.0 to 1.0
      |
      v
+--------------------+
| Check Escalation   |  Evaluates sentiment score + category
+--------------------+
      |
      +--- escalated ----> Escalate to Human Agent ---> END
      |
      +--- normal -------> Generate AI Response -----> END
```

Escalation triggers:
- Sentiment score below -0.6
- Angry sentiment detected
- Negative complaints

## Project Structure

```
Customer-Support-Agent/
├── main.py          # Entry point (CLI and interactive mode)
├── graph.py         # LangGraph workflow definition
├── nodes.py         # Node functions (categorize, sentiment, response, escalation)
├── state.py         # Agent state schema
├── config.py        # Configuration and constants
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:

```bash
cp .env.example .env
# Edit .env and add your API key
```

## Usage

### Interactive mode

```bash
python main.py
```

### Single query

```bash
python main.py "I've been charged twice for my subscription and no one is helping me!"
```

### Example output

```
============================================================
CUSTOMER SUPPORT AGENT RESULT
============================================================
Query:       I've been charged twice for my subscription
Category:    billing
Sentiment:   negative (score: -0.40)
Escalated:   False
------------------------------------------------------------
Response:
I'm sorry to hear about the double charge on your subscription.
I can help resolve this right away. Let me look into your account
and initiate a refund for the duplicate charge...
============================================================
```

### Escalation example

```
Query:       This is ridiculous! Your service has been down for 3 days and nobody cares!
Category:    complaint
Sentiment:   angry (score: -0.85)
Escalated:   True
Reason:      Very negative sentiment (score: -0.85); Customer is angry; Negative complaint requires human attention
```

## Configuration

Key settings in `config.py`:

| Setting                | Default      | Description                              |
|------------------------|-------------|------------------------------------------|
| `MODEL_NAME`           | gpt-4o-mini | OpenAI model to use                      |
| `ESCALATION_THRESHOLD` | -0.6        | Sentiment score below this escalates     |
| `CATEGORIES`           | 6 categories| Billing, technical, account, product, complaint, general |

## License

MIT
