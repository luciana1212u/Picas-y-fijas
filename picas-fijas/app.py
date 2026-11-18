import os
import random
import threading

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")
app.json.ensure_ascii = False  

jugadores = set()
juegos = {}
siguiente_id = 1
candado = threading.Lock()

SIN_COMPLETAR = "sin completar"   # creado, esperando al segundo jugador
EN_JUEGO = "en juego"             # ya hay dos jugadores
TERMINADO = "terminado"           # alguien adivinó el número


# ---------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------
def error(mensaje, codigo):
    # Devuelve un mensaje de error con su codigo
    return jsonify({"error": mensaje}), codigo


def validar_numero(numero):
    """Devuelve un mensaje de error si el numero no es valido, o None si esta bien."""
    if not isinstance(numero, str):
        return "El numero debe enviarse como texto, por ejemplo \"4271\""
    if not numero.isdigit():
        return "El numero solo puede tener digitos (sin letras ni simbolos)"
    if len(numero) != 4:
        return "El numero debe tener exactamente 4 digitos"
    if len(set(numero)) != 4:
        return "Los 4 digitos deben ser diferentes"
    return None


def calcular_fijas_picas(secreto, intento):
    """Fija = misma cifra en la misma posicion. Pica = cifra existe pero en otra posicion."""
    fijas = 0
    picas = 0
    for i in range(4):
        if intento[i] == secreto[i]:
            fijas += 1
        elif intento[i] in secreto:
            picas += 1
    return fijas, picas


def resumen(juego):
    """Datos publicos de un juego (nunca muestra los numeros secretos mientras se juega)."""
    datos = {
        "id": juego["id"],
        "estado": juego["estado"],
        "creador": juego["jugador1"],
        "jugador2": juego["jugador2"],
        "turno": juego["turno"],
        "ganador": juego["ganador"],
    }
    return datos


def buscar_juego(juego_id):
    # Busca un juego por su identificador
    return juegos.get(juego_id)


def leer_json():
    # silent=True: si el JSON es invalido devuelve None en lugar de lanzar error
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return {}
    return datos


# ---------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------
@app.route("/")
def inicio():
    # Sirve el front basico
    return send_from_directory("static", "index.html")


@app.route("/health")
def health():
    # Lo usa Kubernetes para saber si el pod esta vivo
    return jsonify({"status": "ok"})


# POST /login  -> registra el nombre del jugador
@app.route("/login", methods=["POST"])
def login():
    nombre = leer_json().get("nombre")
    if not isinstance(nombre, str) or nombre.strip() == "":
        return error("Debes enviar un 'nombre' valido", 400)
    nombre = nombre.strip()
    with candado:
        jugadores.add(nombre)
    return jsonify({"mensaje": "Bienvenido " + nombre, "nombre": nombre})


# POST /juego  -> crear un juego
@app.route("/juego", methods=["POST"])
def crear_juego():
    global siguiente_id
    datos = leer_json()
    nombre = datos.get("nombre")
    numero = datos.get("numero")

    if nombre not in jugadores:
        return error("Jugador no registrado, primero haz /login", 401)
    problema = validar_numero(numero)
    if problema:
        return error(problema, 400)

    with candado:
        juego = {
            "id": siguiente_id,
            "estado": SIN_COMPLETAR,
            "jugador1": nombre,
            "jugador2": None,
            "secretos": {nombre: numero},
            "turno": None,
            "ganador": None,
            "intentos": [],
        }
        juegos[siguiente_id] = juego
        siguiente_id += 1
    return jsonify(resumen(juego)), 201


# PUT /juego/{id}  -> unirse a un juego
@app.route("/juego/<int:juego_id>", methods=["PUT"])
def unirse(juego_id):
    datos = leer_json()
    nombre = datos.get("nombre")
    numero = datos.get("numero")

    if nombre not in jugadores:
        return error("Jugador no registrado, primero haz /login", 401)
    problema = validar_numero(numero)
    if problema:
        return error(problema, 400)

    with candado:
        juego = buscar_juego(juego_id)
        if juego is None:
            return error("El juego no existe", 404)
        if juego["estado"] != SIN_COMPLETAR:
            return error("El juego ya tiene dos jugadores", 409)
        if nombre == juego["jugador1"]:
            return error("No puedes unirte a tu propio juego", 409)

        juego["jugador2"] = nombre
        juego["secretos"][nombre] = numero
        juego["estado"] = EN_JUEGO
        # El primer turno se escoge al azar
        juego["turno"] = random.choice([juego["jugador1"], juego["jugador2"]])
    return jsonify(resumen(juego))


# POST /juego/{id}/jugar  -> enviar un intento
@app.route("/juego/<int:juego_id>/jugar", methods=["POST"])
def jugar(juego_id):
    datos = leer_json()
    nombre = datos.get("nombre")
    numero = datos.get("numero")

    if nombre not in jugadores:
        return error("Jugador no registrado, primero haz /login", 401)
    problema = validar_numero(numero)
    if problema:
        return error(problema, 400)

    with candado:
        juego = buscar_juego(juego_id)
        if juego is None:
            return error("El juego no existe", 404)
        if juego["estado"] == SIN_COMPLETAR:
            return error("El juego aun no inicia, falta el segundo jugador", 409)
        if juego["estado"] == TERMINADO:
            return error("El juego ya termino, gano " + juego["ganador"], 409)
        if nombre not in juego["secretos"]:
            return error("No participas en este juego", 403)
        if juego["turno"] != nombre:
            return error("No es tu turno, le toca a " + juego["turno"], 409)


        oponente = juego["jugador2"] if nombre == juego["jugador1"] else juego["jugador1"]
        fijas, picas = calcular_fijas_picas(juego["secretos"][oponente], numero)

        juego["intentos"].append(
            {"jugador": nombre, "numero": numero, "fijas": fijas, "picas": picas}
        )

        if fijas == 4:
            juego["estado"] = TERMINADO
            juego["ganador"] = nombre
            juego["turno"] = None
        else:
            juego["turno"] = oponente

        respuesta = {"fijas": fijas, "picas": picas, "estado": juego["estado"],
                     "ganador": juego["ganador"], "turno": juego["turno"]}
    return jsonify(respuesta)


# GET /juego/{id}  -> ver el estado de un juego
@app.route("/juego/<int:juego_id>", methods=["GET"])
def ver_juego(juego_id):
    with candado:
        juego = buscar_juego(juego_id)
        if juego is None:
            return error("El juego no existe", 404)
        datos = resumen(juego)
        datos["intentos"] = juego["intentos"]
        if juego["estado"] == TERMINADO:

            datos["secretos"] = juego["secretos"]
    return jsonify(datos)


# GET /juego  -> listar los juegos (opcional: ?estado=terminado)
@app.route("/juego", methods=["GET"])
def listar_juegos():
    filtro = request.args.get("estado")
    with candado:
        lista = [resumen(j) for j in juegos.values()]
    if filtro:
        lista = [j for j in lista if j["estado"] == filtro]
    return jsonify(lista)


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=puerto)
