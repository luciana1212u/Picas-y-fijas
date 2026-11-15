# Imagen oficial y liviana de Python
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Instalar Flask (única dependencia)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación (app.py, static/)
COPY . .

# Puerto que usa la aplicación
EXPOSE 3000

# Ejecutar como usuario sin privilegios
USER nobody

# Iniciar la aplicación
CMD ["python", "app.py"]
