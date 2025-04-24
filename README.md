# Proyecto Medios Magnéticos Odoo 16

Este sistema automatiza el proceso de generación de **Medios Magnéticos** requerido por el área financiera. Permite cargar un archivo Excel con columnas específicas y transformarlo en un archivo `.txt` siguiendo un conjunto de reglas estrictas. La solución está compuesta por un **script Python** y un **módulo de integración con Odoo 16**, facilitando el manejo de la información directamente desde una interfaz gráfica.

## Tabla de Contenido

- [Descripción](#descripción)
- [Funcionalidades Principales](#funcionalidades-principales)
- [Prerequisitos](#prerequisitos)
- [¿Cómo iniciar?](#cómo-iniciar)
- [Trabajando con contenedores](#trabajando-con-contenedores)
  - [Dockerizado](#dockerizado)
  - [Docker compose](#docker-compose)
- [Variables de entorno](#variables-de-entorno)
- [Sistema de archivos](#sistema-de-archivos)

## Descripción

El sistema está diseñado para:

- Transformar datos de archivos Excel en archivos `.txt` según reglas de formato.
- Integrar esta transformación dentro de una interfaz en Odoo 16.
- Descargar automáticamente el archivo `.txt` resultante desde el ERP.

## Funcionalidades Principales

- **Script Python (`medio.py`)**:
  - Recibe una URL local del archivo Excel.
  - Aplica reglas de transformación:
    - ANIO: cuatro dígitos, completado con ceros a la izquierda.
    - CONCEPTO: máximo 10 caracteres, completado con `$`.
    - VALOR: hasta 20 dígitos, completado con ceros a la izquierda.
  - Genera un `.txt` con el formato correcto.
- **Módulo Odoo 16**:
  - Interfaz para cargar archivo Excel.
  - Botón para transformar y descargar archivo `.txt`.

## Prerequisitos

| Nombre                  | Descripción                                     | Versión   |
| ----------------------- | ----------------------------------------------- | --------- |
| Python                  | Para ejecutar el script de transformación       | `>=3`     |
| Docker / Docker Compose | Para levantar Odoo y PostgreSQL en contenedores | `v23.0.1` |
| Odoo 16                 | ERP donde se integra el módulo                  | `v16`     |

## ¿Cómo iniciar?

1. Clona el repositorio:

   > https://github.com/yornipaz/medio-odoo

2. Crea y activa un entorno virtual:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows

   ```

3. Instala dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Ejecuta el script:

   ```bash
   python medio.py <ruta_del_excel> <ruta_del_txt>
   ```

5. Para trabajar con la interfaz Odoo, continúa con la sección de contenedores.

## Trabajando con contenedores

### Dockerizado

El proyecto se ejecuta con Docker Compose. Se incluyen dos servicios:

- **db**: Contenedor de PostgreSQL
- **odoo**: Contenedor con Odoo 16 y módulo personalizado

### Docker Compose

1.  Crea un archivo .env a partir de .env.example y configura las siguientes variables:

    ```bash
    POSTGRES_DB=postgres
    POSTGRES_PASSWORD=odoo16
    POSTGRES_USER=odoo16
    PGDATA=/var/lib/pgsql/data/pgdata

    HOST=postgres
    USER=odoo16
    PASSWORD=odoo16

    ```

2.  Levanta los contenedores:

    ```bash
        docker compose up --build

    ```

3.  Accede a Odoo en `http://localhost:8069`.

4.  Instala el módulo desde Apps.

## Variables de entorno

Estas variables son utilizadas en los contenedores y deben estar definidas en un archivo .env en la raíz del proyecto:

```bash
POSTGRES_DB=XXXXX
POSTGRES_PASSWORD=XXXXXX
POSTGRES_USER=XXXXXXXX
PGDATA=/var/lib/pgsql/data/pgdata
HOST=XXXXXX
USER=XXXXXXX
PASSWORD=XXXXX
```

## Sistema de archivos

Estructura del proyecto:

- `/medio.py`: Script que transforma el archivo Excel.

- `/requirements.txt`: Dependencias de Python .

- `/custom-addons/`: Carpeta donde se encuentra el módulo personalizado de Odoo.

- `/docker-compose.yml`: Archivo para levantar el entorno con Docker.

- `/config/`: Archivos de configuración de Odoo.

- `/README.md`: Documentación del proyecto.
