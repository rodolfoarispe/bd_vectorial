-- =====================================================
-- Vista: vi_sage_job_agregado
-- Propósito: Resumen agregado de facturas por job del sistema Sage/Peachtree
-- Fecha: 2026-02-24
-- Descripción: Agrupa todas las facturas por job/proyecto con totales de
--              ingresos, gastos, utilidad y conteos por estado de pago
-- =====================================================

-- Eliminar vista si existe
IF OBJECT_ID('dbo.vi_sage_job_agregado', 'V') IS NOT NULL
    DROP VIEW dbo.vi_sage_job_agregado;
GO

-- Crear vista
CREATE VIEW dbo.vi_sage_job_agregado AS
SELECT 
    -- Información del job
    j.jobid,
    j.jobdescription,
    j.startdate AS job_startdate,
    j.enddate AS job_enddate,
    j.supervisor AS job_supervisor,
    j.customerrecordnumber AS job_cliente_id,
    
    -- Agregados financieros
    SUM(CASE WHEN h.module = 'R' THEN h.mainamount ELSE 0 END) AS total_ingresos,
    SUM(CASE WHEN h.module = 'P' THEN ABS(h.mainamount) ELSE 0 END) AS total_gastos,
    SUM(CASE WHEN h.module = 'R' THEN h.mainamount ELSE 0 END) - 
    SUM(CASE WHEN h.module = 'P' THEN ABS(h.mainamount) ELSE 0 END) AS utilidad_bruta,
    
    -- Conteos de facturas por tipo
    COUNT(DISTINCT CASE WHEN h.module = 'R' THEN h.id END) AS num_facturas_emitidas,
    COUNT(DISTINCT CASE WHEN h.module = 'P' THEN h.id END) AS num_facturas_recibidas,
    COUNT(DISTINCT h.id) AS total_facturas,
    
    -- Estado de pago - Facturas emitidas (Receivables)
    COUNT(DISTINCT CASE 
        WHEN h.module = 'R' AND (TRY_CAST(h.totalinvoicepaid AS float) > 0 OR ABS(h.amountpaid) >= ABS(h.mainamount)) 
        THEN h.id END) AS facturas_cobradas,
    COUNT(DISTINCT CASE 
        WHEN h.module = 'R' AND h.amountpaid = 0 AND (h.totalinvoicepaid IS NULL OR TRY_CAST(h.totalinvoicepaid AS float) = 0) 
        THEN h.id END) AS facturas_pendientes_cobro,
    COUNT(DISTINCT CASE 
        WHEN h.module = 'R' AND h.amountpaid > 0 AND ABS(h.amountpaid) < ABS(h.mainamount) AND (h.totalinvoicepaid IS NULL OR TRY_CAST(h.totalinvoicepaid AS float) = 0)
        THEN h.id END) AS facturas_cobro_parcial,
    
    -- Estado de pago - Facturas recibidas (Payables)
    COUNT(DISTINCT CASE 
        WHEN h.module = 'P' AND (TRY_CAST(h.totalinvoicepaid AS float) > 0 OR ABS(h.amountpaid) >= ABS(h.mainamount)) 
        THEN h.id END) AS facturas_pagadas,
    COUNT(DISTINCT CASE 
        WHEN h.module = 'P' AND h.amountpaid = 0 AND (h.totalinvoicepaid IS NULL OR TRY_CAST(h.totalinvoicepaid AS float) = 0) 
        THEN h.id END) AS facturas_pendientes_pago,
    COUNT(DISTINCT CASE 
        WHEN h.module = 'P' AND h.amountpaid > 0 AND ABS(h.amountpaid) < ABS(h.mainamount) AND (h.totalinvoicepaid IS NULL OR TRY_CAST(h.totalinvoicepaid AS float) = 0)
        THEN h.id END) AS facturas_pago_parcial,
    
    -- Montos por estado de pago
    SUM(CASE 
        WHEN h.module = 'R' AND (TRY_CAST(h.totalinvoicepaid AS float) > 0 OR ABS(h.amountpaid) >= ABS(h.mainamount)) 
        THEN h.mainamount ELSE 0 END) AS ingresos_cobrados,
    SUM(CASE 
        WHEN h.module = 'R' AND h.amountpaid = 0 AND (h.totalinvoicepaid IS NULL OR TRY_CAST(h.totalinvoicepaid AS float) = 0) 
        THEN h.mainamount ELSE 0 END) AS ingresos_por_cobrar,
    SUM(CASE 
        WHEN h.module = 'P' AND (TRY_CAST(h.totalinvoicepaid AS float) > 0 OR ABS(h.amountpaid) >= ABS(h.mainamount)) 
        THEN ABS(h.mainamount) ELSE 0 END) AS gastos_pagados,
    SUM(CASE 
        WHEN h.module = 'P' AND h.amountpaid = 0 AND (h.totalinvoicepaid IS NULL OR TRY_CAST(h.totalinvoicepaid AS float) = 0) 
        THEN ABS(h.mainamount) ELSE 0 END) AS gastos_por_pagar,
    
    -- Fechas de transacciones
    MIN(h.transactiondate) AS fecha_primera_factura,
    MAX(h.transactiondate) AS fecha_ultima_factura,
    
    -- Métricas calculadas
    CASE 
        WHEN SUM(CASE WHEN h.module = 'R' THEN h.mainamount ELSE 0 END) > 0 
        THEN ROUND(
            (SUM(CASE WHEN h.module = 'R' THEN h.mainamount ELSE 0 END) - 
             SUM(CASE WHEN h.module = 'P' THEN ABS(h.mainamount) ELSE 0 END)) * 100.0 / 
             SUM(CASE WHEN h.module = 'R' THEN h.mainamount ELSE 0 END), 2)
        ELSE 0 
    END AS margen_utilidad_porcentaje,
    
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN h.module = 'R' THEN h.id END) > 0
        THEN ROUND(
            COUNT(DISTINCT CASE WHEN h.module = 'R' AND (TRY_CAST(h.totalinvoicepaid AS float) > 0 OR ABS(h.amountpaid) >= ABS(h.mainamount)) THEN h.id END) * 100.0 / 
            COUNT(DISTINCT CASE WHEN h.module = 'R' THEN h.id END), 2)
        ELSE 0 
    END AS porcentaje_cobrado,
    
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN h.module = 'P' THEN h.id END) > 0
        THEN ROUND(
            COUNT(DISTINCT CASE WHEN h.module = 'P' AND (TRY_CAST(h.totalinvoicepaid AS float) > 0 OR ABS(h.amountpaid) >= ABS(h.mainamount)) THEN h.id END) * 100.0 / 
            COUNT(DISTINCT CASE WHEN h.module = 'P' THEN h.id END), 2)
        ELSE 0 
    END AS porcentaje_pagado,
    
    -- Campos de auditoría
    GETDATE() AS fecha_calculo
    
