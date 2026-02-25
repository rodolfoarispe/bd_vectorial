-- =====================================================
-- Vista: vi_sage_jobs_facturas
-- Propósito: Análisis de facturas por job del sistema Sage/Peachtree
-- Fecha: 2026-02-24
-- Descripción: Extrae facturas con estado de pago, clasificadas por 
--              ingresos/gastos y asociadas a jobs/proyectos
-- =====================================================

-- Eliminar vista si existe
IF OBJECT_ID('dbo.vi_sage_jobs_facturas', 'V') IS NOT NULL
    DROP VIEW dbo.vi_sage_jobs_facturas;
GO

-- Crear vista
CREATE VIEW dbo.vi_sage_jobs_facturas AS
SELECT 
    -- Información del job
    j.jobid,
    j.jobdescription,
    j.startdate AS job_startdate,
    j.enddate AS job_enddate,
    j.supervisor AS job_supervisor,
    
    -- Información de la factura
    COALESCE(h.reference, h.customerinvoiceno, r.invnumforthistrx, 'SIN_FACTURA') AS factura,
    h.transactiondate AS fecha_factura,
    h.module AS tipo_modulo,
    CASE 
        WHEN h.module = 'R' THEN 'RECEIVABLES (Factura a Cliente)'
        WHEN h.module = 'P' THEN 'PAYABLES (Factura de Proveedor)'
        ELSE 'OTRO'
    END AS descripcion_modulo,
    
    -- Montos
    h.mainamount AS monto_factura,
    h.amountpaid AS monto_pagado_parcial,
    h.totalinvoicepaid AS indicador_pago_total,
    
    -- Estado de pago calculado
    CASE 
        WHEN TRY_CAST(h.totalinvoicepaid AS float) > 0 THEN 'PAGADA'
        WHEN h.amountpaid = 0 THEN 'PENDIENTE'
        WHEN ABS(h.amountpaid) >= ABS(h.mainamount) THEN 'PAGADA'
        ELSE 'PARCIAL'
    END AS estado_pago,
    
    -- Clasificación ingresos vs gastos
    CASE 
        WHEN h.module = 'R' THEN h.mainamount 
        ELSE 0 
    END AS ingresos,
    CASE 
        WHEN h.module = 'P' THEN ABS(h.mainamount) 
        ELSE 0 
    END AS gastos,
    
    -- Información adicional de la transacción
    h.description AS descripcion_transaccion,
    h.custvendid AS cliente_proveedor_id,
    h.jrnlkey_trxnumber AS numero_transaccion,
    h.jrnlkey_journal AS journal_id,
    h.postorder AS post_order,
    
    -- Información de las líneas
    r.rowdescription AS descripcion_linea,
    r.amount AS monto_linea,
    r.glacntnumber AS cuenta_contable,
    r.itemrecordnumber,
    r.jobrecordnumber,
    
    -- Campos de auditoría
    h.id AS header_id,
    r.id AS row_id,
    GETDATE() AS fecha_consulta
    
FROM dbo.temp_sage_journal_header h
JOIN dbo.temp_sage_journal_row r
    ON h.jrnlkey_journal = r.journal 
   AND h.postorder = r.postorder
LEFT JOIN dbo.temp_sage_jobs j
    ON CAST(r.jobrecordnumber AS varchar(50)) = j.jobrecordnumber
WHERE r.jobrecordnumber IS NOT NULL 
  AND r.jobrecordnumber <> 0
  AND h.mainamount <> 0;
GO

-- Comentarios de la vista
EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Vista que combina facturas del sistema Sage/Peachtree con información de jobs/proyectos, incluyendo estado de pago y clasificación de ingresos/gastos',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'VIEW', @level1name = N'vi_sage_jobs_facturas';
GO

-- =====================================================
-- Ejemplos de uso de la vista
-- =====================================================

/*
-- 1. Facturas de un mes específico
SELECT * 
FROM dbo.vi_sage_jobs_facturas 
WHERE fecha_factura >= '2026-12-01' 
  AND fecha_factura < '2027-01-01'
ORDER BY jobid, fecha_factura DESC;

-- 2. Resumen por job (agregado)
SELECT 
    jobid,
    jobdescription,
    SUM(ingresos) AS total_ingresos,
    SUM(gastos) AS total_gastos,
    SUM(ingresos) - SUM(gastos) AS utilidad_bruta,
    COUNT(*) AS total_facturas,
    COUNT(CASE WHEN estado_pago = 'PAGADA' THEN 1 END) AS facturas_pagadas,
    COUNT(CASE WHEN estado_pago = 'PENDIENTE' THEN 1 END) AS facturas_pendientes,
    COUNT(CASE WHEN estado_pago = 'PARCIAL' THEN 1 END) AS facturas_parciales
FROM dbo.vi_sage_jobs_facturas 
WHERE fecha_factura >= '2026-12-01' 
  AND fecha_factura < '2027-01-01'
GROUP BY jobid, jobdescription
ORDER BY total_ingresos DESC;

-- 3. Facturas pendientes de pago/cobro
SELECT 
    jobid,
    jobdescription,
    factura,
    fecha_factura,
    descripcion_modulo,
    monto_factura,
    estado_pago
FROM dbo.vi_sage_jobs_facturas 
WHERE estado_pago IN ('PENDIENTE', 'PARCIAL')
  AND fecha_factura >= '2026-01-01'
ORDER BY fecha_factura DESC;

-- 4. Top jobs por ingresos
SELECT TOP 10
    jobid,
    jobdescription,
    SUM(ingresos) AS total_ingresos,
    COUNT(CASE WHEN tipo_modulo = 'R' THEN 1 END) AS num_facturas_emitidas
FROM dbo.vi_sage_jobs_facturas 
WHERE fecha_factura >= '2026-01-01'
GROUP BY jobid, jobdescription
HAVING SUM(ingresos) > 0
ORDER BY total_ingresos DESC;

-- 5. Análisis de flujo de efectivo por mes
SELECT 
    YEAR(fecha_factura) AS anio,
    MONTH(fecha_factura) AS mes,
    SUM(CASE WHEN estado_pago = 'PAGADA' AND tipo_modulo = 'R' THEN ingresos ELSE 0 END) AS ingresos_cobrados,
    SUM(CASE WHEN estado_pago = 'PAGADA' AND tipo_modulo = 'P' THEN gastos ELSE 0 END) AS gastos_pagados,
    SUM(CASE WHEN estado_pago = 'PENDIENTE' AND tipo_modulo = 'R' THEN ingresos ELSE 0 END) AS ingresos_por_cobrar,
    SUM(CASE WHEN estado_pago = 'PENDIENTE' AND tipo_modulo = 'P' THEN gastos ELSE 0 END) AS gastos_por_pagar
FROM dbo.vi_sage_jobs_facturas 
WHERE fecha_factura >= '2026-01-01'
GROUP BY YEAR(fecha_factura), MONTH(fecha_factura)
ORDER BY anio, mes;
*/