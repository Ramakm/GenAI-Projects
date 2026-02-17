# GenAI-Projects

A collection of production-style Generative AI and AI Agent projects. Each project demonstrates a real-world use case built with modern frameworks like LangChain, LangGraph, and OpenAI -- designed to help you understand how to build GenAI products from scratch.

Built by [Ramakrushna Mohapatra](https://github.com/Ramakm)

---

## Projects

| # | Project | Description | Tech Stack |
|---|---------|-------------|------------|
| 1 | [Customer Support Agent](./Customer-Support-Agent) | An intelligent support agent that categorizes customer queries, analyzes sentiment, and either responds or escalates to a human agent | LangGraph, LangChain, OpenAI |

---

## Customer Support Agent

An AI-powered customer support pipeline built with LangGraph. It processes incoming customer messages through a multi-step state machine:

1. **Query Categorization** -- classifies the message into billing, technical support, account management, product inquiry, complaint, or general
2. **Sentiment Analysis** -- detects sentiment (positive, neutral, negative, angry) with a numeric score
3. **Escalation Check** -- routes angry or highly negative queries to a human agent
4. **Response Generation** -- produces a helpful, empathetic reply for non-escalated queries

```
Customer Query --> Categorize --> Sentiment --> Escalation Check
                                                  |
                                       +----------+----------+
                                       |                     |
                                  AI Response         Human Handoff
```

[View project details](./Customer-Support-Agent)

---

## Getting Started

Each project is self-contained in its own folder with its own `README.md`, `requirements.txt`, and setup instructions. To run any project:

```bash
# Clone the repo
git clone https://github.com/Ramakm/GenAI-Projects.git
cd GenAI-Projects

# Navigate to a project
cd Customer-Support-Agent

# Install dependencies
pip install -r requirements.txt

# Follow the project-specific README for usage
```

## Repository Structure

```
GenAI-Projects/
├── README.md
├── LICENSE
└── Customer-Support-Agent/
    ├── README.md
    ├── main.py
    ├── graph.py
    ├── nodes.py
    ├── state.py
    ├── config.py
    ├── requirements.txt
    ├── .env.example
    └── .gitignore
```

## Tech Stack

Frameworks and tools used across projects:

- **LangChain** -- LLM orchestration and prompt management
- **LangGraph** -- Stateful agent workflows with conditional routing
- **OpenAI** -- GPT models for language understanding and generation
- **Pydantic** -- Data validation and state schemas
- **Python 3.10+**

## Contributing

Contributions are welcome. To add a new project:

1. Fork the repository
2. Create a new folder with a descriptive name
3. Include a `README.md`, `requirements.txt`, and `.env.example` in the project folder
4. Submit a pull request

## License

MIT License. See [LICENSE](LICENSE) for details.
