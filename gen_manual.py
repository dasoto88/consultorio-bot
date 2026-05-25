from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_CENTER

doc = SimpleDocTemplate("manual_medpanel.pdf", pagesize=letter,
                        leftMargin=0.8*inch, rightMargin=0.8*inch,
                        topMargin=0.8*inch, bottomMargin=0.8*inch)

styles = getSampleStyleSheet()
PURPLE = colors.HexColor("#6C63FF")
DARK   = colors.HexColor("#1a1a2e")
GRAY   = colors.HexColor("#555555")

title_style = ParagraphStyle("titulo", parent=styles["Title"],   fontSize=26, textColor=PURPLE, spaceAfter=6,  alignment=TA_CENTER)
sub_style   = ParagraphStyle("sub",    parent=styles["Normal"],  fontSize=13, textColor=GRAY,   spaceAfter=20, alignment=TA_CENTER)
h1_style    = ParagraphStyle("h1",     parent=styles["Heading1"],fontSize=15, textColor=PURPLE, spaceBefore=16,spaceAfter=6)
h2_style    = ParagraphStyle("h2",     parent=styles["Heading2"],fontSize=12, textColor=DARK,   spaceBefore=10,spaceAfter=4)
body_style  = ParagraphStyle("body",   parent=styles["Normal"],  fontSize=10, leading=16, spaceAfter=6, textColor=colors.HexColor("#222222"))
note_style  = ParagraphStyle("note",   parent=styles["Normal"],  fontSize=9,  leading=14, textColor=GRAY, leftIndent=14)
foot_style  = ParagraphStyle("foot",   parent=styles["Normal"],  fontSize=8,  textColor=GRAY, alignment=TA_CENTER)

def H1(t): return Paragraph(t, h1_style)
def H2(t): return Paragraph(t, h2_style)
def P(t):  return Paragraph(t, body_style)
def N(t):  return Paragraph("&#x2022; " + t, note_style)
def SP(n=8): return Spacer(1, n)
def HR(): return HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0"), spaceAfter=8)

story = []

# PORTADA
story += [SP(30),
    Paragraph("MedPanel Pro", title_style),
    Paragraph("Manual de Usuario - Guia Completa", sub_style),
    HR(),
    P("Bienvenido a <b>MedPanel Pro</b>, la plataforma de gestion medica disenada para consultorios modernos. "
      "Este manual te guia paso a paso por todas las funciones del sistema."),
    SP(6),
    P("<b>Soporte:</b> dasoto88122911@gmail.com  |  <b>WhatsApp:</b> 633 112 4596"),
    PageBreak()]

# 1. PRIMEROS PASOS
story += [H1("1. Primeros Pasos"), HR(),
    H2("1.1 Iniciar Sesion"),
    P("Entra a <b>https://consultorio-bot.streamlit.app</b> y selecciona la pestania "
      "<b>Iniciar Sesion</b>. Ingresa tu <b>usuario</b> y <b>contrasenia</b> provisionales "
      "que recibiste por correo y presiona <i>Entrar al Panel</i>."),
    H2("1.2 Cambiar tu Contrasenia (Obligatorio al primer ingreso)"),
    P("Por seguridad cambia tu contrasenia al primer ingreso:"),
    N("Ve a la pestania <b>Salir</b> (ultima del menu)."),
    N("Completa: contrasenia actual, nueva contrasenia, confirmar nueva contrasenia."),
    N("Presiona <b>Actualizar Contrasenia</b>."),
    SP(4),
    P("<b>Importante:</b> Si olvidas tu contrasenia usa <i>Recuperar Contrasenia</i> "
      "en la pantalla inicial. El sistema te enviara una nueva al correo registrado."),
    PageBreak()]

# 2. AGENDA
story += [H1("2. Agenda de Citas"), HR(),
    H2("2.1 Ver Citas del Dia"),
    P("La pestania <b>Agenda</b> muestra todas tus citas programadas. "
      "Filtra por fecha con el selector de calendario en la parte superior."),
    H2("2.2 Agendar Nueva Cita"),
    N("Selecciona la fecha y hora deseada."),
    N("Busca al paciente existente o agrega uno nuevo."),
    N("Indica el motivo de consulta."),
    N("Presiona <b>Guardar Cita</b>."),
    H2("2.3 Cancelar o Reprogramar"),
    P("Haz clic sobre la cita, edita la hora o selecciona <b>Cancelar</b>. "
      "El sistema guarda el historial de cambios."),
    PageBreak()]

# 3. PACIENTES
story += [H1("3. Gestion de Pacientes"), HR(),
    H2("3.1 Agregar Paciente Nuevo"),
    P("En <b>Pacientes</b> presiona <b>+ Nuevo Paciente</b> y completa:"),
    N("Nombre completo, fecha de nacimiento, sexo."),
    N("Telefono y correo electronico."),
    N("Alergias conocidas y notas medicas iniciales."),
    H2("3.2 Buscar Paciente"),
    P("El buscador en la parte superior acepta nombre, telefono o correo electronico."),
    H2("3.3 Historial Clinico"),
    P("Al seleccionar un paciente visualizas todas sus consultas, recetas y cobros "
      "en orden cronologico inverso (mas reciente primero)."),
    PageBreak()]

