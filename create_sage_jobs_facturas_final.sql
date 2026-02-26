-- Vista final vi_sage_jobs_facturas: Reconciliación Job vs Facturas
-- Muestra como las facturas individuales construyen los totales del job
-- Compatible con vi_sage_profit para validación cruzada

CREATE VIEW dbo.vi_sage_jobs_facturas AS
SELECT 
    -- Identificadores
    MAX(Company_Name) as company_name,
    Job_Id as job_reference,
    JrlH_Reference as invoice_reference,
    
    -- Clasificación de factura
    JrlH_module as invoice_module, -- R=Cliente, P=Proveedor
    CASE 
        WHEN JrlH_module = 'R' AND JrlH_Reference LIKE 'CRM%' THEN 'Nota de Crédito Cliente'
        WHEN JrlH_module = 'R' THEN 'Factura Cliente' 
        WHEN JrlH_module = 'P' THEN 'Factura Proveedor'
        ELSE 'Otro'
    END as invoice_type,
    
    -- Entidades involucradas
    MAX(Cust_Customer_bill_name) as customer_name,
    MAX(Vend_Name) as vendor_name,
    
    -- Totales financieros (usando lógica comprobada de vi_sage_profit)
    SUM(CAST(Ingresos as DECIMAL(12,2))) as ingresos_factura,
    SUM(CAST(Gastos as DECIMAL(12,2))) as gastos_factura, 
    SUM(CAST(Ganancia as DECIMAL(12,2))) as ganancia_factura,
    
    -- Información de auditoría
    COUNT(*) as detail_lines_count,
    COUNT(DISTINCT Chrt_Accounttype) as account_types_used,
    MIN(jrlH_TransactionDate) as earliest_transaction_date,
    MAX(jrlH_TransactionDate) as latest_transaction_date,
    
    -- Campos de referencia cruzada con vi_sage_profit
    MAX(Job_StartDate) as job_start_date,
    MAX(Job_Description) as job_description

FROM vi_sage_journal
WHERE JrlH_Reference IS NOT NULL 
  AND Job_Id IS NOT NULL
  -- Filtrar solo transacciones con impacto financiero
  AND (Ingresos != 0 OR Gastos != 0)
  
GROUP BY Job_Id, JrlH_Reference, JrlH_module;