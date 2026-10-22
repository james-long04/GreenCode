---
title: Bench dataset
created: 2026-10-22
project: GreenCode
tags: [rules, sql, dataset]
---

# The controlled SQL dataset (schema `bench`)

Built deterministically by `database/seed/bench_dataset.sql` (`python scripts\seed_bench_dataset.py`), ~850 000 rows, so every SQL case is measured against identical data and planner statistics.

| Table | Rows | Columns |
|---|---|---|
| `customers` | 50 000 | `id, email, full_name, country (IE/GB/DE/FR/US/ES/NL/PL), created_at, is_active` |
| `products` | 2 000 | `id, sku, name, category (books/electronics/garden/toys/clothing/grocery), price_cents` |
| `orders` | 200 000 | `id, customer_id → customers, status (pending/paid/shipped/delivered/cancelled), created_at, total_cents` |
| `order_items` | 600 000 | `id, order_id → orders, product_id → products, quantity, unit_cents` |

Indexes: `customers(email)`, `customers(country)`, `customers(created_at)`, `orders(customer_id)` and more — see the seed file.

The schema DDL summary is injected into SQL prompts (`benchdb.schema_ddl_summary()`), so the model knows the tables.
