-- GreenCode controlled SQL benchmark dataset.
--
-- A small e-commerce schema with deterministic synthetic data (seeded random so
-- every run of this script produces identical tables). Sizes are chosen so that
-- inefficient queries take tens to hundreds of milliseconds while the dataset
-- still loads in seconds on a laptop.
--
--   customers    50,000 rows
--   products      2,000 rows
--   orders      200,000 rows
--   order_items 600,000 rows
--
-- Run with:  psql "$GREENCODE_BENCHMARK_DATABASE_URL" -f database/seed/bench_dataset.sql

DROP SCHEMA IF EXISTS bench CASCADE;
CREATE SCHEMA bench;
SET search_path TO bench, public;
SELECT setseed(0.42);

CREATE TABLE customers (
    id          integer PRIMARY KEY,
    email       text NOT NULL,
    full_name   text NOT NULL,
    country     char(2) NOT NULL,
    created_at  timestamp NOT NULL,
    is_active   boolean NOT NULL
);

INSERT INTO customers (id, email, full_name, country, created_at, is_active)
SELECT g,
       'user' || g || '@' || (ARRAY['gmail.com','outlook.com','tcd.ie','tudublin.ie','example.org'])[1 + (g % 5)],
       'Customer ' || g,
       (ARRAY['IE','GB','DE','FR','US','ES','NL','PL'])[1 + (g % 8)],
       timestamp '2019-01-01' + (random() * 365 * 6) * interval '1 day',
       random() < 0.9
FROM generate_series(1, 50000) AS g;

CREATE TABLE products (
    id          integer PRIMARY KEY,
    sku         text NOT NULL,
    name        text NOT NULL,
    category    text NOT NULL,
    price_cents integer NOT NULL
);

INSERT INTO products (id, sku, name, category, price_cents)
SELECT g,
       'SKU-' || lpad(g::text, 6, '0'),
       'Product ' || g,
       (ARRAY['books','electronics','garden','toys','clothing','grocery'])[1 + (g % 6)],
       500 + (random() * 50000)::int
FROM generate_series(1, 2000) AS g;

CREATE TABLE orders (
    id            integer PRIMARY KEY,
    customer_id   integer NOT NULL REFERENCES customers(id),
    status        text NOT NULL,
    created_at    timestamp NOT NULL,
    total_cents   integer NOT NULL
);

INSERT INTO orders (id, customer_id, status, created_at, total_cents)
SELECT g,
       1 + (random() * 49999)::int,
       (ARRAY['pending','paid','shipped','delivered','cancelled'])[1 + (g % 5)],
       timestamp '2021-01-01' + (random() * 365 * 4) * interval '1 day',
       100 + (random() * 100000)::int
FROM generate_series(1, 200000) AS g;

CREATE TABLE order_items (
    id          integer PRIMARY KEY,
    order_id    integer NOT NULL REFERENCES orders(id),
    product_id  integer NOT NULL REFERENCES products(id),
    quantity    integer NOT NULL,
    unit_cents  integer NOT NULL
);

INSERT INTO order_items (id, order_id, product_id, quantity, unit_cents)
SELECT g,
       1 + (g % 200000),
       1 + (random() * 1999)::int,
       1 + (random() * 4)::int,
       500 + (random() * 50000)::int
FROM generate_series(1, 600000) AS g;

-- Indexes that a well-written query can use (and a badly-written one defeats).
CREATE INDEX idx_customers_email       ON customers (email);
CREATE INDEX idx_customers_country     ON customers (country);
CREATE INDEX idx_customers_created_at  ON customers (created_at);
CREATE INDEX idx_orders_customer_id    ON orders (customer_id);
CREATE INDEX idx_orders_created_at     ON orders (created_at);
CREATE INDEX idx_orders_status         ON orders (status);
CREATE INDEX idx_order_items_order_id  ON order_items (order_id);
CREATE INDEX idx_order_items_product   ON order_items (product_id);
CREATE INDEX idx_products_category     ON products (category);

ANALYZE customers;
ANALYZE products;
ANALYZE orders;
ANALYZE order_items;
