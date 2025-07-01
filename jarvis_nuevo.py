import os
import sys
import subprocess
import platform
import shutil
import openai
import pyttsx3
import time
import requests
import psutil
import random
import difflib
import speech_recognition as sr
from collections import Counter
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from datetime import datetime, timedelta


openai.api_key = "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"

HISTORIAL_PATH = "historial_jarvis.txt"
APRENDIZAJE_PATH = "comandos_mas_usados.txt"

# Permisos Google API
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar"
]

def get_gmail_service():
    creds = None
    if os.path.exists('token_gmail.pickle'):
        with open('token_gmail.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token_gmail.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def enviar_email(destinatario, asunto, cuerpo):
    try:
        service = get_gmail_service()
        message = MIMEText(cuerpo)
        message['to'] = destinatario
        message['subject'] = asunto
        create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        texto = frases_chatbot(f"Email enviado a {destinatario} con asunto '{asunto}'.")
        print(texto)
        hablar(texto)
    except Exception as e:
        print(f"No se pudo enviar el email: {e}")
        hablar("No se pudo enviar el email.")

def leer_emails(cantidad=5):
    
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', maxResults=cantidad, labelIds=['INBOX']).execute()
        mensajes = results.get('messages', [])
        if not mensajes:
            print("No hay emails en la bandeja de entrada.")
            hablar("No hay emails nuevos.")
            return
        for i, msg in enumerate(mensajes, 1):
            txt = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
            headers = {h['name']: h['value'] for h in txt['payload']['headers']}
            asunto = headers.get('Subject', '(sin asunto)')
            remitente = headers.get('From', '(desconocido)')
            fecha = headers.get('Date', '')
            resumen = f"Email {i}: '{asunto}' de {remitente} recibido el {fecha}."
            print(resumen)
            hablar(resumen)
    except Exception as e:
        print(f"No se pudieron leer los emails: {e}")
        hablar("No pude leer los emails.")

# --- BLOQUE DE CONFIRMACIÓN INTELIGENTE ---
def requiere_confirmacion(comando):
    comandos_riesgo = [
        "borrar", "eliminar", "rm -rf", "del /f", "format", "shutdown", "autodestruir",
        "mover:", "renombrar:", "descargar:", "macro_limpieza:", "script_python:",
        "crear_proyecto:", "editar:", "sobreescribir", "wipe", "erase"
    ]
    comando_lower = comando.lower()
    for key in comandos_riesgo:
        if key in comando_lower:
            return True
    return False

def confirmar_accion(accion):
    resp = input(f"¿Seguro que querés ejecutar esto? '{accion}' (sí/no): ")
    return resp.lower().strip() in ["sí", "si", "yes", "y"]

# --- BLOQUE DE RECONOCIMIENTO INTELIGENTE DE COMANDOS HUMANOS ---
def comando_parecido(comando, lista):
    comando = comando.replace(" ", "").lower()
    opciones = [x.replace(" ", "").lower() for x in lista]
    mejor = difflib.get_close_matches(comando, opciones, n=1, cutoff=0.75)
    return mejor[0] if mejor else None

def ejecutar_comando_humano(comando):
    acciones = {
        "abrir:calculadora": abrir_app_calc,
        "abrir:calc": abrir_app_calc,
        "abrir:spotify": abrir_app_spotify,
        "abrir:spotifyporfavor": abrir_app_spotify,
        "abrir:blocdenotas": abrir_app_notepad,
        "abrir:navegador": abrir_app_browser,
    }
    lista_acciones = list(acciones.keys())
    key_match = comando_parecido(comando, lista_acciones)
    if key_match:
        acciones[key_match]()
        return True
    comando_simple = comando.replace(" ", "").lower()
    if "calculadora" in comando_simple or "calc" in comando_simple:
        abrir_app_calc()
        return True
    if "spotify" in comando_simple:
        abrir_app_spotify()
        return True
    if "blocdenotas" in comando_simple or "notepad" in comando_simple:
        abrir_app_notepad()
        return True
    if "navegador" in comando_simple or "chrome" in comando_simple or "firefox" in comando_simple:
        abrir_app_browser()
        return True
    return False

def abrir_app_calc():
    sistema = platform.system()
    try:
        if sistema == "Windows":
            subprocess.Popen(["calc"], shell=True)
        elif sistema == "Darwin":
            subprocess.Popen(["open", "-a", "Calculator"])
        else:
            subprocess.Popen(["gnome-calculator"])
        texto = frases_chatbot("Calculadora abierta correctamente.")
        print(texto)
        hablar(texto)
    except Exception as e:
        print(f"No se pudo abrir la calculadora: {e}")
        hablar("No se pudo abrir la calculadora.")

def abrir_app_spotify():
    sistema = platform.system()
    try:
        if sistema == "Windows":
            subprocess.Popen(["start", "spotify"], shell=True)
        elif sistema == "Darwin":
            subprocess.Popen(["open", "-a", "Spotify"])
        else:
            subprocess.Popen(["spotify"])
        texto = frases_chatbot("Spotify abierto correctamente.")
        print(texto)
        hablar(texto)
    except Exception as e:
        print(f"No se pudo abrir Spotify: {e}")
        hablar("No se pudo abrir Spotify.")

def abrir_app_notepad():
    sistema = platform.system()
    try:
        if sistema == "Windows":
            subprocess.Popen(["notepad"], shell=True)
        elif sistema == "Darwin":
            subprocess.Popen(["open", "-a", "TextEdit"])
        else:
            subprocess.Popen(["gedit"])
        texto = frases_chatbot("Bloc de notas abierto correctamente.")
        print(texto)
        hablar(texto)
    except Exception as e:
        print(f"No se pudo abrir el bloc de notas: {e}")
        hablar("No se pudo abrir el bloc de notas.")

def abrir_app_browser():
    try:
        import webbrowser
        webbrowser.open("https://www.google.com")
        texto = frases_chatbot("Navegador abierto correctamente.")
        print(texto)
        hablar(texto)
    except Exception as e:
        print(f"No se pudo abrir el navegador: {e}")
        hablar("No se pudo abrir el navegador.")

# --- BLOQUE UTILIDADES ---
def hablar(texto):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 178)
        engine.say(texto)
        engine.runAndWait()
    except Exception as e:
        print(f"[JARVIS] (No se pudo leer por voz: {e})")

