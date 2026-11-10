from flask import Flask, render_template, request, send_file, abort
import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from io import BytesIO
import os

app = Flask(__name__)
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    try:
        id_factura = request.form['id_factura']
        response = requests.get(f'{BACKEND_URL}/facturas/v1/{id_factura}')
        
        if response.status_code != 200:
            abort(404, description="Factura no encontrada")
            
        factura = response.json()
        
        # Buffer en memoria y documento PDF en formato A4
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm
        )
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4B5563')
        )
        header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.whitesmoke,
            alignment=1
        )
        cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#1F2937')
        )
        
        # 1. Título y Número de Factura
        elements.append(Paragraph("FACTURA COMERCIAL", title_style))
        elements.append(Paragraph(f"<b>N°:</b> {factura['numero_factura']} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Fecha:</b> {factura['fecha_emision']}", subtitle_style))
        elements.append(Spacer(1, 10 * mm))
        
        # 2. Información de Empresa y Cliente en dos columnas
        empresa_info = f"""
        <b>EMISOR:</b><br/>
        <b>{factura['empresa']['nombre']}</b><br/>
        {factura['empresa']['direccion']}<br/>
        Tel: {factura['empresa']['telefono']}<br/>
        Email: {factura['empresa']['email']}
        """
        cliente_info = f"""
        <b>CLIENTE:</b><br/>
        <b>{factura['cliente']['nombre']}</b><br/>
        {factura['cliente']['direccion']}<br/>
        Tel: {factura['cliente']['telefono']}
        """
        
        info_data = [[
            Paragraph(empresa_info, cell_style),
            Paragraph(cliente_info, cell_style)
        ]]
        info_table = Table(info_data, colWidths=[90 * mm, 90 * mm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F3F4F6')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#EFF6FF')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#E5E7EB')),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#BFDBFE')),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 10 * mm))
        
        # 3. Detalle de la Factura (Tabla de productos/servicios)
        tabla_detalle = [[
            Paragraph("Cant.", header_style),
            Paragraph("Descripción", header_style),
            Paragraph("Precio Unitario", header_style),
            Paragraph("Total", header_style)
        ]]
        
        for item in factura['detalle']:
            tabla_detalle.append([
                Paragraph(str(item['cantidad']), cell_style),
                Paragraph(item['descripcion'], cell_style),
                Paragraph(f"${item['precio_unitario']:,.2f}", cell_style),
                Paragraph(f"${item['total']:,.2f}", cell_style)
            ])
            
        detalle_table = Table(tabla_detalle, colWidths=[20 * mm, 90 * mm, 35 * mm, 35 * mm])
        detalle_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(detalle_table)
        elements.append(Spacer(1, 6 * mm))
        
        # 4. Totales (Subtotal, Impuesto, Total final)
        totales_data = [
            [Paragraph("<b>Subtotal:</b>", cell_style), Paragraph(f"${factura['subtotal']:,.2f}", cell_style)],
            [Paragraph("<b>IVA (21%):</b>", cell_style), Paragraph(f"${factura['impuesto']:,.2f}", cell_style)],
            [Paragraph("<b>TOTAL:</b>", cell_style), Paragraph(f"<b>${factura['total']:,.2f}</b>", cell_style)],
        ]
        totales_table = Table(totales_data, colWidths=[40 * mm, 35 * mm], hAlign='RIGHT')
        totales_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('LINEABOVE', (0, 2), (1, 2), 1, colors.HexColor('#1E3A8A')),
        ]))
        elements.append(totales_table)
        
        # Generar el documento PDF y resetear el puntero del buffer
        doc.build(elements)
        buffer.seek(0)
        
        # Retornar el archivo PDF para previsualizar o descargar
        return send_file(
            buffer,
            as_attachment=False,
            mimetype='application/pdf',
            download_name=f"factura_{id_factura}.pdf"
        )
        
    except requests.exceptions.ConnectionError:
        abort(503, description="Error de conexión con el servidor")
    except Exception as e:
        abort(500, description=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)