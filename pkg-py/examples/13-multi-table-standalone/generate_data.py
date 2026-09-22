# /// script
# dependencies = ["polars"]
# ///
"""Generate (or load cached) synthetic data for a fine-jewelry retailer demo.

Five related tables are produced with a fixed random seed so the data is
identical across runs: diamonds, settings (ring mountings), customers,
orders, and order_items.

Run directly to force-regenerate the cache:
    uv run generate_data.py
"""

from __future__ import annotations

import random
import shutil
from datetime import date, timedelta
from pathlib import Path

import polars as pl

SEED = 42
TODAY = date(2026, 9, 1)
TABLE_NAMES = ["diamonds", "settings", "customers", "orders", "order_items"]


def load_tables(data_dir: Path) -> dict[str, pl.DataFrame]:
    """Return the 5 demo tables, generating and caching them on first call."""
    paths = {name: data_dir / f"{name}.parquet" for name in TABLE_NAMES}

    if all(path.exists() for path in paths.values()):
        return {name: pl.read_parquet(path) for name, path in paths.items()}

    tables = generate_tables()
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.write_parquet(paths[name])
    return tables


def generate_tables() -> dict[str, pl.DataFrame]:
    rng = random.Random(SEED)
    diamonds = generate_diamonds(rng)
    settings = generate_settings(rng)
    customers = generate_customers(rng)
    orders = generate_orders(rng, customers)
    order_items = generate_order_items(rng, orders, diamonds, settings)
    return {
        "diamonds": diamonds,
        "settings": settings,
        "customers": customers,
        "orders": orders,
        "order_items": order_items,
    }


def generate_diamonds(rng: random.Random, n: int = 400) -> pl.DataFrame:
    shapes = [
        "Round", "Princess", "Cushion", "Oval", "Emerald",
        "Radiant", "Asscher", "Marquise", "Pear", "Heart",
    ]
    shape_weights = [30, 12, 10, 12, 8, 8, 4, 4, 6, 6]
    cuts = ["Super Ideal", "Ideal", "Very Good", "Good"]
    cut_weights = [10, 40, 35, 15]
    cut_multiplier = {"Super Ideal": 1.15, "Ideal": 1.05, "Very Good": 0.95, "Good": 0.85}
    colors = ["D", "E", "F", "G", "H", "I", "J"]
    color_multiplier = {"D": 1.2, "E": 1.15, "F": 1.1, "G": 1.0, "H": 0.9, "I": 0.8, "J": 0.7}
    clarities = ["FL", "IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2"]
    clarity_multiplier = {
        "FL": 1.3, "IF": 1.25, "VVS1": 1.15, "VVS2": 1.1,
        "VS1": 1.0, "VS2": 0.95, "SI1": 0.85, "SI2": 0.75,
    }
    certifiers = ["GIA", "IGI", "AGS"]
    certifier_weights = [60, 30, 10]

    rows = []
    for i in range(1, n + 1):
        carat = round(rng.uniform(0.3, 3.5), 2)
        cut = rng.choices(cuts, weights=cut_weights)[0]
        color = rng.choice(colors)
        clarity = rng.choice(clarities)
        price = round(
            3000
            * (carat**1.8)
            * cut_multiplier[cut]
            * color_multiplier[color]
            * clarity_multiplier[clarity],
            -1,
        )
        rows.append(
            {
                "id": i,
                "shape": rng.choices(shapes, weights=shape_weights)[0],
                "carat": carat,
                "cut": cut,
                "color": color,
                "clarity": clarity,
                "certified_by": rng.choices(certifiers, weights=certifier_weights)[0],
                "price": price,
            }
        )
    return pl.DataFrame(rows)


def generate_settings(rng: random.Random, n: int = 50) -> pl.DataFrame:
    styles = ["Solitaire", "Halo", "Pave", "Three-Stone", "Vintage", "Bezel"]
    style_multiplier = {
        "Solitaire": 1.0, "Halo": 1.4, "Pave": 1.3,
        "Three-Stone": 1.5, "Vintage": 1.6, "Bezel": 1.1,
    }
    metal_price = {
        "Platinum": 1400, "18K White Gold": 900, "18K Yellow Gold": 850,
        "18K Rose Gold": 850, "Palladium": 1000,
    }
    metals = list(metal_price)

    rows = []
    for i in range(1, n + 1):
        style = rng.choice(styles)
        metal = rng.choice(metals)
        base_price = round(metal_price[metal] * style_multiplier[style] * rng.uniform(0.9, 1.1), -1)
        rows.append(
            {
                "id": i,
                "style": style,
                "metal": metal,
                "band_width_mm": round(rng.uniform(1.5, 3.5), 1),
                "base_price": base_price,
            }
        )
    return pl.DataFrame(rows)


