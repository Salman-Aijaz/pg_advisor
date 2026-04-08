# pg-advisor Report

**Database:** `localhost:5432/MyPostgres`  
**Generated:** 2026-04-08 13:57:12  
**Total Issues:** 50

| Severity | Count |
|----------|-------|
| ❌ Critical | 10 |
| ⚠️ Warning  | 27  |
| ℹ️ Info     | 13     |

---

## Issue Summary

| Table | Column | Severity | Rule | Message |
|-------|--------|----------|------|---------|
| `ads` | `price` | ❌ critical | `FLOAT_FOR_MONEY` | 'ads.price' uses FLOAT - this may cause precision issues. |
| `ads` | `user_id` | ❌ critical | `FK_WITHOUT_INDEX` | 'ads.user_id' → 'users' is a foreign key without indexed - JOIN queries will be slow. |
| `favorites` | `ad_id` | ❌ critical | `FK_WITHOUT_INDEX` | 'favorites.ad_id' → 'ads' is a foreign key without indexed - JOIN queries will be slow. |
| `favorites` | `user_id` | ❌ critical | `FK_WITHOUT_INDEX` | 'favorites.user_id' → 'users' is a foreign key without indexed - JOIN queries will be slow. |
| `orders` | `base_price` | ❌ critical | `FLOAT_FOR_MONEY` | 'orders.base_price' uses FLOAT - this may cause precision issues. |
| `orders` | `discount_amount` | ❌ critical | `FLOAT_FOR_MONEY` | 'orders.discount_amount' uses FLOAT - this may cause precision issues. |
| `orders` | `final_amount` | ❌ critical | `FLOAT_FOR_MONEY` | 'orders.final_amount' uses FLOAT - this may cause precision issues. |
| `payments` | `amount` | ❌ critical | `FLOAT_FOR_MONEY` | 'payments.amount' uses FLOAT - this may cause precision issues. |
| `watch_list` | `user_id` | ❌ critical | `FK_WITHOUT_INDEX` | 'watch_list.user_id' → 'users' is a foreign key without indexed - JOIN queries will be slow. |
| `watch_list_ad` | `ad_id` | ❌ critical | `FK_WITHOUT_INDEX` | 'watch_list_ad.ad_id' → 'ads' is a foreign key without indexed - JOIN queries will be slow. |
| `ads` | — | ⚠️ warning | `DUPLICATE_INDEX` | Duplicate index found on 'ads' for columns ['id']: 'ix_ads_id' and 'ads_pkey'. |
| `ads` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'ix_ads_id' on 'ads' has never been used (idx_scan = 0). |
| `favorites` | — | ⚠️ warning | `DUPLICATE_INDEX` | Duplicate index found on 'favorites' for columns ['id']: 'ix_favorites_id' and 'favorites_pkey'. |
| `favorites` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'ix_favorites_id' on 'favorites' has never been used (idx_scan = 0). |
| `orders` | — | ⚠️ warning | `DUPLICATE_INDEX` | Duplicate index found on 'orders' for columns ['order_id']: 'orders_order_id_key' and 'idx_orders_order_id'. |
| `orders` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_orders_ad_id' on 'orders' has never been used (idx_scan = 0). |
| `orders` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_orders_order_id' on 'orders' has never been used (idx_scan = 0). |
| `orders` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_orders_status' on 'orders' has never been used (idx_scan = 0). |
| `orders` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_orders_user_id' on 'orders' has never been used (idx_scan = 0). |
| `orders` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'orders_order_id_key' on 'orders' has never been used (idx_scan = 0). |
| `payments` | — | ⚠️ warning | `DUPLICATE_INDEX` | Duplicate index found on 'payments' for columns ['order_id']: 'payments_order_id_key' and 'idx_payments_order_id'. |
| `payments` | — | ⚠️ warning | `DUPLICATE_INDEX` | Duplicate index found on 'payments' for columns ['payment_id']: 'payments_payment_id_key' and 'idx_payments_payment_id'. |
| `payments` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_payments_created_at' on 'payments' has never been used (idx_scan = 0). |
| `payments` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_payments_order_id' on 'payments' has never been used (idx_scan = 0). |
| `payments` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_payments_payment_id' on 'payments' has never been used (idx_scan = 0). |
| `payments` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_payments_status' on 'payments' has never been used (idx_scan = 0). |
| `payments` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'idx_payments_transaction_id' on 'payments' has never been used (idx_scan = 0). |
| `payments` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'payments_order_id_key' on 'payments' has never been used (idx_scan = 0). |
| `payments` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'payments_payment_id_key' on 'payments' has never been used (idx_scan = 0). |
| `users` | — | ⚠️ warning | `DUPLICATE_INDEX` | Duplicate index found on 'users' for columns ['id']: 'users_pkey' and 'ix_users_id'. |
| `users` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'ix_users_email' on 'users' has never been used (idx_scan = 0). |
| `users` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'ix_users_id' on 'users' has never been used (idx_scan = 0). |
| `users` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'users_google_id_key' on 'users' has never been used (idx_scan = 0). |
| `watch_list` | — | ⚠️ warning | `DUPLICATE_INDEX` | Duplicate index found on 'watch_list' for columns ['id']: 'watch_list_pkey' and 'ix_watch_list_id'. |
| `watch_list` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'ix_watch_list_id' on 'watch_list' has never been used (idx_scan = 0). |
| `watch_list_ad` | — | ⚠️ warning | `DUPLICATE_INDEX` | Duplicate index found on 'watch_list_ad' for columns ['id']: 'watch_list_ad_pkey' and 'ix_watch_list_ad_id'. |
| `watch_list_ad` | — | ⚠️ warning | `UNUSED_INDEX` | Index 'ix_watch_list_ad_id' on 'watch_list_ad' has never been used (idx_scan = 0). |
| `ads` | — | ℹ️ info | `MISSING_UPDATED_AT` | Table 'ads' does not have updated_at - cannot track changes. |
| `ads` | `seller_name` | ℹ️ info | `MISSING_NOT_NULL` | 'ads.seller_name' is nullable is allowing NULL really intended?  |
| `favorites` | — | ℹ️ info | `MISSING_UPDATED_AT` | Table 'favorites' does not have updated_at - cannot track changes. |
| `orders` | `status` | ℹ️ info | `LOW_CARDINALITY_INDEX` | Index exists on 'orders.status', but this appears to be a low-cardinality column — index benefit will be limited. |
| `payments` | `account_type_id` | ℹ️ info | `MISSING_NOT_NULL` | 'payments.account_type_id' is nullable is allowing NULL really intended?  |
| `payments` | `status_code` | ℹ️ info | `MISSING_NOT_NULL` | 'payments.status_code' is nullable is allowing NULL really intended?  |
| `payments` | `status` | ℹ️ info | `LOW_CARDINALITY_INDEX` | Index exists on 'payments.status', but this appears to be a low-cardinality column — index benefit will be limited. |
| `users` | — | ℹ️ info | `MISSING_UPDATED_AT` | Table 'users' does not have updated_at - cannot track changes. |
| `users` | `name` | ℹ️ info | `MISSING_NOT_NULL` | 'users.name' is nullable is allowing NULL really intended?  |
| `users` | `email_verified` | ℹ️ info | `MISSING_NOT_NULL` | 'users.email_verified' is nullable is allowing NULL really intended?  |
| `watch_list` | — | ℹ️ info | `MISSING_UPDATED_AT` | Table 'watch_list' does not have updated_at - cannot track changes. |
| `watch_list_ad` | — | ℹ️ info | `MISSING_UPDATED_AT` | Table 'watch_list_ad' does not have updated_at - cannot track changes. |
| `—` | — | ℹ️ info | `NO_STAT_STATEMENTS` | pg_stat_statements extension is not enabled — query analysis skipped. |

