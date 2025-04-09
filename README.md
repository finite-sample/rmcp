## R Econometrics MCP Server

A Model Context Protocol (MCP) server that provides econometric modeling capabilities through R. This server enables AI assistants to perform sophisticated econometric analyses, including linear regression, panel data models, instrumental variables regression, and diagnostic tests.

## Features

- **Linear Regression**: Run linear models with optional robust standard errors.
- **Panel Data Analysis**: Fixed effects, random effects, pooling, between, and first-difference models.
- **Instrumental Variables**: Estimate IV regression models.
- **Diagnostic Tests**: Heteroskedasticity, autocorrelation, and functional form tests.
- **Resources**: Reference documentation for econometric techniques.
- **Prompts**: Pre-defined prompt templates for common econometric analyses.

## Installation

### Using Docker (Recommended)

1. Build the Docker image:
   ```bash
   docker build -t r-econometrics-mcp .
   ```

2. Run the container:

```bash
docker run -it r-econometrics-mcp
```

### Manual Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Install the required R packages (if you run the server outside a container):

```R
install.packages(c("plm", "lmtest", "sandwich", "AER", "jsonlite"), repos="https://cloud.r-project.org/")
```

Run the server:

```bash
python rmcp.py
```

## Usage

The server communicates via standard input/output. When you run:

```bash
python rmcp.py
```

it starts and waits for JSON messages on standard input. To test the server manually, create a file (for example, test_request.json) with a compact (single-line) JSON message.

### Example Test
Create test_request.json with the following content (a one-line JSON):

```json
{"tool": "linear_model", "args": {"formula": "y ~ x1", "data": {"x1": [1,2,3,4,5], "y": [1,3,5,7,9]}, "robust": false}}
```

Then run:

```bash
cat test_request.json | python rmcp.py
```

Output

```
{"coefficients": {"(Intercept)": -1, "x1": 2}, "std_errors": {"(Intercept)": 2.8408e-16, "x1": 8.5654e-17}, "t_values": {"(Intercept)": -3520120717017444, "x1": 23349839270207356}, "p_values": {"(Intercept)": 5.0559e-47, "x1": 1.7323e-49}, "r_squared": 1, "adj_r_squared": 1, "sigma": 2.7086e-16, "df": [2, 3, 2], "model_call": "lm(formula = formula, data = data)", "robust": false}
```
## Usage with Claude Desktop

1. Launch Claude Desktop
2. Open the MCP Servers panel
3. Add a new server with the following configuration:
   - Name: R Econometrics
   - Transport: stdio
   - Command: path/to/python r_econometrics_mcp.py
   - (Or if using Docker): docker run -i r-econometrics-mcp

## Example Queries

Here are some example queries you can use with Claude once the server is connected:

### Linear Regression

```
Can you analyze the relationship between price and mpg in the mtcars dataset using linear regression?
```

### Panel Data Analysis

```
I have panel data with variables gdp, investment, and trade for 30 countries over 20 years. Can you help me determine if a fixed effects or random effects model is more appropriate?
```

### Instrumental Variables

```
I'm trying to estimate the causal effect of education on wages, but I'm concerned about endogeneity. Can you help me set up an instrumental variables regression?
```

### Diagnostic Tests

```
After running my regression model, I'm concerned about heteroskedasticity. Can you run appropriate diagnostic tests and suggest corrections if needed?
```

## Tools Reference

### linear_model

Run a linear regression model.

**Parameters**:
- `formula` (string): The regression formula (e.g., 'y ~ x1 + x2')
- `data` (object): Dataset as a dictionary/JSON object
- `robust` (boolean, optional): Whether to use robust standard errors

### panel_model

Run a panel data model.

**Parameters**:
- `formula` (string): The regression formula (e.g., 'y ~ x1 + x2')
- `data` (object): Dataset as a dictionary/JSON object
- `index` (array): Panel index variables (e.g., ['individual', 'time'])
- `effect` (string, optional): Type of effects: 'individual', 'time', or 'twoways'
- `model` (string, optional): Model type: 'within', 'random', 'pooling', 'between', or 'fd'

### diagnostics

Perform model diagnostics.

**Parameters**:
- `formula` (string): The regression formula (e.g., 'y ~ x1 + x2')
- `data` (object): Dataset as a dictionary/JSON object
- `tests` (array): Tests to run (e.g., ['bp', 'reset', 'dw'])

### iv_regression

Estimate instrumental variables regression.

**Parameters**:
- `formula` (string): The regression formula (e.g., 'y ~ x1 + x2 | z1 + z2')
- `data` (object): Dataset as a dictionary/JSON object

## Resources

- `econometrics:formulas`: Information about common econometric model formulations
- `econometrics:diagnostics`: Reference for diagnostic tests
- `econometrics:panel_data`: Guide to panel data analysis in R

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

