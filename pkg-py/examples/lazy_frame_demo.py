#!/usr/bin/env python3
"""
Demo script comparing eager vs lazy data source performance.

This script demonstrates the performance benefits of using PolarsLazySource
with large datasets. It creates a synthetic dataset and compares:
1. Eager loading (all data in memory upfront)
2. Lazy loading (data stays on disk until needed)

Usage:
    # Set your API key first
    export OPENAI_API_KEY="your-key-here"

    # Run the demo
    cd pkg-py
    uv run python examples/lazy_frame_demo.py

    # Or with a custom number of rows (default: 10 million)
    uv run python examples/lazy_frame_demo.py --rows 50000000
"""

import argparse
import os
import tempfile
import time
from pathlib import Path

import polars as pl


def create_large_dataset(path: Path, n_rows: int) -> None:
    """Create a large parquet file for testing."""
    print(f"Creating dataset with {n_rows:,} rows...")
    start = time.perf_counter()

    # Generate data in chunks to avoid memory issues
    chunk_size = 1_000_000
    chunks_written = 0

    for i in range(0, n_rows, chunk_size):
        chunk_rows = min(chunk_size, n_rows - i)
        chunk = pl.DataFrame(
            {
                "id": range(i, i + chunk_rows),
                "category": [f"cat_{j % 100}" for j in range(chunk_rows)],
                "region": [["North", "South", "East", "West"][j % 4] for j in range(chunk_rows)],
                "value": [float(j % 1000) + 0.5 for j in range(chunk_rows)],
                "quantity": [j % 500 for j in range(chunk_rows)],
                "date": pl.Series([f"2024-{(j % 12) + 1:02d}-{(j % 28) + 1:02d}" for j in range(chunk_rows)]).str.to_date(),
            }
        )

        if chunks_written == 0:
            chunk.write_parquet(path)
        else:
            # Append by reading existing and concatenating
            existing = pl.read_parquet(path)
            pl.concat([existing, chunk]).write_parquet(path)

        chunks_written += 1
        print(f"  Written {min(i + chunk_size, n_rows):,} / {n_rows:,} rows")

    elapsed = time.perf_counter() - start
    file_size_mb = path.stat().st_size / (1024 * 1024)
    print(f"Dataset created: {file_size_mb:.1f} MB in {elapsed:.1f}s\n")


