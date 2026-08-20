# Business Intelligence

`/administracion/bi` presenta visitantes, sesiones, fichas vistas, consultas, visitas y ventas contra el periodo anterior, además de tráfico diario, embudo, inventario y resultados por propiedad. Incluye demanda de búsquedas, búsquedas sin resultados, filtros, atribución por source/medium/campaign/content, gasto y costos, valor/comisiones/tiempo de cierre e información factual para decisiones. No hay scores ni datos inventados; sin denominador o gasto se muestra `—`.

Los contratos HTTP son `/api/v1/admin/bi/overview/`, `listings/`, `searches/`, `marketing/`, `sales/` y `decisions/`. Todos exigen MFA y `analytics.view_bi`, aceptan `days` entre 1 y 366 y trabajan sobre agregados acotados.

Contratos lógicos estables: `vw_daily_traffic`, `vw_listing_performance`, `vw_lead_funnel`, `vw_campaign_performance`, `vw_inventory_summary`, `vw_sales_summary` y `vw_search_demand`. Actualmente se implementan mediante servicios ORM agregados. Si su costo crece se revisarán índices y planes, luego vistas/materialización y finalmente marts, manteniendo el contrato del frontend.
