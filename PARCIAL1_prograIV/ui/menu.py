import os
from api.consultas import (
    cargar_datos, obtener_opciones, consultar, COLUMNAS, formatear_numero
)


def _leer_opcion(etiqueta, opciones):
    """Solicita una opción existente; admite escribir el valor completo."""
    if not opciones:
        raise ValueError(f"No hay opciones disponibles para {etiqueta.lower()}.")
    print(f"\n{etiqueta} disponibles:")
    for indice, opcion in enumerate(opciones, start=1):
        print(f"  {indice}. {opcion}")
    while True:
        entrada = input(f"Escriba el número o el nombre de {etiqueta.lower()}: ").strip()
        if entrada.isdigit():
            indice = int(entrada)
            if 1 <= indice <= len(opciones):
                return opciones[indice - 1]
        for opcion in opciones:
            if entrada.casefold() == opcion.casefold():
                return opcion
        print("Opción no válida. Intente nuevamente.")


def _leer_cantidad():
    while True:
        entrada = input("\nNúmero de registros a consultar: ").strip()
        try:
            cantidad = int(entrada)
            if cantidad > 0:
                return cantidad
        except ValueError:
            pass
        print("Ingrese un número entero mayor que cero.")


def _imprimir_tabla(registros, medianas):
    """Muestra los registros consultados y las medianas calculadas."""
    columnas = [
        ("Departamento", COLUMNAS["departamento"]),
        ("Municipio", COLUMNAS["municipio"]),
        ("Cultivo", COLUMNAS["cultivo"]),
        ("Topografía", COLUMNAS["topografia"]),
    ]
    filas = []
    for _, registro in registros.iterrows():
        filas.append([str(registro[col] or "Sin dato") for _, col in columnas])

    encabezados = [nombre for nombre, _ in columnas]
    anchos = [len(h) for h in encabezados]
    for fila in filas:
        for i, celda in enumerate(fila):
            anchos[i] = min(max(anchos[i], len(celda)), 28)

    def recortar(texto, ancho):
        texto = str(texto)
        return texto if len(texto) <= ancho else texto[:ancho - 1] + "…"

    separador = "+-" + "-+-".join("-" * ancho for ancho in anchos) + "-+"
    print("\nREGISTROS ENCONTRADOS")
    print(separador)
    print("| " + " | ".join(recortar(h, anchos[i]).ljust(anchos[i])
                             for i, h in enumerate(encabezados)) + " |")
    print(separador)
    for fila in filas:
        print("| " + " | ".join(recortar(v, anchos[i]).ljust(anchos[i])
                                 for i, v in enumerate(fila)) + " |")
    print(separador)

    print("\nMEDIANAS DE LAS VARIABLES EDÁFICAS")
    print(f"  pH:       {formatear_numero(medianas['ph'])}")
    print(f"  Fósforo P: {formatear_numero(medianas['fosforo'])} mg/kg")
    print(f"  Potasio K: {formatear_numero(medianas['potasio'])} cmol(+)/kg")
    print(f"\nRegistros usados para calcular las medianas: {len(registros)}")


def ejecutar_aplicacion():
    print("=" * 62)
    print(" CONSULTA DE ANÁLISIS DE LABORATORIO DE SUELOS EN COLOMBIA")
    print("=" * 62)
    try:
        datos = cargar_datos()
        print(f"Archivo cargado correctamente: {len(datos):,} registros disponibles.")
        departamentos = obtener_opciones(datos, "departamento")
        departamento = _leer_opcion("Departamento", departamentos)
        municipios = obtener_opciones(datos, "municipio", departamento=departamento)
        municipio = _leer_opcion("Municipio", municipios)
        cultivos = obtener_opciones(datos, "cultivo", departamento=departamento, municipio=municipio)
        cultivo = _leer_opcion("Cultivo", cultivos)
        cantidad = _leer_cantidad()

        registros, medianas = consultar(datos, departamento, municipio, cultivo, cantidad)
        if registros.empty:
            print("\nNo se encontraron registros para los criterios seleccionados.")
            return
        _imprimir_tabla(registros, medianas)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"\nERROR: {error}")
        print("Revise que el archivo Excel esté en la carpeta principal y vuelva a ejecutar.")
    except KeyboardInterrupt:
        print("\n\nConsulta cancelada por el usuario.")


if __name__ == "__main__":
    ejecutar_aplicacion()
