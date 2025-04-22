import sys
import pandas as pd
import json
import numpy as np 
from abc import ABC, abstractmethod
from typing import List, Optional

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
        print(f"Error al leer el archivo: {e}")
        return None
    
def leer_json(url ):
    """
    Lee el archivo JSON desde la URL proporcionada.

    Args:
        url (str): URL del archivo JSON.

    Returns:
        dict: Diccionario con los datos del JSON.
    """
    try:
        with open(url, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None
def generar_txt(df,ruta):
    """
    Genera un archivo de texto a partir de un DataFrame.

    Args:
        df (pandas.DataFrame): DataFrame a convertir.
        ruta (str): Ruta donde se guardará el archivo de texto.
    """
    try:
        with open(ruta, 'w') as file:
            for index, row in df.iterrows():
                file.write(f"{row.to_json()}\n")
        print(f"Archivo generado en: {ruta}")
    except Exception as e:
        print(f"Error al generar el archivo: {e}")

class ExcelTransformer:
    def __init__(self,  reglas_path="data/reglas.json"):
        self.reglas = self.cargar_reglas(reglas_path)
        self.columnas_a_transformar = [regla["nombre"] for regla in self.reglas]

    def cargar_reglas(self, reglas_path):
        try:
            with open(reglas_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo de reglas en: {reglas_path}")
            sys.exit(1)
    def transformar_anio(self, df):
        if "ANIO" in df.columns:
            try:
                df["ANIO"] = df["ANIO"].astype(int).astype(str).str.zfill(4)
            except (ValueError, TypeError):
                pass
        return df

    def transformar_concepto(self, df):
        if "CONCEPTO" in df.columns:
            df["CONCEPTO"] = df["CONCEPTO"].astype(str).str[:10].str.ljust(10, '$')
        return df

    def transformar_valor(self, df):
        if "VALOR" in df.columns:
            try:
                if pd.isna(df["VALOR"]).any():
                    df["VALOR"] = df["VALOR"].replace(np.nan, '')
                df["VALOR"] = df["VALOR"].astype(int).astype(str).str.zfill(20)
            except (ValueError, TypeError):
                pass
        return df

    def transformar_dataframe(self, df):
        # Crear un nuevo DataFrame con solo las columnas a transformar
        df_transformado = df[self.columnas_a_transformar].copy()

        df_transformado = self.transformar_anio(df_transformado)
        df_transformado = self.transformar_concepto(df_transformado)
        df_transformado = self.transformar_valor(df_transformado)

        return df_transformado.astype(str).replace({np.nan: ''}, regex=False)

    def process_excel_to_txt(self, excel_path, txt_path):
        try:
            df = pd.read_excel(excel_path)

            print("Tipos de datos antes de la transformación:")
            print(df.dtypes)

            # Filtrar el DataFrame original para incluir solo las columnas a transformar
            df = df[self.columnas_a_transformar].copy()

            df = self.transformar_dataframe(df)

            print("\nTipos de datos después de la transformación:")
            print(df)
            # Convertir a string y eliminar espacios
            df_string = df.to_string(index=False, header=False)
            df_string = df_string.replace(' ', '')
            df_string = df_string.replace('\n', ' ')
            df_string = df_string.replace('  ', ' ')
            print("\nDataFrame transformado:")
            print(df_string)
          

            with open(txt_path, 'w') as f:
                f.write(df_string)

            print(f"Archivo .txt generado exitosamente en: {txt_path}")

        except FileNotFoundError:
            print(f"Error: No se encontró el archivo Excel en: {excel_path}")
        except Exception as e:
            print(f"Ocurrió un error: {e}")
            print(e)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python medio.py <ruta_del_excel> <ruta_del_txt>")
    else:
        excel_path = sys.argv[1]
        txt_path = sys.argv[2]
        reglas_path = 'data/reglas.json'
        reglas = leer_json(reglas_path)
        if reglas is None:
            print("Error al cargar las reglas.")
            sys.exit(1)
        transformer = ExcelTransformer()
        transformer.process_excel_to_txt(excel_path, txt_path)