def generate_customers(rng: random.Random, n: int = 200) -> pl.DataFrame:
    first_names = [
        "Olivia", "Liam", "Emma", "Noah", "Ava", "Ethan", "Sophia", "Mason",
        "Isabella", "James", "Mia", "Benjamin", "Charlotte", "Lucas", "Amelia",
        "Henry", "Harper", "Alexander", "Evelyn", "Michael",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Chen", "Kim", "Patel", "Nguyen",
        "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin",
    ]
    states = [
        "CA", "NY", "TX", "FL", "WA", "IL", "MA", "CO", "GA", "NC",
        "VA", "PA", "OH", "AZ", "OR", "NJ", "MD", "MN", "CT", "NV",
    ]
    channels = [
        "Organic Search", "Paid Social", "Referral", "Email", "Direct", "Showroom Walk-in",
    ]
    start = date(2022, 1, 1)
    span_days = (TODAY - start).days

    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "id": i,
                "name": f"{rng.choice(first_names)} {rng.choice(last_names)}",
                "state": rng.choice(states),
                "join_date": start + timedelta(days=rng.randint(0, span_days)),
                "acquisition_channel": rng.choice(channels),
            }
        )
    return pl.DataFrame(rows)


def generate_orders(rng: random.Random, customers: pl.DataFrame, n: int = 350) -> pl.DataFrame:
    statuses = ["Delivered", "Shipped", "Processing", "Returned"]
    status_weights = [70, 15, 10, 5]
    channels = ["Online", "Showroom"]
    join_date_by_customer = dict(zip(customers["id"], customers["join_date"]))
    customer_ids = customers["id"].to_list()

    rows = []
    for i in range(1, n + 1):
        customer_id = rng.choice(customer_ids)
        join_date = join_date_by_customer[customer_id]
        max_offset = max((TODAY - join_date).days, 1)
        order_date = join_date + timedelta(days=rng.randint(0, max_offset))
        rows.append(
            {
                "id": i,
                "customer_id": customer_id,
                "order_date": order_date,
                "status": rng.choices(statuses, weights=status_weights)[0],
                "channel": rng.choice(channels),
            }
        )
    return pl.DataFrame(rows)


def generate_order_items(
    rng: random.Random,
    orders: pl.DataFrame,
    diamonds: pl.DataFrame,
    settings: pl.DataFrame,
    n: int = 450,
) -> pl.DataFrame:
    item_types = ["Engagement Ring", "Loose Diamond", "Wedding Band", "Earrings", "Necklace"]
    item_type_weights = [35, 15, 20, 15, 15]
    order_ids = orders["id"].to_list()
    diamond_ids = diamonds["id"].to_list()
    setting_ids = settings["id"].to_list()
    price_by_diamond = dict(zip(diamonds["id"], diamonds["price"]))
    price_by_setting = dict(zip(settings["id"], settings["base_price"]))

    rows = []
    for i in range(1, n + 1):
        item_type = rng.choices(item_types, weights=item_type_weights)[0]
        diamond_id: int | None = None
        setting_id: int | None = None

        if item_type == "Engagement Ring":
            diamond_id = rng.choice(diamond_ids)
            setting_id = rng.choice(setting_ids)
            price = price_by_diamond[diamond_id] + price_by_setting[setting_id]
        elif item_type == "Loose Diamond":
            diamond_id = rng.choice(diamond_ids)
            price = price_by_diamond[diamond_id]
        elif item_type == "Wedding Band":
            setting_id = rng.choice(setting_ids)
            price = round(price_by_setting[setting_id] * rng.uniform(0.7, 1.0), -1)
        elif item_type == "Earrings":
            price = round(rng.uniform(400, 4000), -1)
        else:  # Necklace
            price = round(rng.uniform(500, 6000), -1)

        rows.append(
            {
                "id": i,
                "order_id": rng.choice(order_ids),
                "item_type": item_type,
                "diamond_id": diamond_id,
                "setting_id": setting_id,
                "price": price,
            }
        )
    return pl.DataFrame(rows)


if __name__ == "__main__":
    target_dir = Path(__file__).parent / "data"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    load_tables(target_dir)
    print(f"Wrote {', '.join(TABLE_NAMES)} to {target_dir}")
