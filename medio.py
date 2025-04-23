import sys
import pandas as pd
import json
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Optional


class Transformacion(ABC):
    @abstractmethod
    def transformar(self, df, columna_nombre, regla):
        pass


class TransformacionAnio(Transformacion):
    def transformar(self, df, columna_nombre, regla):
        if columna_nombre in df.columns:
            try:
                df[columna_nombre] = df[columna_nombre].astype(
                    int).astype(str).str.zfill(regla["TAMANO"])
            except (ValueError, TypeError):
                return None
        return df


class TransformacionConcepto(Transformacion):
    def transformar(self, df, columna_nombre, regla):
        if columna_nombre in df.columns:
            df[columna_nombre] = df[columna_nombre].astype(str).str[:regla["TAMANO"]].str.ljust(regla["TAMANO"], '$')
        return df


class TransformacionValor(Transformacion):
    def transformar(self, df, columna_nombre, regla):
        if columna_nombre in df.columns:
            try:
                if pd.isna(df[columna_nombre]).any():
                    df[columna_nombre] = df[columna_nombre].replace(np.nan, '')
                df[columna_nombre] = df[columna_nombre].astype(
                    int).astype(str).str.zfill(regla["TAMANO"])
            except (ValueError, TypeError):
                return None
        return df


class TransformacionFactory:
    def crear_transformacion(self, nombre_columna):
        if nombre_columna == "ANIO":
            return TransformacionAnio()
        elif nombre_columna == "CONCEPTO":
            return TransformacionConcepto()
        elif nombre_columna == "VALOR":
            return TransformacionValor()
        else:
            raise ValueError(
                f"Tipo de transformación desconocido: {nombre_columna}")


class ExcelTransformer:
    def __init__(self, reglas: List[dict], transformacion_factory: TransformacionFactory, columnas_a_transformar: Optional[List[str]] = None):
        self.reglas = reglas
        self.transformacion_factory = transformacion_factory
        self.columnas_a_transformar = columnas_a_transformar if columnas_a_transformar else [
            regla["nombre"] for regla in self.reglas]

    def transformar_dataframe(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        df_transformado = df[self.columnas_a_transformar].copy()

        for regla in self.reglas:
            nombre_columna = regla["nombre"]
            if nombre_columna in self.columnas_a_transformar:
                transformacion = self.transformacion_factory.crear_transformacion(
                    nombre_columna)
                if transformacion:
                    resultado = transformacion.transformar(
                        df_transformado, nombre_columna, regla)
                    if resultado is None:
                        return None
                    df_transformado = resultado

        return df_transformado.astype(str).replace({np.nan: ''}, regex=False)


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
        return e


def leer_json(url):
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
    df_string = df_string.replace('  ', ' ')
    print("\nDataFrame transformado:")
    print(df_string)

    with open(ruta, 'w') as f:
        f.write(df_string)

    print(f"Archivo .txt generado exitosamente en: {ruta}")


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

        try:
            df = leer_excel(excel_path)
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
        except Exception as e:
            print(
                f"Error durante la transformación o generación del archivo: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error al leer el archivo Excel: {e}")
            sys.exit(1)