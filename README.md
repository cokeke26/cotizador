# 📄 Cotizador PDF – HIDRACODE

Aplicación web para **generar cotizaciones profesionales en PDF**, con **numeración autoincremental**, **persistencia en PostgreSQL (Supabase)** y **despliegue en Streamlit Cloud**.

Pensado para uso interno de agencias y equipos de trabajo.

---

## 🚀 Características principales

- 🔐 **Acceso privado** mediante contraseña
- 🧾 **Generación de cotizaciones en PDF**
- 🔢 **Número de cotización autoincremental** (por año)
- 🗄️ **Persistencia en PostgreSQL (Supabase)**
- 📎 **Ítems dinámicos** (cantidad, precio, totales)
- 💰 **Cálculo automático de totales**
- ☁️ **Deploy en Streamlit Cloud**
- 🧠 Backend moderno con 'psycopg' v3 (compatible con Python 3.13)

---

## 🛠️ Tecnologías utilizadas

- **Python**
- **Streamlit** (UI)
- **ReportLab** (PDF)
- **PostgreSQL** (Supabase)
- **psycopg v3** (driver DB)
- **GitHub + Streamlit Cloud**

---

## ⚙️ Requisitos

- Python **3.12+** (local)
- Cuenta en **Supabase**
- Cuenta en **Streamlit Cloud** (opcional, para deploy)

---

## 🔐 Configuración de variables sensibles

### Archivo local '.streamlit/secrets.toml'

> ⚠️ **Nunca subir este archivo al repositorio**

```toml
APP_PASSWORD = "tu_password_de_acceso"
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:PUERTO/DB?sslmode=require"

APP_PASSWORD: contraseña para acceder a la app
DATABASE_URL: Database password de Supabase (no la de login)

🗄️ Base de datos (Supabase)

Tablas requeridas:

-quotes

-quote_items

-quote_counters

El sistema usa una tabla quote_counters para generar el número de cotización de forma automática y segura.

▶️ Ejecución en local

1️⃣ Crear y activar entorno virtual

python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Linux / macOS

2️⃣ Instalar dependencias

pip install -r requirements.txt

3️⃣ Ejecutar la aplicación

python -m streamlit run app.py

☁️ Deploy en Streamlit Cloud

1.Subir el proyecto a GitHub

2.Crear app en Streamlit Cloud

3.Configurar en Settings → Secrets:
APP_PASSWORD = "..."
DATABASE_URL = "..."

4.Asegurarse de tener runtime.txt en la raíz:
python-3.12.8

🔒 Seguridad

- .streamlit/secrets.toml está en .gitignore

- No se almacenan credenciales en el código

- Conexión a DB siempre con SSL

📌 Roadmap / Mejoras futuras

📊 Historial de cotizaciones

🔁 Reimpresión de PDF

✏️ Edición / duplicado de cotizaciones

📤 Exportación a Excel

👥 Roles de usuario

🎨 Personalización visual por cliente

👨‍💻 Autor
HIDRACODE SOLUTIONS
Diseño + Tecnología para pymes

📄 Licencia
Proyecto de uso interno.
Todos los derechos reservados.