def measure_memory() -> float:
    """Get current memory usage in MB (approximate)."""
    import psutil
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def demo_eager_vs_lazy(parquet_path: Path) -> None:
    """Compare eager vs lazy data loading performance."""
    from querychat import QueryChat

    print("=" * 60)
    print("COMPARING EAGER VS LAZY DATA SOURCE")
    print("=" * 60)

    # Check if we have psutil for memory tracking
    try:
        import psutil  # noqa: F401
        has_psutil = True
    except ImportError:
        has_psutil = False
        print("(Install psutil for memory usage tracking: pip install psutil)\n")

    # --- EAGER LOADING ---
    print("\n1. EAGER LOADING (polars.read_parquet → DataFrame)")
    print("-" * 50)

    if has_psutil:
        mem_before = measure_memory()

    start = time.perf_counter()
    df = pl.read_parquet(parquet_path)
    load_time = time.perf_counter() - start

    if has_psutil:
        mem_after = measure_memory()
        print(f"   Memory increase: {mem_after - mem_before:.1f} MB")

    print(f"   Load time: {load_time:.2f}s")
    print(f"   Rows loaded: {len(df):,}")

    # Create QueryChat with eager data
    start = time.perf_counter()
    qc_eager = QueryChat(
        data_source=df,
        table_name="sales",
        greeting="Hello!",
    )
    init_time = time.perf_counter() - start
    print(f"   QueryChat init: {init_time:.2f}s")

    # Execute a query
    start = time.perf_counter()
    result = qc_eager.data_source.execute_query(
        "SELECT region, SUM(value) as total FROM sales GROUP BY region"
    )
    query_time = time.perf_counter() - start
    print(f"   Query execution: {query_time:.3f}s")
    print(f"   Result rows: {len(result)}")

    del df, qc_eager, result
    import gc
    gc.collect()

    # --- LAZY LOADING ---
    print("\n2. LAZY LOADING (polars.scan_parquet → LazyFrame)")
    print("-" * 50)

    if has_psutil:
        mem_before = measure_memory()

    start = time.perf_counter()
    lf = pl.scan_parquet(parquet_path)
    load_time = time.perf_counter() - start

    if has_psutil:
        mem_after = measure_memory()
        print(f"   Memory increase: {mem_after - mem_before:.1f} MB")

    print(f"   'Load' time: {load_time:.4f}s (just metadata!)")

    # Create QueryChat with lazy data
    start = time.perf_counter()
    qc_lazy = QueryChat(
        data_source=lf,
        table_name="sales",
        greeting="Hello!",
    )
    init_time = time.perf_counter() - start
    print(f"   QueryChat init: {init_time:.2f}s")

    # Execute the same query (stays lazy)
    start = time.perf_counter()
    result_lazy = qc_lazy.data_source.execute_query(
        "SELECT region, SUM(value) as total FROM sales GROUP BY region"
    )
    query_time = time.perf_counter() - start
    print(f"   Query execution (lazy): {query_time:.3f}s")

    # Now collect to get actual results
    start = time.perf_counter()
    result_collected = result_lazy.collect()
    collect_time = time.perf_counter() - start
    print(f"   Collect time: {collect_time:.3f}s")
    print(f"   Result rows: {len(result_collected)}")

    # --- SUMMARY ---
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Key differences:
- EAGER: Loads ALL data into memory immediately
- LAZY: Only reads metadata; data stays on disk until .collect()

Benefits of lazy:
- Much faster startup (no full data load)
- Lower memory usage (only results in memory)
- Query optimization (Polars can push down filters)

Use lazy (scan_parquet) for:
- Large files that don't fit in memory
- When you only need filtered/aggregated subsets
- Interactive exploration of big data
""")


def interactive_demo(parquet_path: Path) -> None:
    """Launch an interactive QueryChat session with the lazy data."""
    from querychat import QueryChat

    print("\n" + "=" * 60)
    print("INTERACTIVE DEMO")
    print("=" * 60)

    lf = pl.scan_parquet(parquet_path)
    qc = QueryChat(
        data_source=lf,
        table_name="sales",
        greeting="I'm connected to a large sales dataset. Ask me anything!",
    )

    print("\nLaunching interactive console...")
    print("Try queries like:")
    print('  - "Show me total sales by region"')
    print('  - "What are the top 10 categories by quantity?"')
    print('  - "Filter to just the North region"')
    print("\nType 'exit' to quit.\n")

    qc.console()


def main():
    parser = argparse.ArgumentParser(description="Demo lazy vs eager data loading")
    parser.add_argument(
        "--rows",
        type=int,
        default=10_000_000,
        help="Number of rows to generate (default: 10 million)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive console after comparison",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Path to existing parquet file (skip generation)",
    )
    args = parser.parse_args()

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Interactive mode won't work.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'\n")

    # Create or use existing data file
    if args.data_path:
        parquet_path = Path(args.data_path)
        if not parquet_path.exists():
            print(f"Error: File not found: {parquet_path}")
            return
    else:
        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        parquet_path = Path(temp_dir) / "large_sales_data.parquet"
        create_large_dataset(parquet_path, args.rows)

    try:
        demo_eager_vs_lazy(parquet_path)

        if args.interactive:
            interactive_demo(parquet_path)
    finally:
        # Cleanup temp file if we created it
        if not args.data_path and parquet_path.exists():
            print(f"\nCleaning up temporary file: {parquet_path}")
            parquet_path.unlink()
            parquet_path.parent.rmdir()


if __name__ == "__main__":
    main()
