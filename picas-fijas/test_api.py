# Pruebas automáticas. Se ejecutan con:  python test_api.py
from app import app, calcular_fijas_picas, validar_numero

cliente = app.test_client()


def prueba(descripcion, condicion):
    print(("OK    " if condicion else "FALLA ") + descripcion)
    assert condicion, descripcion


# --- Reglas del número ---
prueba("ejemplo del enunciado: 4271 vs 1234 = 1 fija, 2 picas", calcular_fijas_picas("4271", "1234") == (1, 2))
prueba("4271 vs 4271 = 4 fijas", calcular_fijas_picas("4271", "4271") == (4, 0))
prueba("número válido", validar_numero("0123") is None)
prueba("rechaza texto", validar_numero("12a4") is not None)
prueba("rechaza dígitos repetidos", validar_numero("1123") is not None)
prueba("rechaza longitud distinta de 4", validar_numero("123") is not None and validar_numero("12345") is not None)
prueba("rechaza que no sea string", validar_numero(1234) is not None)

# --- Flujo completo del juego ---
prueba("login ana", cliente.post("/login", json={"nombre": "ana"}).status_code == 200)
prueba("login luis", cliente.post("/login", json={"nombre": "luis"}).status_code == 200)
prueba("login sin nombre = 400", cliente.post("/login", json={}).status_code == 400)

prueba("crear sin login = 401", cliente.post("/juego", json={"nombre": "x", "numero": "1234"}).status_code == 401)
prueba("crear con número malo = 400", cliente.post("/juego", json={"nombre": "ana", "numero": "1111"}).status_code == 400)

r = cliente.post("/juego", json={"nombre": "ana", "numero": "4271"})
prueba("crear juego = 201", r.status_code == 201)
juego_id = r.get_json()["id"]
prueba("estado inicial 'sin completar'", r.get_json()["estado"] == "sin completar")

prueba("jugar antes de empezar = 409", cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": "ana", "numero": "1234"}).status_code == 409)
prueba("unirse a tu propio juego = 409", cliente.put(f"/juego/{juego_id}", json={"nombre": "ana", "numero": "1234"}).status_code == 409)
prueba("unirse a juego inexistente = 404", cliente.put("/juego/999", json={"nombre": "luis", "numero": "1234"}).status_code == 404)

r = cliente.put(f"/juego/{juego_id}", json={"nombre": "luis", "numero": "5678"})
prueba("luis se une = 200 y el juego queda 'en juego'", r.status_code == 200 and r.get_json()["estado"] == "en juego")
prueba("un tercero no puede unirse = 409", cliente.put(f"/juego/{juego_id}", json={"nombre": "ana", "numero": "1234"}).status_code == 409)

turno = r.get_json()["turno"]
prueba("el turno inicial es ana o luis", turno in ("ana", "luis"))
otro = "luis" if turno == "ana" else "ana"

prueba("el que no tiene turno recibe 409", cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": otro, "numero": "1234"}).status_code == 409)

# Números secretos: ana=4271, luis=5678
intento_ana = "5612"   # contra 5678 -> fijas: 5 y 6 = 2 ; picas: 0
intento_luis = "1234"  # contra 4271 -> 1 fija, 2 picas
intento_ganador_ana = "5678"
intento_ganador_luis = "4271"

if turno == "ana":
    r = cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": "ana", "numero": intento_ana})
    prueba("ana: 5612 vs 5678 = 2 fijas 0 picas", (r.get_json()["fijas"], r.get_json()["picas"]) == (2, 0))
    r = cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": "luis", "numero": intento_luis})
    prueba("luis: 1234 vs 4271 = 1 fija 2 picas", (r.get_json()["fijas"], r.get_json()["picas"]) == (1, 2))
    r = cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": "ana", "numero": intento_ganador_ana})
    ganador_esperado = "ana"
else:
    r = cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": "luis", "numero": intento_luis})
    prueba("luis: 1234 vs 4271 = 1 fija 2 picas", (r.get_json()["fijas"], r.get_json()["picas"]) == (1, 2))
    r = cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": "ana", "numero": intento_ana})
    prueba("ana: 5612 vs 5678 = 2 fijas 0 picas", (r.get_json()["fijas"], r.get_json()["picas"]) == (2, 0))
    r = cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": "luis", "numero": intento_ganador_luis})
    ganador_esperado = "luis"

prueba("4 fijas termina el juego", r.get_json()["estado"] == "terminado" and r.get_json()["ganador"] == ganador_esperado)

r = cliente.get(f"/juego/{juego_id}")
prueba("GET /juego/{id} muestra ganador, intentos y secretos al terminar",
       r.get_json()["ganador"] == ganador_esperado and len(r.get_json()["intentos"]) == 3 and "secretos" in r.get_json())
prueba("no se puede jugar un juego terminado = 409", cliente.post(f"/juego/{juego_id}/jugar", json={"nombre": "ana", "numero": "1234"}).status_code == 409)

# --- Secreto oculto mientras se juega ---
r = cliente.post("/juego", json={"nombre": "ana", "numero": "1234"})
id2 = r.get_json()["id"]
prueba("GET de juego sin terminar no revela secretos", "secretos" not in cliente.get(f"/juego/{id2}").get_json())

# --- Listado ---
lista = cliente.get("/juego").get_json()
prueba("GET /juego lista los 2 juegos", len(lista) == 2)
prueba("filtro ?estado=terminado", len(cliente.get("/juego?estado=terminado").get_json()) == 1)
prueba("filtro ?estado=sin completar", len(cliente.get("/juego?estado=sin completar").get_json()) == 1)
prueba("front en /", cliente.get("/").status_code == 200)

print("\nTodas las pruebas pasaron")
