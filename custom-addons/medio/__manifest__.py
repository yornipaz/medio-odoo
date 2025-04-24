# -*- coding: utf-8 -*-
{
    "name": "medio",
    "version": "1.0",
    "description": "Modulo automatizar el proceso interno llamado Medios Magnéticos, el cual consiste en generar un archivo .txt con un formato específico de acuerdo con un grupo de condiciones dadas para cada uno de los valores que vienen desde un archivo Excel.",
    "author": "Yorni Bonilla",
    "category": "Tools",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/excel_to_txt_views.xml",
    ],
    "installable": True,
    "application": True,
}
