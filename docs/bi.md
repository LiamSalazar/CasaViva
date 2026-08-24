# Business Intelligence

`/administracion/bi` presenta visitantes, sesiones, fichas vistas, consultas, visitas y ventas contra el periodo anterior, además de tráfico diario, inventario y resultados por propiedad. Distingue visitas programadas, realizadas, canceladas y no-show; la conversión efectiva usa sólo `COMPLETED`. "Adiciones a favoritos" significa eventos `favorite_added`, no favoritos actuales. No hay scores ni datos inventados; sin denominador o gasto se muestra `—`.

"Actividad por etapa" cuenta hechos del periodo y no afirma que pertenezcan a las mismas personas. La cohorte parte de leads adquiridos en el periodo. Cada horizonte de 30/60/90 días se calcula desde la fecha de adquisición de cada lead —no desde el fin del periodo—; `lifetime` no impone límite. Marketing separa adquisición por campaña de ventas cerradas en el periodo por origen first-touch, aunque la sesión ocurriera antes. Las campañas con gasto y cero sesiones permanecen visibles y sus costos sin denominador se muestran `—`.

El gasto existe a nivel campaña/fecha y se suma una sola vez. El desglose source/medium/content muestra conversiones, pero gasto `—`: no se reparte ni duplica. Gastos anulados no entran en BI.

Los contratos HTTP son `/api/v1/admin/bi/overview/`, `listings/`, `searches/`, `marketing/`, `sales/` y `decisions/`. Todos exigen MFA y `analytics.view_bi`, aceptan `days` entre 1 y 366 y trabajan sobre agregados acotados.

Contratos lógicos estables: `vw_daily_traffic`, `vw_listing_performance`, `vw_lead_funnel`, `vw_campaign_performance`, `vw_inventory_summary`, `vw_sales_summary` y `vw_search_demand`. Actualmente se implementan mediante servicios ORM agregados. Si su costo crece se revisarán índices y planes, luego vistas/materialización y finalmente marts, manteniendo el contrato del frontend.
