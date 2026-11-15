# Picas y Fijas distribuido (Flask + Kubernetes)

API REST en Python (Flask) con JSON, sin base de datos (todo en memoria), con un front básico y listo para desplegar en Kubernetes (Killercoda).

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `app.py` | Todo el servidor (endpoints y reglas del juego) |
| `static/index.html` | Front básico para probar el juego |
| `requirements.txt` | Dependencias (solo Flask) |
| `Dockerfile` | Convierte la app en una imagen Docker |
| `k8s.yaml` | Deployment y Service de Kubernetes |
| `test_api.py` | Pruebas automáticas |

## Ejecutar en el computador (sin Docker)

```bash
pip install -r requirements.txt
python app.py
```

Abrir http://localhost:3000 para el front. Para las pruebas automáticas, `python test_api.py`.

## Endpoints

Los jugadores se identifican con el campo `nombre` que enviaron en `/login`. Los números siempre se envían como texto, por ejemplo `"4271"`.

| Método y ruta | Cuerpo JSON | Qué hace |
|---|---|---|
| `POST /login` | `{"nombre":"ana"}` | Registra al jugador |
| `POST /juego` | `{"nombre":"ana","numero":"4271"}` | Crea un juego (queda `sin completar`) |
| `PUT /juego/{id}` | `{"nombre":"luis","numero":"5678"}` | Se une. El juego pasa a `en juego` y se sortea quién empieza |
| `POST /juego/{id}/jugar` | `{"nombre":"ana","numero":"1234"}` | Envía un intento y devuelve fijas y picas, solo si es su turno |
| `GET /juego/{id}` | | Estado, turno, ganador e historial de intentos |
| `GET /juego` | | Lista de juegos. Filtro opcional `?estado=terminado` |

Estados de un juego: `sin completar`, `en juego`, `terminado`.

Códigos de respuesta: 200/201 correcto, 400 número o datos inválidos, 401 jugador sin login, 403 no participa en ese juego, 404 juego no existe, 409 acción no permitida en este momento (no es tu turno, juego lleno, juego terminado).

### Reglas de validación del número

Debe ser texto, solo dígitos, exactamente 4 dígitos y todos diferentes (`1123`, `12a4` y `123` se rechazan). Se aplica al crear, al unirse y en cada intento.

### Fijas y picas

Se compara el intento contra el número secreto del oponente. Misma cifra en la misma posición es una fija. La cifra existe pero en otra posición es una pica. Ejemplo: secreto `4271`, intento `1234` da 1 fija (el 2) y 2 picas (el 4 y el 1). Con 4 fijas el que jugó gana y el juego queda `terminado`.

## Cómo funciona el código (para sustentar)

- `jugadores` es un conjunto con los nombres registrados y `juegos` es un diccionario `id -> juego`. Esa es toda la "base de datos".
- Cada juego guarda: jugador1, jugador2, los números secretos de cada uno, de quién es el turno, el ganador y la lista de intentos.
- `validar_numero()` y `calcular_fijas_picas()` son las dos funciones con la lógica del juego.
- `random.choice` escoge quién juega primero al unirse el segundo jugador. Después el turno se alterna en `/jugar`.
- Los números secretos no se muestran en `GET /juego/{id}` hasta que el juego termina.
- `candado` (un `threading.Lock`) evita que dos peticiones simultáneas modifiquen un juego a la vez.
- `/health` lo usa Kubernetes (readinessProbe) para saber si el pod ya está listo.
- **Se usa 1 sola réplica** porque los juegos están en la memoria de cada pod. Con 2 réplicas cada pod tendría sus propios juegos. Para escalar haría falta una base de datos compartida, que el enunciado dice que no es necesaria.

## Desplegar en Kubernetes (Killercoda)

Killercoda crea un cluster de 2 nodos. Una imagen construida en un nodo no existe en el otro, por eso se sube a Docker Hub y el cluster la descarga desde allí.

### Paso 1. Subir el código a un repositorio público de GitHub

```bash
git init
git add .
git commit -m "Picas y fijas distribuido"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/picas-fijas.git
git push -u origin main
```

### Paso 2. Construir y subir la imagen a Docker Hub

Necesitas una cuenta gratis en https://hub.docker.com y Docker Desktop instalado. En la carpeta del proyecto:

```bash
docker login
docker build -t TU_USUARIO/picas-fijas:1.0 .
docker push TU_USUARIO/picas-fijas:1.0
```

Si no tienes Docker en tu computador, puedes hacer lo mismo desde el terminal de Killercoda (playground "Ubuntu", que trae Docker): `git clone` de tu repo y los mismos tres comandos.

### Paso 3. Abrir Killercoda

1. Entrar a https://killercoda.com/playgrounds/scenario/kubernetes (se puede iniciar sesión con GitHub).
2. Esperar a que cargue el terminal (ya tiene `kubectl`).

### Paso 4. Desplegar

```bash
git clone https://github.com/TU_USUARIO/picas-fijas.git
cd picas-fijas
sed -i 's/TU_USUARIO/tu_usuario_de_dockerhub/' k8s.yaml
kubectl apply -f k8s.yaml
kubectl get pods
kubectl get svc picas-fijas
```

Esperar a que el pod aparezca en `Running` y `1/1` (`kubectl get pods -w`, salir con Ctrl+C).

### Paso 5. Probar

Por línea de comandos desde el mismo terminal (el servicio escucha en el puerto 30080 del nodo):

```bash
curl localhost:30080/health
curl -X POST localhost:30080/login -H 'Content-Type: application/json' -d '{"nombre":"ana"}'
```

Para ver el front en el navegador, en Killercoda abrir el menú superior derecho (Traffic / Ports), poner el puerto **30080** y abrir el enlace que genera. Si ese menú no ofrece el puerto, usar un port-forward y exponer el puerto 3000:

```bash
kubectl port-forward --address 0.0.0.0 svc/picas-fijas 3000:3000
```

Y abrir el puerto 3000 desde Traffic / Ports.

### Comandos útiles si algo falla

```bash
kubectl describe pod -l app=picas-fijas   # ver errores (por ejemplo imagen no encontrada)
kubectl logs deploy/picas-fijas           # ver los logs de la aplicación
kubectl delete -f k8s.yaml                # borrar todo y volver a empezar
```

Si el pod queda en `ImagePullBackOff`, casi siempre es el nombre de la imagen mal escrito en `k8s.yaml` o la imagen privada en Docker Hub (debe ser pública).

## Prueba manual de una partida con curl

```bash
curl -X POST localhost:3000/login -H 'Content-Type: application/json' -d '{"nombre":"ana"}'
curl -X POST localhost:3000/login -H 'Content-Type: application/json' -d '{"nombre":"luis"}'
curl -X POST localhost:3000/juego -H 'Content-Type: application/json' -d '{"nombre":"ana","numero":"4271"}'
curl -X PUT  localhost:3000/juego/1 -H 'Content-Type: application/json' -d '{"nombre":"luis","numero":"5678"}'
curl localhost:3000/juego/1     # ver de quién es el turno
curl -X POST localhost:3000/juego/1/jugar -H 'Content-Type: application/json' -d '{"nombre":"ana","numero":"1234"}'
```
