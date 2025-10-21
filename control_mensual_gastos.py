import streamlit as st
from connection_db import get_db_connection
import pandas as pd
from sqlalchemy import text
from datetime import datetime

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

    # 1. Obtener el mes y año actuales
    fecha_actual = datetime.now()
    anio_actual = fecha_actual.year
    mes_actual_num = fecha_actual.month

    # 2. Preparar las opciones para los selectores
    col_mes, col_anio, _ = st.columns([1, 1, 2])
    
    meses_espanol = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    anios_disponibles = list(range(anio_actual - 2, anio_actual + 3))

    # 3. Usar el mes y año actuales para establecer el índice por defecto
    mes_seleccionado_str = col_mes.selectbox(
        "Mes", 
        options=meses_espanol, 
        index=mes_actual_num - 1  # El índice de la lista empieza en 0
    )
    anio_seleccionado = col_anio.selectbox(
        "Año", 
        options=anios_disponibles,
        index=anios_disponibles.index(anio_actual) # Encontrar la posición del año actual
    )

    # El resto del código funciona exactamente igual que antes
    mes_seleccionado_num = meses_espanol.index(mes_seleccionado_str) + 1
    inicio_mes = pd.Timestamp(f'{anio_seleccionado}-{mes_seleccionado_num}-01')
    fin_mes = inicio_mes + pd.DateOffset(months=1)

    st.info(f"Mostrando gastos con vencimiento entre el {inicio_mes.strftime('%d de %B %Y')} y el {(fin_mes - pd.Timedelta(days=1)).strftime('%d de %B %Y')}")

    cuotas_sin_pagar = conn.query("""
        SELECT tbc.idcuota, tbc.fecha_vencimiento, tbc.monto,tbc.numero_cuota,tbt.fecha,tbu.apodo,ccg.nombre AS categoria,ccg.tipo AS tipo_categoria,
                 ct.idtarjeta,ct.nombre AS tarjeta,tbt.descripcion, tbt.detalle,tbt.monto_total, tbt.meses_total,tbc.pagado
        FROM tbl_cuotas tbc
        JOIN tbl_transacciones tbt USING (idtransaccion)
        JOIN tbl_usuarios tbu USING (idusuario)
        JOIN cat_tarjetas ct USING (idtarjeta)
        JOIN cat_categoriagasto ccg USING (idcategoriagasto)
        WHERE tbt.idusuario = :id_usuario AND (tbc.pagado = False OR (tbc.fecha_pago >= :inicio_mes AND tbc.fecha_pago < :fin_mes))
        ORDER BY tbt.fecha ASC
    """, params={"id_usuario": id_usuario,"inicio_mes": inicio_mes, "fin_mes": fin_mes}, ttl=0)

    # 2. Define el mapa de reemplazo
    mapa_estado = {True: 'Pagado ✅', False: 'Pendiente ❌'}
    cuotas_sin_pagar['pagado_string'] = cuotas_sin_pagar['pagado'].map(mapa_estado)

    cuotas_variables = cuotas_sin_pagar[cuotas_sin_pagar['tipo_categoria'] == 'Variable']
    cuotas_fijas = cuotas_sin_pagar[cuotas_sin_pagar['tipo_categoria'] == 'Fijo']


    suma_gastos_variables = cuotas_variables['monto'].sum()
    suma_gastos_fijos = cuotas_fijas['monto'].sum()

    col5, col6,col7,col8 = st.columns(4)
    col5.metric("Suma Gastos Fijos del Mes", f"${suma_gastos_fijos:,.2f}")
    col6.metric("Disponible Gasto Fijo del Mes", f"${valor_gasto_fijo_mensual - suma_gastos_fijos:,.2f}")
    col7.metric("Suma Gastos Variables del Mes", f"${suma_gastos_variables:,.2f}")
    col8.metric("Disponible Gasto Variable del Mes", f"${valor_gasto_variable_mensual - suma_gastos_variables:,.2f}")

    #df_usuarios = usuarios.rename(columns={"idusuario": "ID Usuario", "apodo": "Apodo","ingreso_mensual":"Ingreso Mensual"}).style.format({"Ingreso Mensual": "${:,.2f}"})

    st.subheader("Detalles de Gastos del Usuario")

    tab1, tab2 = st.tabs(["Gastos Fijos","Gastos Variables"])

    with tab1:
        column_config = {
            "idcuota": st.column_config.NumberColumn("ID", disabled=True),
            "fecha_vencimiento": "Fecha Límite de Pago",
            "numero_cuota": "Mensualidad Nº",
            "monto": st.column_config.NumberColumn("Monto"), # Formato de moneda aquí
            "fecha": "Fecha de Transacción",
            "apodo": None,  # Ocultar la columna de apodo
            "categoria": "Categoría",
            "tarjeta": st.column_config.TextColumn("Tarjeta", width="small"), # Ajuste de ancho aquí
            "descripcion": "Descripción Compra",
            "detalle": st.column_config.TextColumn("Detalle Adicional", width="medium"), # Ajuste de ancho aquí
            "monto_total": st.column_config.NumberColumn("Monto Total Transacción"), # Formato de moneda aquí
            "meses_total": "Total Meses",
            "idtarjeta": None, # Ocultar la columna de ID de tarjeta
            "tipo_categoria": None, # Ocultar la columna de tipo de categoría
            "pagado_string": "Estado de Pago",
            "pagado": None # Ocultar la columna de pagado
        }
        st.dataframe(
            cuotas_fijas.style.format({"monto": "${:,.2f}", "monto_total": "${:,.2f}"}, na_rep="-"),  # Pasamos el DataFrame de datos puros
            column_config=column_config,
            hide_index=True,
            width='stretch',
            height=600,
        )
 
    with tab2:
        column_config = {
            "idcuota": st.column_config.NumberColumn("ID", disabled=True),
            "fecha_vencimiento": "Fecha Límite de Pago",
            "numero_cuota": "Mensualidad Nº",
            "monto": st.column_config.NumberColumn("Monto"), # Formato de moneda aquí
            "fecha": "Fecha de Transacción",
            "apodo": None,  # Ocultar la columna de apodo
            "categoria": "Categoría",
            "tarjeta": st.column_config.TextColumn("Tarjeta", width="small"), # Ajuste de ancho aquí
            "descripcion": "Descripción Compra",
            "detalle": st.column_config.TextColumn("Detalle Adicional", width="medium"), # Ajuste de ancho aquí
            "monto_total": st.column_config.NumberColumn("Monto Total Transacción"), # Formato de moneda aquí
            "meses_total": "Total Meses",
            "idtarjeta": None, # Ocultar la columna de ID de tarjeta
            "tipo_categoria": None, # Ocultar la columna de tipo de categoría
            "pagado_string": "Estado de Pago",
            "pagado": None # Ocultar la columna de pagado
        }
        st.dataframe(
            cuotas_variables.style.format({"monto": "${:,.2f}", "monto_total": "${:,.2f}"}, na_rep="-"),  # Pasamos el DataFrame de datos puros
            column_config=column_config,
            hide_index=True,
            width='stretch',
            height=600,
        )
