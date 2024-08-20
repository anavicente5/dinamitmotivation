import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import re
import urllib3

# Desactivar advertencias de SSL inseguro
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="💥 Optimización Dinamita", page_icon="💥", layout="wide")

st.title("💥 Optimización Dinamita")

# Campos de entrada
api_key = st.text_input("🔑 API Key de OpenAI")
url_optimizar = st.text_input("🔗 URL para optimizar")
keyword_principal = st.text_input("🎯 Keyword principal del artículo")
keyword_secundaria = st.text_input("🏹 Keyword 2ª principal del artículo")
keywords_adicionales = st.text_input("🔤 Keywords secundarias (separadas por comas)")
competencia_urls = [
    st.text_input(f"🏆 URL de la competencia #{i+1}") for i in range(5)
]
url_tono_marca = st.text_input("🎨 URL con el tono de la marca")

# Carga del logo
logo_file = st.file_uploader("📸 Sube el logo para el PDF", type=["png", "jpg", "jpeg"])

def extraer_datos_url(url):
    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "No se encontró título"
        meta_description = soup.find('meta', attrs={'name': 'description'})
        meta_description = meta_description['content'] if meta_description else "No se encontró metadescripción"
        
        # Búsqueda más exhaustiva del H1
        h1 = None
        h1_tag = soup.find('h1')
        if h1_tag:
            h1 = h1_tag.get_text(strip=True)
        if not h1:
            # Buscar en clases comunes de encabezados
            header_classes = ['entry-title', 'post-title', 'page-title', 'article-title']
            for class_name in header_classes:
                h1_candidate = soup.find(class_=class_name)
                if h1_candidate:
                    h1 = h1_candidate.get_text(strip=True)
                    break
        if not h1:
            h1 = "No se encontró H1"

        body = soup.body.get_text() if soup.body else "No se encontró contenido en el body"
        h2s = [h2.text.strip() for h2 in soup.find_all('h2')]
        return title, meta_description, h1, body, h2s
    except requests.exceptions.RequestException as e:
        st.error(f"Error al acceder a la URL {url}: {str(e)}")
        return "Error", "Error", "Error", "Error al extraer contenido", []

