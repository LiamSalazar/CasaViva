# Runbook Growth

Las alarmas sólo dicen “Revisar activación de Growth”. Revisar CPU sostenida 65–70%, RAM 75–80%, saturación legítima repetida, 5xx por capacidad, competencia DB por RAM/I/O, RTO inaceptable, necesidad de más de un nodo o trabajos que afecten web.

Antes de habilitar Growth, PostgreSQL debe estar fuera de EC2 y el cambio debe aprobarse manualmente. Elegir ALB + nodos stateless o ECS según la evaluación del momento. Entonces configurar min 1, desired 1, max 4; sólo después el scaling dentro de esos límites es automático. El número de visitantes por sí solo no activa Growth.
