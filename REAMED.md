#   Medios Magnéticos

Este proyecto automatiza el proceso de Medios Magnéticos. La automatización implica la conversión de datos desde archivos Excel a archivos de texto (`.txt`) con un formato específico, aplicando reglas de transformación. 

El proyecto se compone de dos partes principales:

1.  **Script de Transformación de Datos (Python):** Un script en Python que toma un archivo Excel como entrada, transforma los datos de acuerdo con reglas predefinidas, y genera un archivo `.txt` como salida. 
2.  **Módulo de Integración con Odoo 16:** Un módulo de Odoo 16 que proporciona una interfaz de usuario para cargar archivos Excel, disparar la transformación de datos (utilizando el script de Python), y descargar el archivo `.txt` resultante. 

El objetivo final es optimizar el flujo de trabajo, reducir errores manuales y aumentar la eficiencia en el manejo de la información financiera. 

#   Tecnologías Utilizadas

* **Contenedorización:** Docker se utiliza para empaquetar la aplicación Odoo 16 y la base de datos PostgreSQL, asegurando la portabilidad y consistencia del entorno.
* **Base de Datos:** PostgreSQL es el sistema de gestión de base de datos relacional utilizado para almacenar los datos de Odoo.
* **Lenguaje de Programación:** Python 3 se utiliza para desarrollar el script de transformación de datos.
* **Librerías de Python:**
    * `pandas`: Para la manipulación y análisis de datos, especialmente para leer y procesar los archivos Excel.
    * `json`: Para trabajar con datos en formato JSON (aunque no se especifica un uso extensivo de JSON en el documento, podría ser útil para la configuración o el manejo de reglas). [cite: 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    * `numpy`: Para operaciones numéricas eficientes, especialmente si se requiere un manejo avanzado de los datos en la columna "VALOR".
    * `abc`: Para trabajar con clases abstractas (su uso específico dependerá del diseño del script, pero podría utilizarse para definir una interfaz para los transformadores de datos).
* **ERP:** Odoo 16 es el sistema de planificación de recursos empresariales (ERP) donde se integra la funcionalidad. [cite: 19, 20, 21, 22, 23]

#   Entorno y Configuración

Para la correcta ejecución del proyecto, se definen las siguientes variables de entorno:

* `POSTGRES_USER=mi_usuario_db`
* `POSTGRES_PASSWORD=mi_contraseña_segura`
* `POSTGRES_DB=mi_basededatos`
* `POSTGRES_PORT=5432`
* `ODOO_ADMIN_PASSWORD=mi_contraseña_admin_odoo`
* `ODOO_PORT=8069`

Estas variables son cruciales para la configuración de la conexión a la base de datos PostgreSQL y la configuración de la instancia de Odoo.

#   Instalación y Dependencias

1.  **Instalación de Docker y Docker Compose:** (No se especifica en el documento, pero es esencial para el entorno descrito)
    * Descargar e instalar Docker Desktop (para Windows y macOS) o Docker Engine y Docker Compose (para Linux) desde la página oficial de Docker.
2.  **Instalación de Python 3:** (Asumido como requisito previo)
    * Asegurarse de tener Python 3 instalado en el sistema.
3.  **Creación de un Entorno Virtual (Recomendado):**
    * Crear un entorno virtual para el proyecto Python para aislar las dependencias:

        ```bash
        python3 -m venv venv
        source venv/bin/activate # En Linux/macOS
        venv\Scripts\activate # En Windows
        ```

4.  **Instalación de Dependencias de Python:**
    * Utilizar el archivo `requirements.txt` para instalar las librerías necesarias:

        ```bash
        pip install -r requirements.txt
        ```
    * (Asumiendo que `requirements.txt` contiene: `pandas`, `numpy`, `json`)
5.  **Instalación y Configuración de Odoo 16:**
    * Si se opta por la instalación manual (alternativa a Docker), descargar Odoo 16 desde el enlace proporcionado en el documento. [cite: 25]
    * Configurar Odoo para conectarse a la base de datos PostgreSQL utilizando las variables de entorno.
6.  **Configuración de PostgreSQL:**
    * Asegurarse de que PostgreSQL esté instalado y configurado, ya sea directamente o a través de Docker.
    * Crear la base de datos y el usuario con los permisos adecuados para que Odoo pueda acceder a ella.

#   Consideraciones Adicionales

* **URLs y Documentación:** Es importante documentar claramente las URLs de acceso a Odoo, las rutas de los archivos, y cualquier otra información relevante para la configuración y el uso de la aplicación.
* **Manejo de Errores:** Implementar un manejo robusto de errores tanto en el script de Python como en el módulo de Odoo para asegurar la estabilidad y la facilidad de depuración. 
* **Seguridad:** Considerar las implicaciones de seguridad, especialmente en el manejo de las contraseñas y la conexión a la base de datos.
* **Escalabilidad:** Diseñar la solución teniendo en cuenta la posible escalabilidad futura, especialmente si se prevé un aumento en el volumen de datos o el número de usuarios.