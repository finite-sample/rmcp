# K-means Clustering Analysis Script for RMCP
# ===========================================
#
# This script performs K-means clustering analysis with cluster validation
# including silhouette analysis and variance explained calculations.

# Load required libraries
library(cluster)
library(knitr)

# Prepare data and parameters
variables <- args$variables
k <- args$k
max_iter <- args$max_iter %||% 100
nstart <- args$nstart %||% 25

# Select and prepare data
rmcp_progress("Preparing data for clustering")
cluster_data <- data[, variables, drop = FALSE]
cluster_data <- na.omit(cluster_data)

# Scale variables for clustering
rmcp_progress("Scaling variables for clustering")
scaled_data <- scale(cluster_data)

# Perform k-means
rmcp_progress("Running k-means clustering", 0, 100)
set.seed(123) # For reproducibility
kmeans_result <- kmeans(scaled_data, centers = k, iter.max = max_iter, nstart = nstart)
rmcp_progress("K-means clustering completed", 100, 100)
# Calculate cluster statistics
cluster_centers <- kmeans_result$centers
cluster_assignments <- kmeans_result$cluster
# Within-cluster sum of squares
wss <- kmeans_result$withinss
total_wss <- kmeans_result$tot.withinss
between_ss <- kmeans_result$betweenss
total_ss <- kmeans_result$totss
# Cluster sizes
cluster_sizes <- table(cluster_assignments)
# Silhouette analysis
sil <- silhouette(cluster_assignments, dist(scaled_data))
silhouette_score <- mean(sil[, 3])
result <- list(
  cluster_assignments = cluster_assignments,
  cluster_centers = as.list(as.data.frame(cluster_centers)),
  cluster_sizes = as.list(cluster_sizes),
  within_ss = wss,
  total_within_ss = total_wss,
  between_ss = between_ss,
  total_ss = total_ss,
  variance_explained = between_ss / total_ss * 100,
  silhouette_score = silhouette_score,
  k = k,
  variables = variables,
  n_obs = nrow(cluster_data),
  converged = kmeans_result$iter < max_iter,
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create clustering summary table
        cluster_summary <- data.frame(
          Method = "K-means",
          Clusters = k,
          Variables = length(variables),
          Observations = nrow(cluster_data),
          Variance_Explained = round(between_ss / total_ss * 100, 2),
          Silhouette_Score = round(silhouette_score, 3)
        )
        paste(as.character(knitr::kable(
          cluster_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        "K-means clustering completed successfully"
      }
    ),
    interpretation = paste0(
      "K-means clustering with ", k, " clusters explains ",
      round(between_ss / total_ss * 100, 1), "% of variance (silhouette score: ",
      round(silhouette_score, 3), ")."
    )
  )
)
