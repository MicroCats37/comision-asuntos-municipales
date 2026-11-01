/**
 * rhPdfPage — Configuración de impresión de los PDFs de RH mensual.
 *
 * A4 VERTICAL: el documento se imprime como los originales (el de Delegado
 * cabe en vertical porque su tabla es compacta). El contenido es responsive:
 * la tabla usa `width: 100%` con columnas en porcentaje, así que se ajusta al
 * ancho de la hoja sin cortarse.
 */
export const RH_PDF_PAGE_CSS = `
@page { size: A4 portrait; margin: 10mm; }
html, body { margin: 0 !important; padding: 0 !important; background: #ffffff !important; }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
table { page-break-inside: auto; }
tr { page-break-inside: avoid; page-break-after: auto; }
thead { display: table-header-group; }
`;
