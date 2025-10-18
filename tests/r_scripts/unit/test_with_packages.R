# Test flexible R execution with package loading
# Uses dplyr for data manipulation

library(dplyr)

# Create summary statistics using dplyr
result <- data %>%
    summarise(
        count = n(),
        mean_x = mean(x),
        mean_y = mean(y),
        sd_x = sd(x),
        sd_y = sd(y),
        correlation = cor(x, y)
    )