import streamlit as st
from connection_db import get_db_connection
import pandas as pd
from sqlalchemy import text

def control_mensual():
    st.header("Control Mensual de Gastos")

    conn = get_db_connection()

    usuarios = conn.query("SELECT idusuario, apodo,ingreso_mensual FROM tbl_usuarios WHERE idusuario in (1,2) ORDER BY idusuario", ttl=0)
    usuarios_list = {row.apodo: row.idusuario for row in usuarios.itertuples(index=False)}
    usuario_seleccionado = st.selectbox("Usuario", options=list(usuarios_list.keys()))

    id_usuario = usuarios_list[usuario_seleccionado]
    usuario_actual = usuarios[usuarios['idusuario'] == id_usuario]

    valor_ingreso_mensual = usuario_actual["ingreso_mensual"].item()
    valor_gasto_fijo_mensual = valor_ingreso_mensual * 0.5
    valor_gasto_variable_mensual = valor_ingreso_mensual * 0.3
    valor_ahorro_mensual = valor_ingreso_mensual * 0.2

    st.subheader("Desglose Ingreso del Usuario")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingreso mensual", f"${valor_ingreso_mensual:,.2f}" if pd.notna(valor_ingreso_mensual) else "No definido")
    col2.metric("Gasto fijo mensual recomendado (50%)", f"${valor_gasto_fijo_mensual:,.2f}" if pd.notna(valor_ingreso_mensual) else "No definido")
    col3.metric("Gasto variable mensual recomendado (30%)", f"${valor_gasto_variable_mensual:,.2f}" if pd.notna(valor_ingreso_mensual) else "No definido")
    col4.metric("Ahorro mensual recomendado (20%)", f"${valor_ahorro_mensual:,.2f}" if pd.notna(valor_ingreso_mensual) else "No definido")

    st.subheader("Resumen de Gastos del Usuario")

    cuotas_sin_pagar = conn.query("""
        SELECT tbc.idcuota, tbc.fecha_vencimiento, tbc.monto,tbc.numero_cuota,tbt.fecha,tbu.apodo,ccg.nombre AS categoria,ccg.tipo AS tipo_categoria,
                 ct.idtarjeta,ct.nombre AS tarjeta,tbt.descripcion, tbt.detalle,tbt.monto_total, tbt.meses_total
        FROM tbl_cuotas tbc
        JOIN tbl_transacciones tbt USING (idtransaccion)
        JOIN tbl_usuarios tbu USING (idusuario)
        JOIN cat_tarjetas ct USING (idtarjeta)
        JOIN cat_categoriagasto ccg USING (idcategoriagasto)
        WHERE tbc.pagado = FALSE AND tbt.idusuario = :id_usuario
        ORDER BY tbc.fecha_vencimiento ASC
    """, params={"id_usuario": id_usuario}, ttl=0)

    cuotas_variables = cuotas_sin_pagar[cuotas_sin_pagar['tipo_categoria'] == 'Variable']
    cuotas_fijas = cuotas_sin_pagar[cuotas_sin_pagar['tipo_categoria'] == 'Fijo']

    suma_gastos_variables = cuotas_variables['monto'].sum()
    suma_gastos_fijos = cuotas_fijas['monto'].sum()

    col5, col6,col7,col8 = st.columns(4)
    col5.metric("Suma Gastos Variables del Mes", f"${suma_gastos_variables:,.2f}")
    col6.metric("Disponible Gasto Variable del Mes", f"${valor_gasto_variable_mensual - suma_gastos_variables:,.2f}")
    col7.metric("Suma Gastos Fijos del Mes", f"${suma_gastos_fijos:,.2f}")
    col8.metric("Disponible Gasto Fijo del Mes", f"${valor_gasto_fijo_mensual - suma_gastos_fijos:,.2f}")

    #df_usuarios = usuarios.rename(columns={"idusuario": "ID Usuario", "apodo": "Apodo","ingreso_mensual":"Ingreso Mensual"}).style.format({"Ingreso Mensual": "${:,.2f}"})

    st.subheader("Detalles de Gastos del Usuario")

    tab1, tab2 = st.tabs(["Gastos Fijos","Gastos Variables"])

    with tab1:
        column_config = {
            "idcuota": st.column_config.NumberColumn("ID", disabled=True),
            "fecha_vencimiento": "Fecha Límite de Pago",
            "numero_cuota": "Mensualidad Nº",
            "monto": st.column_config.NumberColumn("Monto", format="$%.2f"), # Formato de moneda aquí
            "fecha": "Fecha de Transacción",
            "apodo": None,  # Ocultar la columna de apodo
            "categoria": "Categoría",
            "tarjeta": st.column_config.TextColumn("Tarjeta", width="small"), # Ajuste de ancho aquí
            "descripcion": "Descripción Compra",
            "detalle": st.column_config.TextColumn("Detalle Adicional", width="large"), # Ajuste de ancho aquí
            "monto_total": st.column_config.NumberColumn("Monto Total Transacción", format="$%.2f"), # Formato de moneda aquí
            "meses_total": "Total Meses",
            "idtarjeta": None, # Ocultar la columna de ID de tarjeta
            "tipo_categoria": None, # Ocultar la columna de tipo de categoría
        }
        st.dataframe(
            cuotas_fijas,  # Pasamos el DataFrame de datos puros
            column_config=column_config,
            hide_index=True,
            width='stretch',
        )

    with tab2:
        column_config = {
            "idcuota": st.column_config.NumberColumn("ID", disabled=True),
            "fecha_vencimiento": "Fecha Límite de Pago",
            "numero_cuota": "Mensualidad Nº",
            "monto": st.column_config.NumberColumn("Monto", format="$%.2f"), # Formato de moneda aquí
            "fecha": "Fecha de Transacción",
            "apodo": None,  # Ocultar la columna de apodo
            "categoria": "Categoría",
            "tarjeta": st.column_config.TextColumn("Tarjeta", width="small"), # Ajuste de ancho aquí
            "descripcion": "Descripción Compra",
            "detalle": st.column_config.TextColumn("Detalle Adicional", width="large"), # Ajuste de ancho aquí
            "monto_total": st.column_config.NumberColumn("Monto Total Transacción", format="$%.2f"), # Formato de moneda aquí
            "meses_total": "Total Meses",
            "idtarjeta": None, # Ocultar la columna de ID de tarjeta
            "tipo_categoria": None, # Ocultar la columna de tipo de categoría
        }
        st.dataframe(
            cuotas_variables,  # Pasamos el DataFrame de datos puros
            column_config=column_config,
            hide_index=True,
            width='stretch',
        )
