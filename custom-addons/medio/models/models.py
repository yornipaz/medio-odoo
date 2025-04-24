# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
# import base64
# from odoo.exceptions import UserError
# import pandas as pd
# import json
# import numpy as np
# from abc import ABC, abstractmethod
# from typing import List, Optional
# import io
# import os


# class Transformacion(ABC):
#     @abstractmethod
#     def transformar(self, df, columna_nombre, regla):
#         pass


# class TransformacionAnio(Transformacion):
#     def transformar(self, df, columna_nombre, regla):
#         if columna_nombre in df.columns:
#             try:
#                 df[columna_nombre] = (
#                     df[columna_nombre]
#                     .astype(int)
#                     .astype(str)
#                     .str.zfill(regla["TAMANO"])
#                 )
#             except (ValueError, TypeError):
#                 return None
#         return df


# class TransformacionConcepto(Transformacion):
#     def transformar(self, df, columna_nombre, regla):
#         if columna_nombre in df.columns:
#             df[columna_nombre] = (
#                 df[columna_nombre]
#                 .astype(str)
#                 .str[: regla["TAMANO"]]
#                 .str.ljust(regla["TAMANO"], "$")
#             )
#         return df


# class TransformacionValor(Transformacion):
#     def transformar(self, df, columna_nombre, regla):
#         if columna_nombre in df.columns:
#             try:
#                 if pd.isna(df[columna_nombre]).any():
#                     df[columna_nombre] = df[columna_nombre].replace(np.nan, "")
#                 df[columna_nombre] = (
#                     df[columna_nombre]
#                     .astype(int)
#                     .astype(str)
#                     .str.zfill(regla["TAMANO"])
#                 )
#             except (ValueError, TypeError):
#                 return None
#         return df


# class TransformacionFactory:
#     def crear_transformacion(self, nombre_columna):
#         if nombre_columna == "ANIO":
#             return TransformacionAnio()
#         elif nombre_columna == "CONCEPTO":
#             return TransformacionConcepto()
#         elif nombre_columna == "VALOR":
#             return TransformacionValor()
#         else:
#             raise ValueError(f"Tipo de transformación desconocido: {nombre_columna}")


# class ExcelTransformer:
#     def __init__(
#         self,
#         reglas: List[dict],
#         transformacion_factory: TransformacionFactory,
#         columnas_a_transformar: Optional[List[str]] = None,
#     ):
#         self.reglas = reglas
#         self.transformacion_factory = transformacion_factory
#         self.columnas_a_transformar = (
#             columnas_a_transformar
#             if columnas_a_transformar
#             else [regla["nombre"] for regla in self.reglas]
#         )

#     def transformar_dataframe(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
#         df_transformado = df[self.columnas_a_transformar].copy()

#         for regla in self.reglas:
#             nombre_columna = regla["nombre"]
#             if nombre_columna in self.columnas_a_transformar:
#                 transformacion = self.transformacion_factory.crear_transformacion(
#                     nombre_columna
#                 )
#                 if transformacion:
#                     resultado = transformacion.transformar(
#                         df_transformado, nombre_columna, regla
#                     )
#                     if resultado is None:
#                         return None
#                     df_transformado = resultado

#         return df_transformado.astype(str).replace({np.nan: ""}, regex=False)


# class medio(models.TransientModel):
#     _name = "medio.excel_to_txt"
#     _description = "Wizard to Convert Excel to TXT"
#     excel_file = fields.Binary(string="Archivo Excel", required=True)
#     excel_filename = fields.Char(string="Nombre del Archivo Excel")
#     txt_file = fields.Binary(string="Archivo TXT", readonly=True)
#     txt_filename = fields.Char(string="Nombre del Archivo TXT", readonly=True)

#     def _get_reglas_path(self):
#         """Devuelve la ruta absoluta al archivo de reglas JSON."""
#         return os.path.join(
#             os.path.dirname(os.path.abspath(__file__)), "..", "data", "reglas.json"
#         )

#     def _get_reglas(self):
#         """Lee las reglas de transformación desde el archivo JSON."""
#         try:
#             reglas_path = self._get_reglas_path()
#             with open(reglas_path, "r") as f:
#                 reglas_data = json.load(f)
#             return reglas_data
#         except FileNotFoundError:
#             raise UserError(
#                 f"No se encontró el archivo de reglas en: {self._get_reglas_path()}"
#             )
#         except json.JSONDecodeError:
#             raise UserError(f"Error al decodificar el archivo JSON de reglas.")
#         except Exception as e:
#             raise UserError(f"Ocurrió un error al leer el archivo de reglas: {e}")

#     def transform_excel(self):
#         self.ensure_one()
#         if not self.excel_file:
#             raise UserError("Por favor, selecciona un archivo Excel.")

#         try:
#             excel_content = base64.b64decode(self.excel_file)
#             df = pd.read_excel(io.BytesIO(excel_content), engine="openpyxl")

#             reglas = self._get_reglas()
#             factory = TransformacionFactory()
#             # Las columnas a transformar se obtienen dinámicamente de las reglas
#             columnas_a_transformar = [regla["nombre"] for regla in reglas]
#             transformer = ExcelTransformer(reglas, factory, columnas_a_transformar)
#             df_transformado = transformer.transformar_dataframe(df.copy())

#             if df_transformado is not None:
#                 txt_content = df_transformado.to_string(index=False, header=False)
#                 txt_content = txt_content.replace(" ", "")
#                 txt_content = txt_content.replace("\n", " ")
#                 txt_content = txt_content.replace(
#                     "\xa0", " "
#                 )  # Handle non-breaking spaces

#                 self.txt_file = base64.b64encode(txt_content.encode("utf-8"))
#                 self.txt_filename = "transformado.txt"

#                 return {
#                     "type": "ir.actions.act_url",
#                     "url": "/web/content?model=excel.to.txt.wizard&id=%s&field=txt_file&download=true&filename=%s"
#                     % (self.id, self.txt_filename),
#                     "target": "self",
#                 }
#             else:
#                 raise UserError("Error durante la transformación del archivo Excel.")

#         except Exception as e:
#             raise UserError(f"Ocurrió un error durante la transformación: {e}") from e
