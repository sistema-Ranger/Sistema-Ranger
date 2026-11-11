# 01 · Visión y Alcance

## Problema

La supervisión de infraestructura suele ser **reactiva**: se revisan dashboards y logs manualmente o se actúa cuando una alerta indica que el fallo ya ocurrió. Síntomas típicos:

- Incrementos anormales de CPU, memoria, disco o tráfico.
- Caídas o reinicios frecuentes de servidores y servicios.
- Aumento progresivo de tiempos de respuesta.
- Errores recurrentes en logs.
- Saturación de recursos y cuellos de botella.
- Degradación previa a una interrupción completa.
- Exceso de alertas (ruido) que oculta lo relevante.
- Dificultad para correlacionar métricas, logs y eventos de distintos componentes.

## Propuesta de valor

Ranger pasa de un enfoque **reactivo a preventivo**: centraliza métricas/logs/eventos, aprende el comportamiento normal, detecta desviaciones, estima riesgo y emite alertas **priorizadas con evidencia y acción sugerida**. No es un CRUD ni un dashboard pasivo: genera conocimiento accionable.

## Objetivo general

Desarrollar un sistema web inteligente de monitoreo y predicción de fallos que procese métricas, logs y eventos de servidores y aplicaciones para detectar anomalías, anticipar fallos, degradaciones y cuellos de botella, generando alertas inteligentes que apoyen la respuesta técnica.

## Objetivos específicos (trazables)

| ID | Objetivo | Módulo / doc |
|---|---|---|
| OE1 | Centralizar métricas, logs y eventos | Collector, `05` ingest |
| OE2 | Monitorear CPU, memoria, disco, red, latencia, disponibilidad, errores | `04` metrics |
| OE3 | Procesar y normalizar datos históricos y casi en tiempo real | `07` ETL |
| OE4 | Identificar anomalías y patrones de degradación | `07` anomalías |
| OE5 | Modelo predictivo / de anomalías para estimar riesgo | `07` modelo |
| OE6 | Detectar cuellos de botella por correlación de métricas | `07` correlación |
| OE7 | Alertas priorizadas por severidad, comportamiento y riesgo | `07` motor de alertas |
| OE8 | Dashboards con indicadores, tendencias, eventos y estado | `06` |
| OE9 | Registrar incidentes e historial de alertas | `04` incidents |
| OE10 | Validar con MVP, datos simulados/reales y pruebas controladas | `09` pruebas |

## Usuarios y roles

| Rol (código) | Usuario | Permisos principales |
|---|---|---|
| `admin` | Administrador | Todo: usuarios, roles, hosts, reglas, configuración |
| `infra` | Ingeniero/Admin. de infraestructura | Hosts, alertas (ack/resolver), incidentes, reglas |
| `developer` | Desarrollador | Lectura de métricas/logs, comentar incidentes |
| `analyst` | Analista / Observabilidad | Lectura de todo + predicciones, reportes, exportar |
| `viewer` | Gerente / Consulta | Solo dashboard general, disponibilidad e incidentes |

## Alcance funcional del MVP

| Módulo | Incluye |
|---|---|
| **Seguridad y usuarios** | Login, JWT, roles y permisos, gestión básica de usuarios |
| **Infraestructura** | Registro de servidores/aplicaciones/servicios, agrupación por entorno/área, estado y disponibilidad |
| **Métricas** | CPU, memoria, disco, red; latencia y tiempos de respuesta; disponibilidad y tasa de error; históricos por componente |
| **Logs y eventos** | Recepción y almacenamiento, clasificación por severidad (info/warning/error/critical), búsqueda y filtros |
| **Observabilidad** | Estado general, tendencias, uso de recursos, vista por host |
| **Detección de anomalías** | Comportamiento fuera de patrón, reglas de umbral configurables, tendencias, correlación básica métricas↔eventos |
| **Predicción y riesgo** | Modelo de detección/predicción, riesgo por componente, horizonte configurable, evaluación con métricas |
| **Alertas inteligentes** | Por anomalía y degradación progresiva, priorización, notificación in‑app, historial y estado |
| **Incidentes y reportes** | Registro y seguimiento de incidentes, reportes de disponibilidad/rendimiento, exportación CSV |
| **API y documentación** | REST con Swagger/OpenAPI, manual de usuario, documentación técnica |

## Fuera de alcance (no implementar)

- Control directo o reparación automática de servidores.
- Agentes propietarios en infraestructura empresarial real fuera del entorno de prueba.
- Integraciones completas con plataformas comerciales de observabilidad.
- Remediación automática ejecutando comandos en servidores productivos.
- App móvil nativa.
- Deep Learning avanzado que requiera grandes volúmenes de datos.
- Despliegue a gran escala / SaaS multiempresa.
- Gestión de activos físicos no tecnológicos.

## Criterios de éxito de la demo (2 dic)

1. Levantar todo con `docker compose up --build`.
2. Al menos 2–3 hosts simulados enviando métricas y logs.
3. Inyectar un escenario de fallo (p. ej. fuga de memoria + errores 5xx) y mostrar que Ranger **eleva el riesgo y alerta antes** de la "caída" simulada.
4. Mostrar la alerta con componente, evidencia, tendencia, riesgo y acción sugerida.
5. Mostrar métricas del modelo (precision, recall, F1) en la pantalla Predicciones.
6. Registrar el incidente y exportar un reporte.

## Ejemplo de alerta objetivo

| Campo | Ejemplo |
|---|---|
| Componente | Servidor API-01 |
| CPU | 92 % durante 18 minutos |
| Memoria | 87 % y tendencia ascendente |
| Latencia | Aumento de 180 ms a 620 ms |
| Logs | Incremento de errores HTTP 5xx |
| Riesgo estimado | Alto |
| Posible situación | Degradación progresiva del servicio |
| Acción sugerida | Revisar consumo de recursos, errores de aplicación y conexiones al servicio |
