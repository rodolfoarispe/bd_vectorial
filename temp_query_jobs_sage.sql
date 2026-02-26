-- Consulta: Jobs y Facturas Sage - Enero 2026 (Primeros 100)
SELECT TOP 100
    jobid,
    jobdescription,
    factura,
    fecha_factura,
    descripcion_modulo,
    monto_factura,
    estado_pago,
    ingresos,
    gastos,
    cliente_proveedor_id,
    descripcion_transaccion
FROM dbo.vi_sage_jobs_facturas 
WHERE fecha_factura >= '2026-01-01' 
  AND fecha_factura < '2026-02-01'
ORDER BY fecha_factura DESC, jobid;