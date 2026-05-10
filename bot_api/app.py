from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="ConsultorioBot API")

@app.get("/", response_class=HTMLResponse)
def landing_doctores():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ConsultorioBot | Asistente Virtual para Médicos</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 900px;
                width: 100%;
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #0d47a1 0%, #1976d2 100%);
                color: white;
                padding: 60px 40px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
                font-weight: 700;
            }
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            .status-badge {
                display: inline-block;
                background: #4caf50;
                padding: 8px 20px;
                border-radius: 50px;
                margin-top: 20px;
                font-weight: 600;
            }
            .content {
                padding: 50px 40px;
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 30px;
                margin-bottom: 40px;
            }
            .feature {
                text-align: center;
                padding: 30px 20px;
                border-radius: 12px;
                background: #f8f9fa;
                transition: transform 0.3s;
            }
            .feature:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .feature-icon {
                font-size: 3rem;
                margin-bottom: 15px;
            }
            .feature h3 {
                color: #0d47a1;
                margin-bottom: 10px;
                font-size: 1.3rem;
            }
            .feature p {
                color: #666;
                line-height: 1.6;
            }
            .cta {
                text-align: center;
                padding: 30px;
                background: #f8f9fa;
                border-radius: 12px;
            }
            .cta h2 {
                color: #0d47a1;
                margin-bottom: 15px;
            }
            .btn {
                display: inline-block;
                background: #1976d2;
                color: white;
                padding: 15px 40px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: 600;
                margin-top: 15px;
                transition: background 0.3s;
            }
            .btn:hover {
                background: #0d47a1;
            }
            .footer {
                text-align: center;
                padding: 20px;
                color: #999;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>ConsultorioBot</h1>
                <p>Asistente Virtual Inteligente para Consultorios Médicos</p>
                <div class="status-badge">● Sistema Activo</div>
            </div>
            <div class="content">
                <div class="features">
                    <div class="feature">
                        <div class="feature-icon">📅</div>
                        <h3>Agenda Automática</h3>
                        <p>Gestiona citas por WhatsApp 24/7. Tus pacientes agendan solos, sin llamadas.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">💬</div>
                        <h3>Respuestas Instantáneas</h3>
                        <p>Resuelve dudas frecuentes sobre horarios, ubicación y precios al instante.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🔔</div>
                        <h3>Recordatorios</h3>
                        <p>Reduce inasistencias con confirmaciones automáticas por WhatsApp.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">📊</div>
                        <h3>Expedientes Digitales</h3>
                        <p>Registra consultas y mantén historial de pacientes en un solo lugar.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🔒</div>
                        <h3>Datos Seguros</h3>
                        <p>Cumplimiento con normativas de privacidad. Información encriptada.</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">⚡</div>
                        <h3>Setup en 5 Minutos</h3>
                        <p>Sin instalaciones. Conecta tu WhatsApp y empieza a recibir citas hoy.</p>
                    </div>
                </div>
                <div class="cta">
                    <h2>¿Listo para modernizar tu consultorio?</h2>
                    <p>Únete a más de 200 médicos que ya automatizaron su agenda</p>
                    <a href="https://wa.me/526531234567?text=Hola,%20quiero%20info%20de%20ConsultorioBot" class="btn">Solicitar Demo por WhatsApp</a>
                </div>
            </div>
            <div class="footer">
                © 2026 ConsultorioBot. Tecnología para profesionales de la salud.
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "service": "consultorio-bot"}