---

## Detailed Findings

### Table: `ads`

#### ❌ `FLOAT_FOR_MONEY``.price`

**Severity:** CRITICAL  
**Message:** 'ads.price' uses FLOAT - this may cause precision issues.

**Recommended Fix:**
```sql
ALTER TABLE ads ALTER COLUMN price TYPE NUMERIC(12,2);
```

#### ❌ `FK_WITHOUT_INDEX``.user_id`

**Severity:** CRITICAL  
**Message:** 'ads.user_id' → 'users' is a foreign key without indexed - JOIN queries will be slow.

**Recommended Fix:**
```sql
CREATE INDEX idx_ads_user_id ON ads(user_id);
```

#### ⚠️ `DUPLICATE_INDEX`

**Severity:** WARNING  
**Message:** Duplicate index found on 'ads' for columns ['id']: 'ix_ads_id' and 'ads_pkey'.

**Recommended Fix:**
```sql
DROP INDEX ix_ads_id;  -- or drop 'ads_pkey'
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'ix_ads_id' on 'ads' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX ix_ads_id;  -- verify before dropping
```

#### ℹ️ `MISSING_UPDATED_AT`

**Severity:** INFO  
**Message:** Table 'ads' does not have updated_at - cannot track changes.

**Recommended Fix:**
```sql
ALTER TABLE ads ADD COLUMN updated_at TIMESTAMPTZ;
-- Also add a trigger to automatically update this column
```