def escuchar():
    r = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("🎤 JARVIS te está escuchando... hablá claro:")
        hablar("Te escucho Martín.")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)
    try:
        texto = r.recognize_google(audio, language="es-AR")
        print(f"Vos dijiste: {texto}")
        hablar(f"Entendí: {texto}")
        return texto
    except Exception as e:
        print("No pude entenderte. Intentá de nuevo.")
        hablar("No pude entenderte. Intentá de nuevo.")
        return ""

def guardar_historial(comando):
    with open(HISTORIAL_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {comando}\n")

def guardar_aprendizaje(comando):
    with open(APRENDIZAJE_PATH, "a", encoding="utf-8") as f:
        f.write(f"{comando}\n")

def frases_chatbot(texto, usuario="Martín"):
    counter = Counter()
    if os.path.exists(APRENDIZAJE_PATH):
        with open(APRENDIZAJE_PATH, encoding="utf-8") as f:
            for linea in f:
                cmd = linea.strip().split(":", 1)[0]
                counter[cmd] += 1
    if counter:
        top = counter.most_common(1)[0][0]
        if top in texto:
            return f"¡Otra vez {top}! Veo que te gusta usar ese comando. {texto}"
    frases = [
        f"¡Listo {usuario}! Acción completada.",
        f"Hecho, {usuario}. ¿Te ayudo con algo más?",
        f"Pedido realizado. ¿Algo más que quieras hoy, {usuario}?",
        f"Acción ejecutada correctamente.",
        f"Todo OK. ¿Seguimos con otra tarea?",
        f"Perfecto, tarea hecha. ¿Algo más?"
    ]
    return random.choice(frases) + " " + texto

def bienvenida():
    mensaje = "\n" + "="*60 + "\n" + \
              "  🦾  HOLA MARTÍN, SOY JARVIS SUPREMO. ¡CONFIRMACIÓN INTELIGENTE Y ACCIONES INSTANTÁNEAS!\n" + \
              "="*60 + "\n" + \
              "Reconozco tus órdenes aunque tengan errores y ejecuto las apps más comunes directo.\n" + \
              "Probá: crear, editar, mover, copiar, buscar, abrir, descargar archivos, dictado por voz y más.\n" + \
              "Escribí 'salir' para cerrar JARVIS.\n"
    print(mensaje)
    hablar("Hola Martín, soy Jarvis. Reconozco tus pedidos aunque tengan errores. Listo para tus órdenes.")

# --- FUNCIONES AVANZADAS DE ARCHIVOS Y AUTOMATIZACIÓN ---
def listar_archivos_carpeta(path="."):
    archivos = os.listdir(path)
    if not archivos:
        return "No hay archivos ni carpetas en la ubicación actual."
    return "\n".join(archivos)

def editar_archivo(nombre, texto, modo="a"):
    try:
        with open(nombre, modo, encoding="utf-8") as f:
            f.write(texto + "\n")
        return frases_chatbot(f"Archivo '{nombre}' editado/agregado correctamente.")
    except Exception as e:
        return f"No se pudo editar el archivo: {e}"

def mover_archivo(nombre, destino):
    try:
        shutil.move(nombre, destino)
        return frases_chatbot(f"Archivo '{nombre}' movido a '{destino}'.")
    except Exception as e:
        return f"No se pudo mover el archivo: {e}"

def copiar_archivo(nombre, nuevo_nombre):
    try:
        shutil.copy2(nombre, nuevo_nombre)
        return frases_chatbot(f"Archivo '{nombre}' copiado como '{nuevo_nombre}'.")
    except Exception as e:
        return f"No se pudo copiar el archivo: {e}"

def renombrar_archivo(nombre, nuevo_nombre):
    try:
        os.rename(nombre, nuevo_nombre)
        return frases_chatbot(f"Archivo '{nombre}' renombrado a '{nuevo_nombre}'.")
    except Exception as e:
        return f"No se pudo renombrar el archivo: {e}"

def buscar_archivos(palabra, path="."):
    encontrados = []
    for root, dirs, files in os.walk(path):
        for archivo in files:
            if palabra.lower() in archivo.lower():
                encontrados.append(os.path.join(root, archivo))
    if encontrados:
        return "Archivos encontrados:\n" + "\n".join(encontrados)
    else:
        return "No se encontraron archivos con esa palabra."

def info_sistema(tipo):
    if tipo == "ram":
        ram = psutil.virtual_memory()
        return f"RAM usada: {ram.used // (1024*1024)} MB / Total: {ram.total // (1024*1024)} MB"
    elif tipo == "cpu":
        cpu = psutil.cpu_percent(interval=1)
        return f"Uso de CPU actual: {cpu}%"
    elif tipo == "disco":
        disco = psutil.disk_usage('.')
        return f"Espacio en disco: {disco.used // (1024*1024)} MB usados / {disco.total // (1024*1024)} MB totales"
    elif tipo == "procesos":
        procesos = [p.info["name"] for p in psutil.process_iter(["name"])]
        return "Procesos en ejecución:\n" + "\n".join(procesos)
    else:
        return "No se reconoce el tipo de información de sistema."

def descargar_archivo(url, nombre=None):
    try:
        r = requests.get(url, stream=True, timeout=15)
        if not nombre:
            nombre = url.split("/")[-1] or "descarga"
        with open(nombre, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return frases_chatbot(f"Archivo descargado como '{nombre}'.")
    except Exception as e:
        return f"No se pudo descargar el archivo: {e}"

def buscar_en_web(query):
    try:
        import webbrowser
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return frases_chatbot("Busqué tu consulta en Google y te abrí los resultados.")
    except Exception as e:
        return f"No pude abrir el navegador: {e}"

def crear_macro_limpieza(carpeta):
    nombre = f"limpieza_{carpeta.replace('/', '_').replace(' ', '_')}.bat"
    with open(nombre, "w") as f:
        f.write(f'del /Q "{carpeta}\\*.*"\n')
    return frases_chatbot(f"Macro de limpieza creada: {nombre}")

def crear_proyecto(tipo, nombre):
    if tipo.lower() == "flask":
        os.makedirs(nombre, exist_ok=True)
        with open(os.path.join(nombre, "app.py"), "w") as f:
            f.write("""from flask import Flask\napp = Flask(__name__)\n\n@app.route('/')\ndef home():\n    return "¡Hola, Flask desde JARVIS!"\n\nif __name__ == '__main__':\n    app.run(debug=True)\n""")
        return frases_chatbot(f"Proyecto Flask creado en la carpeta '{nombre}'.")
    elif tipo.lower() == "node":
        os.makedirs(nombre, exist_ok=True)
        with open(os.path.join(nombre, "index.js"), "w") as f:
            f.write("""const express = require('express');\nconst app = express();\napp.get('/', (req, res) => res.send('¡Hola desde Node/Jarvis!'));\napp.listen(3000, () => console.log('Servidor funcionando en puerto 3000'));\n""")
        return frases_chatbot(f"Proyecto Node.js creado en la carpeta '{nombre}'.")
    else:
        return "Por ahora solo puedo crear proyectos Flask y Node.js."

# --- EJECUCIÓN PRINCIPAL DE COMANDOS ---
def ejecutar_archivo(comando):
    # --- INTELIGENCIA: reconoce acciones humanas y ejecuta si corresponde ---
    if ejecutar_comando_humano(comando):
        return
    # --- RESTO: IA y automatización ---
    if comando.startswith("carpeta:") or comando.startswith("crear:carpeta:"):
        nombre = comando.replace("crear:carpeta:", "carpeta:").split("carpeta:",1)[1].strip()
        if not os.path.exists(nombre):
            os.makedirs(nombre)
            texto = frases_chatbot(f"Carpeta '{nombre}' creada.")
            print(texto)
            hablar(texto)
        else:
            print(f"La carpeta '{nombre}' ya existe.")
            hablar(f"La carpeta {nombre} ya existe.")
    elif comando.startswith("archivo:") or comando.startswith("crear:archivo:"):
        parte = comando.replace("crear:archivo:", "archivo:").split("archivo:",1)[1]
        partes = parte.split(":",1)
        if len(partes) == 2:
            nombre, contenido = partes
            with open(nombre.strip(), "w", encoding="utf-8") as f:
                f.write(contenido.strip().strip('"'))
            texto = frases_chatbot(f"Archivo '{nombre.strip()}' creado con el contenido indicado.")
            print(texto)
            hablar(texto)
        else:
            print("Formato incorrecto para crear archivo.")
            hablar("Formato incorrecto para crear archivo.")
    elif comando.startswith("editar:"):
        partes = comando.split("editar:",1)[1].split(":",1)
        if len(partes) == 2:
            nombre, texto = partes
            res = editar_archivo(nombre.strip(), texto.strip(), modo="a")
            print(res)
            hablar(res)
        else:
            print("Formato incorrecto para editar archivo.")
            hablar("Formato incorrecto para editar archivo.")
    elif comando.startswith("mover:"):
        partes = comando.split("mover:",1)[1].split(":",1)
        if len(partes) == 2:
            nombre, destino = partes
            res = mover_archivo(nombre.strip(), destino.strip())
            print(res)
            hablar(res)
        else:
            print("Formato incorrecto para mover archivo.")
            hablar("Formato incorrecto para mover archivo.")
    elif comando.startswith("copiar:"):
        partes = comando.split("copiar:",1)[1].split(":",1)
        if len(partes) == 2:
            nombre, nuevo_nombre = partes
            res = copiar_archivo(nombre.strip(), nuevo_nombre.strip())
            print(res)
            hablar(res)
        else:
            print("Formato incorrecto para copiar archivo.")
            hablar("Formato incorrecto para copiar archivo.")
    elif comando.startswith("renombrar:"):
        partes = comando.split("renombrar:",1)[1].split(":",1)
        if len(partes) == 2:
            nombre, nuevo_nombre = partes
            res = renombrar_archivo(nombre.strip(), nuevo_nombre.strip())
            print(res)
            hablar(res)
        else:
            print("Formato incorrecto para renombrar archivo.")
            hablar("Formato incorrecto para renombrar archivo.")
    elif comando.startswith("buscar:"):
        palabra = comando.split("buscar:",1)[1].strip()
        res = buscar_archivos(palabra)
        print(res)
        hablar(res)
    elif comando.startswith("borrar:"):
        nombre = comando.split("borrar:",1)[1].strip()
        if os.path.isdir(nombre):
            os.rmdir(nombre)
            texto = frases_chatbot(f"Carpeta '{nombre}' borrada.")
            print(texto)
            hablar(texto)
        elif os.path.isfile(nombre):
            os.remove(nombre)
            texto = frases_chatbot(f"Archivo '{nombre}' borrado.")
            print(texto)
            hablar(texto)
        else:
            print(f"No se encontró '{nombre}'.")
            hablar(f"No se encontró {nombre}.")
    elif comando.startswith("abrir:") or comando.startswith("abrir "):
        archivo = comando.replace("abrir:", "").replace("abrir ", "").strip()
        sistema = platform.system()
        try:
            if sistema == "Windows":
                os.startfile(archivo)
            elif sistema == "Darwin":
                subprocess.Popen(["open", archivo])
            else:
                subprocess.Popen(["xdg-open", archivo])
            texto = frases_chatbot(f"'{archivo}' abierto correctamente.")
            print(texto)
            hablar(texto)
        except Exception as e:
            print(f"No se pudo abrir el archivo: {e}")
            hablar(f"No se pudo abrir el archivo {archivo}")
    elif comando.startswith("listar_archivos:"):
        path = comando.split("listar_archivos:",1)[1].strip() or "."
        texto = "Archivos y carpetas en la ubicación seleccionada:\n" + listar_archivos_carpeta(path)
        print(texto)
        hablar("Listando archivos y carpetas en la ubicación seleccionada.")
    elif comando.startswith("script_python:"):
        partes = comando.split("script_python:",1)[1].split(":",1)
        if len(partes) == 2:
            nombre, contenido = partes
            with open(nombre.strip(), "w", encoding="utf-8") as f:
                f.write(contenido.strip().strip('"'))
            texto = frases_chatbot(f"Script Python '{nombre.strip()}' creado. Ejecutando...")
            print(texto)
            hablar(texto)
            try:
                subprocess.run(["python", nombre.strip()])
            except Exception as e:
                print(f"No se pudo ejecutar el script: {e}")
                hablar(f"No se pudo ejecutar el script.")
        else:
            print("Formato incorrecto para crear script Python.")
            hablar("Formato incorrecto para crear script Python.")
    elif comando.startswith("info_sistema:"):
        tipo = comando.split("info_sistema:",1)[1].strip().lower()
        texto = info_sistema(tipo)
        print(texto)
        hablar(texto)
    elif comando.startswith("descargar:"):
        partes = comando.split("descargar:",1)[1].split(":",1)
        if len(partes) == 2:
            url, nombre = partes
            texto = descargar_archivo(url.strip(), nombre.strip())
        else:
            url = comando.split("descargar:",1)[1].strip()
            texto = descargar_archivo(url)
        print(texto)
        hablar(texto)
    elif comando.startswith("buscar_web:"):
        query = comando.split("buscar_web:",1)[1].strip()
        texto = buscar_en_web(query)
        print(texto)
        hablar(texto)
    elif comando.startswith("macro_limpieza:"):
        carpeta = comando.split("macro_limpieza:",1)[1].strip()
        texto = crear_macro_limpieza(carpeta)
        print(texto)
        hablar(texto)
    elif comando.startswith("crear_proyecto:"):
        partes = comando.split("crear_proyecto:",1)[1].split(":",1)
        if len(partes) == 2:
            tipo, nombre = partes
            texto = crear_proyecto(tipo.strip(), nombre.strip())
            print(texto)
            hablar(texto)
        else:
            print("Formato incorrecto para crear proyecto.")
            hablar("Formato incorrecto para crear proyecto.")
    # --- EMAIL GMAIL ---
    elif comando.startswith("enviar_email:"):
        partes = comando.split("enviar_email:", 1)[1].split(":", 2)
        if len(partes) == 3:
            destinatario, asunto, cuerpo = partes
            enviar_email(destinatario.strip(), asunto.strip(), cuerpo.strip())
        else:
            print("Formato incorrecto para enviar email. Usá: enviar_email:destinatario:asunto:cuerpo")
            hablar("Formato incorrecto para enviar email.")
    # --- LEER EMAILS ---
    elif comando.startswith("leer_emails"):
        partes = comando.split("leer_emails",1)
        cantidad = 5
        if len(partes) > 1 and partes[1].strip().isdigit():
            cantidad = int(partes[1].strip())
        leer_emails(cantidad)
    elif comando.lower() in ["salir", "exit", "quit"]:
        print("Cerrando JARVIS. ¡Hasta la próxima, Martín!")
        hablar("Hasta la próxima, Martín.")
        sys.exit(0)
    else:
        try:
            subprocess.Popen(comando, shell=True)
            texto = frases_chatbot("Pedido ejecutado.")
            print(texto)
            hablar(texto)
        except Exception as e:
            print(f"Error al ejecutar: {e}")
            hablar("Hubo un error ejecutando el pedido.")

def consultar_chatgpt(prompt):
    system_prompt = """
Sos JARVIS CLI, un traductor entre lenguaje natural y comandos para automatizar tareas en PC.
Convertí el pedido del usuario en comandos del tipo:
- carpeta:nombrecarpeta
- archivo:nombre.txt:contenido
- borrar:nombrearchivo_o_carpeta
- editar:nombre.txt:texto
- mover:nombre.txt:nueva_ubicacion
- copiar:nombre.txt:nombre_copia.txt
- renombrar:nombre_viejo.txt:nombre_nuevo.txt
- buscar:palabra
- abrir:nombre.txt
- script_python:nombre.py:contenido
- abrir spotify
- abrir calculadora
- abrir bloc de notas
- abrir navegador
- reproducir musica
- listar_archivos:ubicacion
- info_sistema:ram/cpu/disco/procesos
- descargar:url:nombre (o descargar:url)
- buscar_web:consulta
- macro_limpieza:carpeta
- crear_proyecto:tipo:nombre
- enviar_email:destinatario:asunto:cuerpo
- leer_emails:n
Si el pedido es muy complejo o requiere varias acciones, devolvé los comandos separados por '|'.
NO EXPLIQUES, SOLO DEVOLVÉ EL COMANDO.
"""
    try:
        client = openai.OpenAI(api_key=openai.api_key)
        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700,
            temperature=0
        )
        comando = respuesta.choices[0].message.content.strip()
        return comando
    except Exception as e:
        return None

def main():
    bienvenida()
    while True:
        entrada = input("JARVIS> ")
        if entrada.strip().lower() in ["escuchame", "escuchar", "voice", "mic"]:
            texto = escuchar()
            if texto:
                entrada = texto
            else:
                continue
        if entrada.strip().lower() in ["salir", "exit", "quit"]:
            print("Cerrando JARVIS. ¡Hasta la próxima, Martín!")
            hablar("Hasta la próxima, Martín.")
            sys.exit(0)
        comando_final = consultar_chatgpt(entrada)
        if not comando_final:
            print("No pude entender el pedido. Probá con otra frase.")
            hablar("No pude entender el pedido. Probá con otra frase.")
            continue
        for cmd in comando_final.split("|"):
            cmd = cmd.strip()
            if not cmd:
                continue
            if requiere_confirmacion(cmd):
                if not confirmar_accion(cmd):
                    print("Acción cancelada.")
                    hablar("Acción cancelada.")
                    continue
            guardar_historial(entrada)
            guardar_aprendizaje(cmd)
            ejecutar_archivo(cmd)

if __name__ == "__main__":
    main()
texto