FROM dbo.temp_sage_journal_header h
JOIN dbo.temp_sage_journal_row r
    ON h.jrnlkey_journal = r.journal 
   AND h.postorder = r.postorder
LEFT JOIN dbo.temp_sage_jobs j
    ON CAST(r.jobrecordnumber AS varchar(50)) = j.jobrecordnumber
WHERE r.jobrecordnumber IS NOT NULL 
  AND r.jobrecordnumber <> 0
  AND h.mainamount <> 0
GROUP BY 
    j.jobid,
    j.jobdescription,
    j.startdate,
    j.enddate,
    j.supervisor,
    j.customerrecordnumber;
GO

-- Comentarios de la vista
EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Vista agregada que resume por job/proyecto todos los ingresos, gastos, estados de pago y métricas financieras del sistema Sage/Peachtree',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'VIEW', @level1name = N'vi_sage_job_agregado';
GO

-- =====================================================
-- Ejemplos de uso de la vista
-- =====================================================

/*
-- 1. Top 10 jobs más rentables
SELECT TOP 10
    jobid,
    jobdescription,
    total_ingresos,
    total_gastos,
    utilidad_bruta,
    margen_utilidad_porcentaje
FROM dbo.vi_sage_job_agregado 
WHERE total_ingresos > 0
ORDER BY utilidad_bruta DESC;

-- 2. Jobs con problemas de cobranza
SELECT 
    jobid,
    jobdescription,
    total_ingresos,
    ingresos_por_cobrar,
    facturas_pendientes_cobro,
    porcentaje_cobrado,
    fecha_ultima_factura
FROM dbo.vi_sage_job_agregado 
WHERE facturas_pendientes_cobro > 0 
  AND porcentaje_cobrado < 80
ORDER BY ingresos_por_cobrar DESC;

-- 3. Resumen ejecutivo de todos los jobs activos
SELECT 
    COUNT(*) AS total_jobs,
    SUM(total_ingresos) AS ingresos_totales,
    SUM(total_gastos) AS gastos_totales,
    SUM(utilidad_bruta) AS utilidad_total,
    SUM(facturas_pendientes_cobro) AS total_pendientes_cobro,
    SUM(facturas_pendientes_pago) AS total_pendientes_pago,
    AVG(margen_utilidad_porcentaje) AS margen_promedio
FROM dbo.vi_sage_job_agregado 
WHERE total_ingresos > 0;

-- 4. Jobs por rango de ingresos
SELECT 
    CASE 
        WHEN total_ingresos = 0 THEN '0 - Sin Ingresos'
        WHEN total_ingresos <= 1000 THEN '1 - Hasta $1,000'
        WHEN total_ingresos <= 5000 THEN '2 - $1,001 - $5,000'
        WHEN total_ingresos <= 10000 THEN '3 - $5,001 - $10,000'
        WHEN total_ingresos <= 50000 THEN '4 - $10,001 - $50,000'
        ELSE '5 - Más de $50,000'
    END AS rango_ingresos,
    COUNT(*) AS cantidad_jobs,
    SUM(total_ingresos) AS suma_ingresos,
    AVG(margen_utilidad_porcentaje) AS margen_promedio
FROM dbo.vi_sage_job_agregado
GROUP BY 
    CASE 
        WHEN total_ingresos = 0 THEN '0 - Sin Ingresos'
        WHEN total_ingresos <= 1000 THEN '1 - Hasta $1,000'
        WHEN total_ingresos <= 5000 THEN '2 - $1,001 - $5,000'
        WHEN total_ingresos <= 10000 THEN '3 - $5,001 - $10,000'
        WHEN total_ingresos <= 50000 THEN '4 - $10,001 - $50,000'
        ELSE '5 - Más de $50,000'
    END
ORDER BY rango_ingresos;

-- 5. Jobs con actividad reciente (últimos 30 días)
SELECT 
    jobid,
    jobdescription,
    total_ingresos,
    total_gastos,
    utilidad_bruta,
    total_facturas,
    fecha_ultima_factura,
    DATEDIFF(day, fecha_ultima_factura, GETDATE()) AS dias_ultima_actividad
FROM dbo.vi_sage_job_agregado 
WHERE fecha_ultima_factura >= DATEADD(day, -30, GETDATE())
ORDER BY fecha_ultima_factura DESC;

-- 6. Análisis de eficiencia de cobranza
SELECT 
    jobid,
    jobdescription,
    num_facturas_emitidas,
    facturas_cobradas,
    facturas_pendientes_cobro,
    porcentaje_cobrado,
    ingresos_cobrados,
    ingresos_por_cobrar,
    CASE 
        WHEN porcentaje_cobrado >= 90 THEN 'EXCELENTE'
        WHEN porcentaje_cobrado >= 70 THEN 'BUENO'
        WHEN porcentaje_cobrado >= 50 THEN 'REGULAR'
        ELSE 'DEFICIENTE'
    END AS calificacion_cobranza
FROM dbo.vi_sage_job_agregado 
WHERE num_facturas_emitidas > 0
ORDER BY porcentaje_cobrado DESC;
*/