#### ℹ️ `MISSING_NOT_NULL``.seller_name`

**Severity:** INFO  
**Message:** 'ads.seller_name' is nullable is allowing NULL really intended? 

**Recommended Fix:**
```sql
ALTER TABLE ads ALTER COLUMN seller_name SET NOT NULL;
```

---

### Table: `favorites`

#### ❌ `FK_WITHOUT_INDEX``.ad_id`

**Severity:** CRITICAL  
**Message:** 'favorites.ad_id' → 'ads' is a foreign key without indexed - JOIN queries will be slow.

**Recommended Fix:**
```sql
CREATE INDEX idx_favorites_ad_id ON favorites(ad_id);
```

#### ❌ `FK_WITHOUT_INDEX``.user_id`

**Severity:** CRITICAL  
**Message:** 'favorites.user_id' → 'users' is a foreign key without indexed - JOIN queries will be slow.

**Recommended Fix:**
```sql
CREATE INDEX idx_favorites_user_id ON favorites(user_id);
```

#### ⚠️ `DUPLICATE_INDEX`

**Severity:** WARNING  
**Message:** Duplicate index found on 'favorites' for columns ['id']: 'ix_favorites_id' and 'favorites_pkey'.

**Recommended Fix:**
```sql
DROP INDEX ix_favorites_id;  -- or drop 'favorites_pkey'
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'ix_favorites_id' on 'favorites' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX ix_favorites_id;  -- verify before dropping
```

#### ℹ️ `MISSING_UPDATED_AT`

**Severity:** INFO  
**Message:** Table 'favorites' does not have updated_at - cannot track changes.

**Recommended Fix:**
```sql
ALTER TABLE favorites ADD COLUMN updated_at TIMESTAMPTZ;
-- Also add a trigger to automatically update this column
```

---

### Table: `orders`

#### ❌ `FLOAT_FOR_MONEY``.base_price`

**Severity:** CRITICAL  
**Message:** 'orders.base_price' uses FLOAT - this may cause precision issues.

**Recommended Fix:**
```sql
ALTER TABLE orders ALTER COLUMN base_price TYPE NUMERIC(12,2);
```

#### ❌ `FLOAT_FOR_MONEY``.discount_amount`

**Severity:** CRITICAL  
**Message:** 'orders.discount_amount' uses FLOAT - this may cause precision issues.

**Recommended Fix:**
```sql
ALTER TABLE orders ALTER COLUMN discount_amount TYPE NUMERIC(12,2);
```

#### ❌ `FLOAT_FOR_MONEY``.final_amount`

**Severity:** CRITICAL  
**Message:** 'orders.final_amount' uses FLOAT - this may cause precision issues.

**Recommended Fix:**
```sql
ALTER TABLE orders ALTER COLUMN final_amount TYPE NUMERIC(12,2);
```

#### ⚠️ `DUPLICATE_INDEX`

**Severity:** WARNING  
**Message:** Duplicate index found on 'orders' for columns ['order_id']: 'orders_order_id_key' and 'idx_orders_order_id'.

**Recommended Fix:**
```sql
DROP INDEX orders_order_id_key;  -- or drop 'idx_orders_order_id'
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_orders_ad_id' on 'orders' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_orders_ad_id;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_orders_order_id' on 'orders' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_orders_order_id;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_orders_status' on 'orders' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_orders_status;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_orders_user_id' on 'orders' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_orders_user_id;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'orders_order_id_key' on 'orders' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX orders_order_id_key;  -- verify before dropping
```

#### ℹ️ `LOW_CARDINALITY_INDEX``.status`

