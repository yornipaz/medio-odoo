import sys
import pandas as pd
from transformaciones import TransformacionFactory, ExcelTransformer, leer_json


def leer_excel(url):
    """
    Lee el archivo Excel desde la URL proporcionada.

    Args:
        url (str): URL del archivo Excel.

    Returns:
        pandas.DataFrame: DataFrame con los datos del Excel.
    """
    try:
        df = pd.read_excel(url, engine='openpyxl')
        return df
    except Exception as e:
        print(f"Error al leer el archivo Excel: {e}")
        return None


def generar_txt(df, ruta):
    """
    Genera un archivo de texto a partir de un DataFrame.

    Args:
        df (pandas.DataFrame): DataFrame a convertir.
        ruta (str): Ruta donde se guardará el archivo de texto.
    """

    df_string = df.to_string(index=False, header=False)
    df_string = df_string.replace(' ', '')
    df_string = df_string.replace('\n', ' ')
    df_string = df_string.replace('\xa0', ' ')  # Para manejar caracteres de espacio no separables
    print("\nDataFrame transformado:")
    print(df_string)

    with open(ruta, 'w') as f:
        f.write(df_string)

    print(f"Archivo .txt generado exitosamente en: {ruta}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python main.py <ruta_del_excel> <ruta_del_txt>")
    else:
        excel_path = sys.argv[1]
        txt_path = sys.argv[2]
        reglas_path = 'data/reglas.json'
        reglas = leer_json(reglas_path)
        if reglas is None:
            print("Error al cargar las reglas.")
            sys.exit(1)

        try:
            df = leer_excel(excel_path)
            if df is not None:
                factory = TransformacionFactory()
                columnas_a_transformar = ["ANIO", "CONCEPTO", "VALOR"]
                transformer = ExcelTransformer(
                    reglas, factory, columnas_a_transformar)
                df_transformado = transformer.transformar_dataframe(df.copy())
                if df_transformado is not None:
                    generar_txt(df_transformado, txt_path)
                else:
                    print("Error en la transformación del DataFrame.")
                    sys.exit(1)
            else:
                sys.exit(1)
        except Exception as e:
            print(
                f"Error durante la transformación o generación del archivo: {e}")
            sys.exit(1)