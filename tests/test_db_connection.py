# from mcp_servers.database_server import run_sql_query

# print(run_sql_query("""
#     SELECT b.branch_name,
#            ROUND(SUM(oi.quantity*oi.unit_price - oi.discount_amount)::numeric, 2) AS revenue
#     FROM order_items oi
#     JOIN orders o ON o.order_id = oi.order_id
#     JOIN branches b ON b.branch_id = o.branch_id
#     WHERE o.order_status <> 'cancelled'
#     GROUP BY 1 ORDER BY 2 DESC;
# """))
# print(run_sql_query("DROP TABLE orders"))

# from mcp_servers.database_server import get_schema_info
# print(get_schema_info())

from mcp_servers.database_server import run_sql_query
print(run_sql_query("""
    SELECT sales_channel,
           COUNT(*) AS orders,
           COUNT(*) FILTER (WHERE branch_id = fulfillment_branch_id) AS same_branch,
           COUNT(*) FILTER (WHERE branch_id <> fulfillment_branch_id) AS different_branch
    FROM orders GROUP BY 1;
"""))