**Severity:** INFO  
**Message:** Index exists on 'orders.status', but this appears to be a low-cardinality column — index benefit will be limited.

**Recommended Fix:**
```sql
DROP INDEX idx_orders_status;  -- Consider partial index: CREATE INDEX ON orders(status) WHERE status = true;
```

---

### Table: `payments`

#### ❌ `FLOAT_FOR_MONEY``.amount`

**Severity:** CRITICAL  
**Message:** 'payments.amount' uses FLOAT - this may cause precision issues.

**Recommended Fix:**
```sql
ALTER TABLE payments ALTER COLUMN amount TYPE NUMERIC(12,2);
```

#### ⚠️ `DUPLICATE_INDEX`

**Severity:** WARNING  
**Message:** Duplicate index found on 'payments' for columns ['order_id']: 'payments_order_id_key' and 'idx_payments_order_id'.

**Recommended Fix:**
```sql
DROP INDEX payments_order_id_key;  -- or drop 'idx_payments_order_id'
```

#### ⚠️ `DUPLICATE_INDEX`

**Severity:** WARNING  
**Message:** Duplicate index found on 'payments' for columns ['payment_id']: 'payments_payment_id_key' and 'idx_payments_payment_id'.

**Recommended Fix:**
```sql
DROP INDEX payments_payment_id_key;  -- or drop 'idx_payments_payment_id'
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_payments_created_at' on 'payments' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_payments_created_at;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_payments_order_id' on 'payments' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_payments_order_id;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_payments_payment_id' on 'payments' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_payments_payment_id;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_payments_status' on 'payments' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_payments_status;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'idx_payments_transaction_id' on 'payments' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX idx_payments_transaction_id;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'payments_order_id_key' on 'payments' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX payments_order_id_key;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'payments_payment_id_key' on 'payments' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX payments_payment_id_key;  -- verify before dropping
```

#### ℹ️ `MISSING_NOT_NULL``.account_type_id`

**Severity:** INFO  
**Message:** 'payments.account_type_id' is nullable is allowing NULL really intended? 

**Recommended Fix:**
```sql
ALTER TABLE payments ALTER COLUMN account_type_id SET NOT NULL;
```

#### ℹ️ `MISSING_NOT_NULL``.status_code`

**Severity:** INFO  
**Message:** 'payments.status_code' is nullable is allowing NULL really intended? 

**Recommended Fix:**
```sql
ALTER TABLE payments ALTER COLUMN status_code SET NOT NULL;
```

#### ℹ️ `LOW_CARDINALITY_INDEX``.status`

**Severity:** INFO  
**Message:** Index exists on 'payments.status', but this appears to be a low-cardinality column — index benefit will be limited.

**Recommended Fix:**
```sql
DROP INDEX idx_payments_status;  -- Consider partial index: CREATE INDEX ON payments(status) WHERE status = true;
```

---

### Table: `users`

#### ⚠️ `DUPLICATE_INDEX`

**Severity:** WARNING  
**Message:** Duplicate index found on 'users' for columns ['id']: 'users_pkey' and 'ix_users_id'.

**Recommended Fix:**
```sql
DROP INDEX users_pkey;  -- or drop 'ix_users_id'
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'ix_users_email' on 'users' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX ix_users_email;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'ix_users_id' on 'users' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX ix_users_id;  -- verify before dropping
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'users_google_id_key' on 'users' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX users_google_id_key;  -- verify before dropping
```

#### ℹ️ `MISSING_UPDATED_AT`

**Severity:** INFO  
**Message:** Table 'users' does not have updated_at - cannot track changes.

**Recommended Fix:**
```sql
ALTER TABLE users ADD COLUMN updated_at TIMESTAMPTZ;
-- Also add a trigger to automatically update this column
```

#### ℹ️ `MISSING_NOT_NULL``.name`

**Severity:** INFO  
**Message:** 'users.name' is nullable is allowing NULL really intended? 

**Recommended Fix:**
```sql
ALTER TABLE users ALTER COLUMN name SET NOT NULL;
```

#### ℹ️ `MISSING_NOT_NULL``.email_verified`

**Severity:** INFO  
**Message:** 'users.email_verified' is nullable is allowing NULL really intended? 

**Recommended Fix:**
```sql
ALTER TABLE users ALTER COLUMN email_verified SET NOT NULL;
```

---

### Table: `watch_list`

