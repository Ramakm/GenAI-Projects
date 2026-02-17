# Data Analysis Agent

An AI-powered data analysis agent built with PydanticAI that allows you to analyze datasets using natural language queries. Ask questions about your data in plain English and the agent automatically generates and executes pandas code to extract insights.

## How It Works

```
Natural Language Query
        |
        v
+------------------+
| PydanticAI Agent |  Receives dataset schema + question
+------------------+
        |
        v  generated pandas code
+------------------+
| Safe Executor    |  Runs code against DataFrame
+------------------+
        |
        v
+------------------+
| Result Formatter |  Produces readable text + tables
+------------------+
        |
        v
  AnalysisResult (code, answer, table)
```

The agent receives the dataset schema (column names, types, sample values) as context, generates a pandas expression or code block, executes it in a sandboxed environment, and returns a formatted result.

## Project Structure

```
Data-Analysis-Agent/
├── main.py          # Entry point (CLI and interactive mode)
├── agent.py         # PydanticAI agent definition
├── executor.py      # Safe pandas code execution
├── data_loader.py   # CSV loading and schema extraction
├── schemas.py       # Pydantic models for input/output
├── config.py        # Configuration and constants
├── sample_data.csv  # Sample employee dataset
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
python main.py --data sample_data.csv
```

### Single query

```bash
python main.py --data sample_data.csv --query "What is the average salary by department?"
```

### With your own data

```bash
python main.py --data your_dataset.csv
```

## Example Queries

Using the included `sample_data.csv` (employee dataset):

```
Ask: What is the average salary by department?
Code: df.groupby('department')['salary'].mean()

Ask: Who has the highest rating?
Code: df.loc[df['rating'].idxmax()]

Ask: How many employees are in each city?
Code: df['city'].value_counts()

Ask: What is the total salary of employees with more than 5 years experience?
Code: df[df['experience_years'] > 5]['salary'].sum()

Ask: Show the top 3 highest paid employees
Code: df.nlargest(3, 'salary')[['name', 'department', 'salary']]
```

### Sample output

```
============================================================
DATA ANALYSIS RESULT
============================================================
Query:  What is the average salary by department?
Code:   df.groupby('department')['salary'].mean()
------------------------------------------------------------
Result: Series with 3 entries.

+----+--------------+---------+
|    | department   |  salary |
+====+==============+=========+
|  0 | Engineering  |  102400 |
+----+--------------+---------+
|  1 | Marketing    |   77000 |
+----+--------------+---------+
|  2 | Sales        |   69200 |
+----+--------------+---------+
============================================================
```

## Configuration

Key settings in `config.py`:

| Setting      | Default           | Description            |
|-------------|-------------------|------------------------|
| `MODEL_NAME` | openai:gpt-4o-mini | PydanticAI model identifier |
| `MAX_RETRIES` | 3                 | Retry attempts for LLM calls |

## License

MIT