def analizar_contenido(api_key, contenido, keywords):
    client = OpenAI(api_key=api_key)
    prompt = f"""
    Analiza el siguiente contenido según las especificaciones de Contenido útil de Google:
    {contenido}

    Keywords principales y secundarias: {keywords}

    Proporciona:
    1. Un resumen general del contenido (máximo 150 palabras)
    2. Áreas de mejora (lista de 5 puntos)
    3. Áreas que están bien (lista de 5 puntos)
    4. Puntuación del 1 al 10 en:
       - Uso de keywords principales y secundarias
       - Contenido original
       - Organización de los H2 del contenido
       - Calidad de la redacción
       - Clasificación general del contenido

    Formato de respuesta:
    Resumen general: [Tu resumen aquí]

    Áreas de mejora:
    - [Punto 1]
    - [Punto 2]
    - [Punto 3]
    - [Punto 4]
    - [Punto 5]

    Áreas positivas:
    - [Punto 1]
    - [Punto 2]
    - [Punto 3]
    - [Punto 4]
    - [Punto 5]

    Puntuaciones:
    1. Uso de keywords: [puntuación]
    2. Contenido original: [puntuación]
    3. Organización de H2: [puntuación]
    4. Calidad de redacción: [puntuación]
    5. Clasificación general: [puntuación]
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def analizar_competencia(api_key, urls):
    client = OpenAI(api_key=api_key)
    resultados = []
    for url in urls:
        if url:
            title, meta_description, h1, body, h2s = extraer_datos_url(url)
            if title != "Error":
                prompt = f"""
                Analiza el contenido de esta página de la competencia:
                URL: {url}
                Title: {title}
                Meta Description: {meta_description}
                H1: {h1}
                H2s: {h2s}
                Contenido: {body[:1000]}  # Limitamos a 1000 caracteres para el análisis

                Proporciona:
                1. Temáticas principales que trabaja la página (máximo 3)
                2. Sector económico en el que está especializado
                3. Keywords principales y secundarias utilizadas (máximo 5 de cada una)
                4. Conclusiones sobre la calidad del contenido (máximo 100 palabras)
                5. Aspectos destacables del SEO On-Page (máximo 100 palabras)
                6. Observaciones sobre la experiencia de usuario (UX) (máximo 100 palabras)

                Formato de respuesta:
                Temáticas: [Lista de temáticas]
                Sector económico: [Sector]
                Keywords principales: [Lista de keywords]
                Keywords secundarias: [Lista de keywords]
                Calidad del contenido: [Tus conclusiones]
                SEO On-Page: [Tus observaciones]
                UX: [Tus observaciones]
                """
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                resultados.append({
                    "url": url,
                    "title": title,
                    "meta_description": meta_description,
                    "h1": h1,
                    "h2s": h2s,
                    "analisis": response.choices[0].message.content
                })
            else:
                resultados.append({
                    "url": url,
                    "title": "Error",
                    "meta_description": "Error",
                    "h1": "Error",
                    "h2s": [],
                    "analisis": "No se pudo analizar debido a un error al acceder a la URL"
                })
    return resultados

def generar_estructura_h2(api_key, analisis_competencia, keywords):
    client = OpenAI(api_key=api_key)
    prompt = f"""
    Basándote en el siguiente análisis de la competencia y keywords:
    {analisis_competencia}
    Keywords: {keywords}

    Genera una estructura de H2 optimizada para alcanzar la primera posición en Google.
    La estructura debe tener entre 5 y 8 H2s.
    Cada H2 debe ser una frase corta y atractiva que incluya keywords relevantes.

    Formato de respuesta:
    1. [H2 #1]
    2. [H2 #2]
    3. [H2 #3]
    ...
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def generar_contenido_optimizado(api_key, estructura_h2, contenido_actual, tono_marca, keywords):
    client = OpenAI(api_key=api_key)
    prompt = f"""
    Utilizando la siguiente estructura de H2:
    {estructura_h2}

    Y teniendo en cuenta el contenido actual:
    {contenido_actual[:2000]}  # Limitamos a 2000 caracteres para el análisis

    Genera un contenido optimizado que:
    1. Siga el tono de marca: {tono_marca}
    2. Respete el contenido actual siempre que sea posible
    3. Cumpla con los requisitos de Contenido Útil de Google
    4. Utilice las siguientes keywords: {keywords}
    5. Cada sección H2 debe tener al menos 2 párrafos y alrededor de 200 palabras
    6. Sigue las pautas de redacción proporcionadas (oraciones cortas, párrafos breves, lenguaje claro, etc.)

    Marca el contenido nuevo en formato HTML con <span style="color: green;">nuevo contenido</span>
    y el contenido existente en formato HTML con <span style="color: black;">contenido existente</span>.

    Utiliza el siguiente formato para la estructura:
    <h2>[Título H2]</h2>
    <p>[Contenido del párrafo]</p>

    Asegúrate de que el contenido sea coherente, informativo y valioso para el lector.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def generar_metadata(api_key, contenido_optimizado, keywords):
    client = OpenAI(api_key=api_key)
    prompt = f"""
    Basándote en el siguiente contenido optimizado y keywords:
    {contenido_optimizado[:1000]}  # Limitamos a 1000 caracteres para el análisis
    Keywords: {keywords}

    Genera:
    1. 5 Titles optimizados (máximo 60 caracteres)
    2. 5 Metadescriptions optimizadas (máximo 155 caracteres)
    3. 5 H1 optimizados (máximo 60 caracteres)

    Asegúrate de incluir las keywords principales y que sean atractivos para mejorar el CTR.

    Formato de respuesta:
    Titles:
    1. [Title 1]
    2. [Title 2]
    3. [Title 3]
    4. [Title 4]
    5. [Title 5]

    Metadescriptions:
    1. [Metadescription 1]
    2. [Metadescription 2]
    3. [Metadescription 3]
    4. [Metadescription 4]
    5. [Metadescription 5]

    H1s:
    1. [H1 1]
    2. [H1 2]
    3. [H1 3]
    4. [H1 4]
    5. [H1 5]
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def procesar_puntuaciones(puntuaciones_texto):
    puntuaciones = {}
    for line in puntuaciones_texto.strip().split('\n'):
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip().split('/')[0]  # Tomar solo el número antes del '/'
        try:
            puntuaciones[key] = float(value)
        except ValueError:
            st.warning(f"No se pudo convertir '{value}' a float para la clave '{key}'. Se omitirá esta puntuación.")
    return puntuaciones

def crear_grafica_puntuaciones(puntuaciones):
    categorias = list(puntuaciones.keys())
    valores = list(puntuaciones.values())

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(categorias, valores, color='red')

    ax.set_ylim(0, 10)
    ax.set_ylabel('Puntuación')
    ax.set_title('Puntuaciones del Contenido')

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height}',
                ha='center', va='bottom')

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return fig

def generar_pdf(url, contenido_analisis, contenido_competencia, logo_file):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    Story = []

    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontSize=16, textColor=colors.red))
    styles.add(ParagraphStyle(name='Subtitulo', fontSize=14, textColor=colors.red))
    styles.add(ParagraphStyle(name='Cuerpo', fontSize=12, textColor=colors.black))

    # Logo
    if logo_file:
        img = Image(logo_file, 1*inch, 0.5*inch)
        img.hAlign = 'RIGHT'
        Story.append(img)

    # Título y subtítulo
    Story.append(Paragraph(f"Análisis de {url}", styles['Titulo']))
    Story.append(Paragraph(f"Hemos realizado el análisis SEO de la {url} para poder optimizar el contenido y mejorar el posicionamiento orgánico.", styles['Subtitulo']))
    Story.append(Spacer(1, 12))

    # Análisis del contenido
    Story.append(Paragraph("1. Análisis del contenido", styles['Subtitulo']))
    
  # Extraer información del análisis de contenido
    resumen_match = re.search(r"Resumen general:(.*?)Áreas de mejora:", contenido_analisis, re.DOTALL)
    resumen = resumen_match.group(1).strip() if resumen_match else "No se encontró resumen"
    
    areas_mejora_match = re.search(r"Áreas de mejora:(.*?)Áreas positivas:", contenido_analisis, re.DOTALL)
    areas_mejora = areas_mejora_match.group(1).strip().split('\n') if areas_mejora_match else []
    
    areas_positivas_match = re.search(r"Áreas positivas:(.*?)Puntuaciones:", contenido_analisis, re.DOTALL)
    areas_positivas = areas_positivas_match.group(1).strip().split('\n') if areas_positivas_match else []
    
    puntuaciones_match = re.search(r"Puntuaciones:(.*?)$", contenido_analisis, re.DOTALL)
    puntuaciones = procesar_puntuaciones(puntuaciones_match.group(1)) if puntuaciones_match else {}

    Story.append(Paragraph("Resumen general del estado del contenido:", styles['Cuerpo']))
    Story.append(Paragraph(resumen, styles['Cuerpo']))
    Story.append(Spacer(1, 12))

    Story.append(Paragraph("Áreas de mejora:", styles['Cuerpo']))
    for area in areas_mejora:
        Story.append(Paragraph(f"• {area.strip()}", styles['Cuerpo']))
    Story.append(Spacer(1, 12))

    Story.append(Paragraph("Áreas positivas del contenido:", styles['Cuerpo']))
    for area in areas_positivas:
        Story.append(Paragraph(f"• {area.strip()}", styles['Cuerpo']))
    Story.append(Spacer(1, 12))

    # Gráfica de puntuaciones
    if puntuaciones:
        fig = crear_grafica_puntuaciones(puntuaciones)
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format='png')
        img_buffer.seek(0)
        img = Image(img_buffer)
        img.drawHeight = 4*inch
        img.drawWidth = 6*inch
        Story.append(img)
    else:
        Story.append(Paragraph("No se pudieron generar las puntuaciones", styles['Cuerpo']))
    Story.append(Spacer(1, 12))

    # Análisis de la competencia
    Story.append(Paragraph("2. Análisis de la competencia", styles['Subtitulo']))

    # Tabla comparativa
    data = [["URL", "Title", "H1", "Meta Description"]]
    for comp in contenido_competencia:
        data.append([comp['url'], comp['title'], comp['h1'], comp['meta_description']])
    
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    Story.append(t)
    Story.append(Spacer(1, 12))

    for comp in contenido_competencia:
        Story.append(Paragraph(f"URL: {comp['url']}", styles['Cuerpo']))
        Story.append(Paragraph("H2s encontrados:", styles['Cuerpo']))
        for h2 in comp['h2s']:
            Story.append(Paragraph(f"• {h2}", styles['Cuerpo']))
        
        analisis_lines = comp['analisis'].split('\n')
        for line in analisis_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                Story.append(Paragraph(f"{key}:", styles['Cuerpo']))
                Story.append(Paragraph(value.strip(), styles['Cuerpo']))
        Story.append(Spacer(1, 12))

    doc.build(Story)
    buffer.seek(0)
    return buffer

