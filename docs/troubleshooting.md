# RMCP Troubleshooting Guide

This guide helps you diagnose and resolve common issues when using RMCP's R integration functionality.

## Table of Contents

- [R Installation Issues](#r-installation-issues)
- [R Package Dependencies](#r-package-dependencies)
- [Script Execution Failures](#script-execution-failures)
- [JSON Serialization Problems](#json-serialization-problems)
- [Performance Issues](#performance-issues)
- [Memory and Resource Problems](#memory-and-resource-problems)
- [Platform-Specific Issues](#platform-specific-issues)

## R Installation Issues

### Problem: "R not found" or FileNotFoundError

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'R'
```

**Solutions:**

1. **Check R installation:**
   ```bash
   # Test if R is accessible
   R --version
   
   # Check PATH
   which R
   ```

2. **Install R if missing:**
   - **macOS:** `brew install r` or download from [CRAN](https://cran.r-project.org/)
   - **Ubuntu/Debian:** `sudo apt-get install r-base r-base-dev`
   - **CentOS/RHEL:** `sudo yum install R`
   - **Windows:** Download installer from [CRAN](https://cran.r-project.org/)

3. **Fix PATH issues:**
   ```bash
   # Add R to PATH (adjust path as needed)
   export PATH="/usr/local/bin:$PATH"
   
   # For conda environments
   conda install r-base
   ```

### Problem: Permission denied when executing R

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: 'R'
```

**Solutions:**
```bash
# Check R executable permissions
ls -la $(which R)

# Fix permissions if needed
chmod +x $(which R)

# For system-wide R installation
sudo chmod +x /usr/bin/R
```

## R Package Dependencies

### Problem: Required R packages not installed

**Symptoms:**
```
RExecutionError: R script failed with return code 1
stderr: Error in library(plm) : there is no package called 'plm'
```

**Required packages for RMCP:**
- Core: `jsonlite`, `plm`, `lmtest`, `sandwich`, `AER`
- Advanced: `forecast`, `vars`, `urca`, `ggplot2`, `gridExtra`, `tidyr`, `dplyr`

**Solutions:**

1. **Install missing packages in R:**
   ```r
   # Start R console
   R
   
   # Install core packages
   install.packages(c("jsonlite", "plm", "lmtest", "sandwich", "AER"))
   
   # Install advanced packages
   install.packages(c("forecast", "vars", "urca", "ggplot2", 
                      "gridExtra", "tidyr", "dplyr"))
   ```

2. **Automated installation script:**
   ```bash
   # Create and run package installer
   cat > install_r_packages.R << 'EOF'
   packages <- c("jsonlite", "plm", "lmtest", "sandwich", "AER",
                 "forecast", "vars", "urca", "ggplot2", "gridExtra", 
                 "tidyr", "dplyr")
   
   new_packages <- packages[!(packages %in% installed.packages()[,"Package"])]
   if(length(new_packages)) {
       install.packages(new_packages, repos="https://cran.rstudio.com/")
   }
   
   cat("All packages installed successfully!\n")
   EOF
   
   Rscript install_r_packages.R
   ```

3. **Verify installation:**
   ```r
   # Test package loading
   lapply(c("jsonlite", "plm", "lmtest"), library, character.only = TRUE)
   ```

### Problem: Package version conflicts

**Symptoms:**
```
Error: package 'XYZ' was installed by an R version with different internals
```

**Solutions:**
```r
# Update all packages
update.packages(ask = FALSE)

# Reinstall problematic package
remove.packages("problematic_package")
install.packages("problematic_package")

# Check R version compatibility
R.version.string
```

## Script Execution Failures

### Problem: R script syntax errors

**Symptoms:**
```
RExecutionError: R script failed with return code 1
stderr: Error: unexpected symbol in "invalid syntax"
```

**Debugging steps:**

1. **Test R script manually:**
   ```bash
   # Save the generated R script to a file and test
   cat > test_script.R << 'EOF'
   library(jsonlite)
   args <- fromJSON("test_args.json")
   # Your script code here
   write_json(result, "result.json", auto_unbox = TRUE)
   EOF
   
   Rscript test_script.R
   ```

2. **Common syntax issues:**
   - Missing commas in lists
   - Unmatched parentheses/brackets
   - Incorrect variable names
   - Missing `%||%` operator definition

3. **Add error checking to your R code:**
   ```r
   # Wrap code in tryCatch
   result <- tryCatch({
       # Your analysis code here
       list(success = TRUE, data = analysis_result)
   }, error = function(e) {
       list(success = FALSE, error = as.character(e))
   })
   ```

### Problem: R script timeouts

**Symptoms:**
```
subprocess.TimeoutExpired: Command '['R', '--slave', ...]' timed out after 120 seconds
```

**Solutions:**

1. **Optimize R code:**
   ```r
   # Use vectorized operations instead of loops
   # Bad:
   for(i in 1:length(x)) { result[i] <- x[i] * 2 }
   
   # Good:
   result <- x * 2
   ```

2. **Process data in chunks:**
   ```python
   # Split large datasets before sending to R
   def chunk_data(data, chunk_size=1000):
       for i in range(0, len(data), chunk_size):
           yield data[i:i + chunk_size]
   ```

3. **Increase timeout (if appropriate):**
   ```python
   # Modify r_integration.py timeout parameter
   process = subprocess.run(
       ['R', '--slave', '--no-restore', '--file=' + script_path],
       capture_output=True,
       text=True,
       timeout=300  # Increase from 120 to 300 seconds
   )
   ```

## JSON Serialization Problems

### Problem: Non-serializable data types

**Symptoms:**
```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
TypeError: Object of type 'complex' is not JSON serializable
```

**Solutions:**

1. **In Python - ensure JSON-compatible data:**
   ```python
   import json
   import numpy as np
   
   # Convert numpy arrays to lists
   data = {
       "values": np.array([1, 2, 3]).tolist(),
       "matrix": np.array([[1, 2], [3, 4]]).tolist()
   }
   
   # Handle datetime objects
   from datetime import datetime
   data["timestamp"] = datetime.now().isoformat()
   ```

2. **In R - ensure proper JSON output:**
   ```r
   library(jsonlite)
   
   # Convert factors to characters
   result$categorical_var <- as.character(result$categorical_var)
   
   # Handle special values
   result$numeric_var[is.infinite(result$numeric_var)] <- NA
   result$numeric_var[is.nan(result$numeric_var)] <- NA
   
   # Use auto_unbox for single values
   write_json(result, output_file, auto_unbox = TRUE, na = "null")
   ```

3. **Validate JSON before sending:**
   ```python
   import json
   
   def validate_json_data(data):
       try:
           json.dumps(data)
           return True
       except (TypeError, ValueError) as e:
           print(f"JSON validation failed: {e}")
           return False
   ```

### Problem: Large dataset serialization

**Symptoms:**
```
MemoryError: Unable to allocate array
json.decoder.JSONDecodeError: Extra data
```

**Solutions:**

1. **Use data streaming:**
   ```python
   # Process data in chunks
   def process_large_dataset(data, chunk_size=5000):
       results = []
       for chunk in chunk_data(data, chunk_size):
           result = execute_r_script(script, {"data": chunk})
           results.append(result)
       return combine_results(results)
   ```

2. **Use R's data.table for large datasets:**
   ```r
   library(data.table)
   
   # Convert to data.table for efficiency
   dt <- as.data.table(args$data)
   
   # Use data.table operations
   result <- dt[, .(mean = mean(value)), by = group]
   ```

## Performance Issues

### Problem: Slow R script execution

**Diagnostic steps:**

1. **Profile R code:**
   ```r
   # Add timing to your R script
   start_time <- Sys.time()
   
   # Your analysis code here
   
   end_time <- Sys.time()
   execution_time <- end_time - start_time
   
   result$execution_time <- as.numeric(execution_time)
   ```

2. **Optimize common operations:**
   ```r
   # Use built-in vectorized functions
   # Avoid: apply(matrix, 1, sum)
   # Use: rowSums(matrix)
   
   # Pre-allocate result vectors
   result_vector <- numeric(n)  # Instead of growing with c()
   
   # Use appropriate data structures
   # data.table for large datasets
   # matrix for numeric operations
   ```

3. **Enable parallel processing:**
   ```r
   library(parallel)
   
   # Detect cores
   n_cores <- detectCores() - 1
   
   # Use parallel operations
   results <- mclapply(data_list, analysis_function, mc.cores = n_cores)
   ```

## Memory and Resource Problems

### Problem: R process running out of memory

**Symptoms:**
```
Error: cannot allocate vector of size X GB
RExecutionError: R script failed with return code 1
```

**Solutions:**

1. **Monitor memory usage:**
   ```r
   # Check memory usage in R script
   memory_usage <- function() {
       cat("Memory usage:", object.size(ls(envir = .GlobalEnv)), "bytes\n")
   }
   
   # Clean up intermediate objects
   rm(large_object)
   gc()  # Force garbage collection
   ```

2. **Optimize data handling:**
   ```r
   # Read only needed columns
   data <- data[, c("col1", "col2", "col3")]
   
   # Use appropriate data types
   data$category <- as.factor(data$category)  # Instead of character
   
   # Process data in chunks
   process_chunk <- function(chunk) {
       # Process chunk
       result <- analyze(chunk)
       # Clean up
       rm(chunk)
       gc()
       return(result)
   }
   ```

3. **Increase available memory (system level):**
   ```bash
   # Check system memory
   free -h
   
   # For Docker containers, increase memory limit
   docker run -m 4g your_container
   
   # Set R memory limit (if applicable)
   R --max-mem-size=4G
   ```

## Platform-Specific Issues

### macOS Issues

**Problem: R not found after installation**
```bash
# Check if R is in Applications
ls /Applications/R.app/Contents/MacOS/R

# Create symlink if needed
sudo ln -s /Applications/R.app/Contents/MacOS/R /usr/local/bin/R
```

**Problem: Permission issues with Homebrew R**
```bash
# Fix Homebrew permissions
brew doctor
brew reinstall r
```

### Windows Issues

**Problem: R path with spaces**
```python
# In r_integration.py, handle Windows paths with spaces
r_cmd = ['R.exe', '--slave', '--no-restore', '--file=' + script_path]
# Make sure to use proper quoting for paths with spaces
```

**Problem: Line ending issues**
```python
# Ensure consistent line endings
script_content = script_content.replace('\r\n', '\n')
```

### Linux Issues

**Problem: Missing development headers**
```bash
# Install R development packages
sudo apt-get install r-base-dev

# For CentOS/RHEL
sudo yum install R-devel
```

**Problem: Locale issues**
```bash
# Set proper locale
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Or in R script
Sys.setlocale("LC_ALL", "en_US.UTF-8")
```

## Getting Help

### Enabling Debug Logging

Add detailed logging to diagnose issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In your tool function
await context.info("Starting analysis", data_shape=len(params["data"]))
```

### Collecting Diagnostic Information

When reporting issues, include:

1. **System information:**
   ```bash
   # OS version
   uname -a
   
   # R version
   R --version
   
   # Python version
   python --version
   
   # RMCP version
   rmcp version
   ```

2. **R package versions:**
   ```r
   # In R console
   sessionInfo()
   ```

3. **Error logs with full stack trace**

4. **Minimal reproducing example**

### Community Resources

- GitHub Issues: [RMCP Issues](https://github.com/finite-sample/rmcp/issues)
- R Help: [R-help mailing list](https://stat.ethz.ch/mailman/listinfo/r-help)
- Stack Overflow: Tag questions with `r` and `mcp`

---

For additional help, please file an issue on GitHub with your diagnostic information and a minimal reproducing example.