# 4. CONSULTAS
story += [H1("4. Consultas Medicas"), HR(),
    H2("4.1 Registrar Consulta"),
    N("Ve a la pestania <b>Consultas</b>."),
    N("Selecciona al paciente y la fecha de atencion."),
    N("Completa: motivo, exploracion fisica, diagnostico y tratamiento."),
    N("Presiona <b>Guardar Consulta</b>."),
    H2("4.2 Diagnostico y Notas de Evolucion"),
    P("Puedes registrar multiples diagnosticos y notas de seguimiento. "
      "Todos quedan en el expediente permanente del paciente."),
    PageBreak()]

# 5. RECETAS
story += [H1("5. Recetas Digitales"), HR(),
    H2("5.1 Emitir Receta"),
    P("En <b>Recetas</b> selecciona al paciente y agrega los medicamentos:"),
    N("Nombre del medicamento y presentacion."),
    N("Dosis y frecuencia (cada cuantas horas)."),
    N("Duracion del tratamiento e indicaciones especiales."),
    H2("5.2 Descargar e Imprimir"),
    P("Al guardar puedes descargar la receta en <b>PDF</b> con tu nombre y cedula "
      "para imprimirla o enviarla por WhatsApp al paciente."),
    PageBreak()]

# 6. COBROS
story += [H1("6. Cobros y Finanzas"), HR(),
    H2("6.1 Registrar Cobro"),
    N("Ve a <b>Cobros</b>."),
    N("Selecciona al paciente y el concepto (consulta, procedimiento, etc.)."),
    N("Indica el monto y metodo de pago: efectivo, transferencia o tarjeta."),
    N("Presiona <b>Registrar Cobro</b>."),
    H2("6.2 Reporte de Ingresos"),
    P("El sistema genera un resumen mensual de ingresos. "
      "Exporta a <b>Excel</b> con el boton Descargar Reporte para tu contabilidad."),
    PageBreak()]

# 7. INVENTARIO
story += [H1("7. Inventario"), HR(),
    P("Controla medicamentos y consumibles del consultorio desde la pestania <b>Inventario</b>:"),
    N("Agrega productos con nombre, cantidad actual y cantidad minima de alerta."),
    N("El sistema te avisa automaticamente cuando un producto esta por agotarse."),
    N("Registra entradas (compras) y salidas (uso en consultas)."),
    PageBreak()]

# 8. CALCULADORAS
story += [H1("8. Calculadoras Medicas"), HR(),
    P("La pestania <b>Calculadoras</b> incluye herramientas clinicas de uso frecuente:"),
    N("Calculo de IMC (Indice de Masa Corporal)."),
    N("Superficie corporal."),
    N("Dosis pediatricas por peso."),
    N("Fechas obstetricas (FUM, FPP)."),
    PageBreak()]

# 9. ESTADISTICAS
story += [H1("9. Estadisticas y Reportes"), HR(),
    P("En <b>Estadisticas</b> encontraras graficas interactivas de:"),
    N("Citas por mes y dia de la semana."),
    N("Ingresos mensuales acumulados."),
    N("Pacientes nuevos vs recurrentes."),
    N("Diagnosticos mas frecuentes."),
    SP(6),
    P("Todos los reportes pueden exportarse a <b>Excel</b>."),
    PageBreak()]

# 10. SECRETARIA
story += [H1("10. Mi Secretaria"), HR(),
    P("Disponible en planes <b>Profesional</b> y <b>Clinica</b>."),
    H2("10.1 Crear Cuenta de Secretaria"),
    N("Ve a la pestania <b>Mi Secretaria</b>."),
    N("Ingresa nombre y correo de tu secretaria."),
    N("El sistema genera credenciales y se las envia por correo automaticamente."),
    H2("10.2 Permisos"),
    P("La secretaria puede agendar citas y gestionar pacientes. "
      "<b>No tiene acceso</b> a finanzas, recetas ni reportes medicos."),
    PageBreak()]

# 11. SOPORTE
story += [H1("11. Soporte y Contacto"), HR(),
    P("Nuestro equipo esta listo para ayudarte:"),
    SP(10)]

data = [
    ["Canal",     "Contacto",                     "Disponibilidad"],
    ["WhatsApp",  "633 112 4596",                 "Lun-Vie 9am-7pm"],
    ["Correo",    "dasoto88122911@gmail.com",      "Respuesta en 24h"],
    ["App",       "consultorio-bot.streamlit.app","24/7"],
]
tbl = Table(data, colWidths=[1.4*inch, 3.2*inch, 2*inch])
tbl.setStyle(TableStyle([
    ("BACKGROUND",     (0,0), (-1,0), PURPLE),
    ("TEXTCOLOR",      (0,0), (-1,0), colors.white),
    ("FONTNAME",       (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",       (0,0), (-1,-1), 9),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f5f5ff"), colors.white]),
    ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
    ("ALIGN",          (0,0), (-1,-1), "LEFT"),
    ("TOPPADDING",     (0,0), (-1,-1), 6),
    ("BOTTOMPADDING",  (0,0), (-1,-1), 6),
    ("LEFTPADDING",    (0,0), (-1,-1), 8),
]))
story.append(tbl)
story += [SP(20), HR(),
    Paragraph("© 2026 MedPanel Pro — Todos los derechos reservados", foot_style)]

doc.build(story)
print("PDF generado OK")