if st.button("🚀 Iniciar optimización"):
    if not api_key:
        st.error("Por favor, introduce tu API Key de OpenAI")
    elif not url_optimizar:
        st.error("Por favor, introduce la URL a optimizar")
    else:
        with st.spinner("Optimizando contenido..."):
            # Extraer datos de la URL a optimizar
            title, meta_description, h1, body, h2s_principal = extraer_datos_url(url_optimizar)
            if title != "Error":
                st.subheader("📊 Datos actuales de la URL")
                df = pd.DataFrame({
                    "Elemento": ["Title", "Metadescription", "H1"],
                    "Contenido": [title, meta_description, h1]
                })
                st.table(df)
                
                st.subheader("📌 H2s actuales")
                for h2 in h2s_principal:
                    st.write(f"- {h2}")

                # Análisis del contenido
                keywords = f"{keyword_principal}, {keyword_secundaria}, {keywords_adicionales}"
                analisis_contenido = analizar_contenido(api_key, body, keywords)
                st.subheader("📝 Análisis del contenido")
                st.write(analisis_contenido)

                # Crear y mostrar gráfica de puntuaciones
                puntuaciones_match = re.search(r"Puntuaciones:(.*?)$", analisis_contenido, re.DOTALL)
                if puntuaciones_match:
                    puntuaciones = procesar_puntuaciones(puntuaciones_match.group(1))
                    if puntuaciones:
                        fig = crear_grafica_puntuaciones(puntuaciones)
                        st.pyplot(fig)
                    else:
                        st.warning("No se pudieron procesar las puntuaciones correctamente.")
                else:
                    st.warning("No se encontraron puntuaciones en el análisis de contenido.")

                # Análisis de la competencia
                st.subheader("🔍 Análisis de la competencia")
                analisis_competencia = analizar_competencia(api_key, competencia_urls)
                for resultado in analisis_competencia:
                    st.write(f"URL: {resultado['url']}")
                    st.write(resultado['analisis'])
                    st.write("H2s encontrados:")
                    for h2 in resultado['h2s']:
                        st.write(f"- {h2}")
                    st.write("---")

                # Generar PDF
                pdf_buffer = generar_pdf(url_optimizar, analisis_contenido, analisis_competencia, logo_file)
                st.download_button(
                    label="📥 Descargar análisis completo (PDF)",
                    data=pdf_buffer,
                    file_name="analisis_completo.pdf",
                    mime="application/pdf"
                )

                # Generar estructura H2
                st.subheader("📌 Estructura de H2 propuesta")
                estructura_h2 = generar_estructura_h2(api_key, str(analisis_competencia), keywords)
                st.write(estructura_h2)

                # Generar contenido optimizado
                st.subheader("✨ Contenido optimizado")
                contenido_optimizado = generar_contenido_optimizado(api_key, estructura_h2, body, url_tono_marca, keywords)
                st.markdown(contenido_optimizado, unsafe_allow_html=True)

                # Generar metadata optimizada
                st.subheader("🏷️ Metadata optimizada")
                metadata_optimizada = generar_metadata(api_key, contenido_optimizado, keywords)
                st.write(metadata_optimizada)

            else:
                st.error("No se pudo acceder a la URL para optimizar. Por favor, verifica la URL e intenta nuevamente.")

if __name__ == "__main__":
    st.sidebar.title("💡 Instrucciones")
    st.sidebar.write("""
    1. Ingresa tu API Key de OpenAI
    2. Completa todos los campos requeridos
    3. Opcionalmente, sube un logo para el PDF
    4. Haz clic en "Iniciar optimización"
    5. Revisa los resultados y descarga el análisis completo en PDF
    """)