#### ❌ `FK_WITHOUT_INDEX``.user_id`

**Severity:** CRITICAL  
**Message:** 'watch_list.user_id' → 'users' is a foreign key without indexed - JOIN queries will be slow.

**Recommended Fix:**
```sql
CREATE INDEX idx_watch_list_user_id ON watch_list(user_id);
```

#### ⚠️ `DUPLICATE_INDEX`

**Severity:** WARNING  
**Message:** Duplicate index found on 'watch_list' for columns ['id']: 'watch_list_pkey' and 'ix_watch_list_id'.

**Recommended Fix:**
```sql
DROP INDEX watch_list_pkey;  -- or drop 'ix_watch_list_id'
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'ix_watch_list_id' on 'watch_list' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX ix_watch_list_id;  -- verify before dropping
```

#### ℹ️ `MISSING_UPDATED_AT`

**Severity:** INFO  
**Message:** Table 'watch_list' does not have updated_at - cannot track changes.

**Recommended Fix:**
```sql
ALTER TABLE watch_list ADD COLUMN updated_at TIMESTAMPTZ;
-- Also add a trigger to automatically update this column
```

---

### Table: `watch_list_ad`

#### ❌ `FK_WITHOUT_INDEX``.ad_id`

**Severity:** CRITICAL  
**Message:** 'watch_list_ad.ad_id' → 'ads' is a foreign key without indexed - JOIN queries will be slow.

**Recommended Fix:**
```sql
CREATE INDEX idx_watch_list_ad_ad_id ON watch_list_ad(ad_id);
```

#### ⚠️ `DUPLICATE_INDEX`

**Severity:** WARNING  
**Message:** Duplicate index found on 'watch_list_ad' for columns ['id']: 'watch_list_ad_pkey' and 'ix_watch_list_ad_id'.

**Recommended Fix:**
```sql
DROP INDEX watch_list_ad_pkey;  -- or drop 'ix_watch_list_ad_id'
```

#### ⚠️ `UNUSED_INDEX`

**Severity:** WARNING  
**Message:** Index 'ix_watch_list_ad_id' on 'watch_list_ad' has never been used (idx_scan = 0).

**Recommended Fix:**
```sql
DROP INDEX ix_watch_list_ad_id;  -- verify before dropping
```

#### ℹ️ `MISSING_UPDATED_AT`

**Severity:** INFO  
**Message:** Table 'watch_list_ad' does not have updated_at - cannot track changes.

**Recommended Fix:**
```sql
ALTER TABLE watch_list_ad ADD COLUMN updated_at TIMESTAMPTZ;
-- Also add a trigger to automatically update this column
```

---

### Table: `—`

#### ℹ️ `NO_STAT_STATEMENTS`

**Severity:** INFO  
**Message:** pg_stat_statements extension is not enabled — query analysis skipped.

**Recommended Fix:**
```sql
CREATE EXTENSION pg_stat_statements;  -- also enable in postgresql.conf
```

---

## Rule Reference

| Rule ID | Category | What it checks |
|---------|----------|----------------|
| `MISSING_PK` | Schema | Table bina primary key ke |
| `FLOAT_FOR_MONEY` | Schema | FLOAT column for price/balance/total |
| `FK_WITHOUT_INDEX` | Schema | Foreign key column pe index nahi |
| `NULLABLE_PK` | Schema | Primary key nullable mark hai |
| `MISSING_CREATED_AT` | Schema | created_at column nahi hai |
| `MISSING_UPDATED_AT` | Schema | updated_at column nahi hai |
| `BOOL_AS_INT` | Schema | is_*/has_* column wrong type mein |
| `GOD_TABLE` | Schema | 30+ columns — normalize karo |
| `MISSING_NOT_NULL` | Schema | Important column nullable hai |
| `DUPLICATE_INDEX` | Index | Same columns pe 2+ indexes |
| `UNUSED_INDEX` | Index | Index kabhi use nahi hua |
| `LOW_CARDINALITY_INDEX` | Index | Boolean/status pe index |
| `SLOW_QUERY` | Query | 500ms+ avg execution time |
| `HIGH_FREQUENCY_QUERY` | Query | 1000+ calls — cache karo |
| `SELECT_STAR` | Query | SELECT * bad practice |

---

*Generated by [pg-advisor](https://github.com/yourname/pg-advisor)*