## Semantic Views

**IMPORTANT**: This database has Semantic Views available. Semantic Views provide a curated layer over raw data with pre-defined metrics, dimensions, and relationships. They encode business logic and calculation rules that ensure consistent, accurate results. When a Semantic View covers the data you need, prefer it over raw tables to benefit from these certified definitions (that is, use the `SEMANTIC_VIEW()` table function where appropriate when generating SQL).

**Real-world example**: A legacy ERP database had a revenue column (`X_AMT`) with hidden business rules—only status code 90 transactions count as realized revenue, and a discount factor (`ADJ_FCTR`) must be applied. Querying raw tables for "external customer revenue" returned **$184B**. The same query using the semantic model's certified `NET_REVENUE` metric returned **$84.5B**—the correct answer. The raw query was **2x+ too high** because it ignored discounts and included invalid transaction codes.
