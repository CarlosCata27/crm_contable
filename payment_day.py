import streamlit as st
from connection_db import get_db_connection
from datetime import date
import pandas as pd
from sqlalchemy import text

def set_payment_day():
    st.header("Registrar Pagos por Tarjetas")

    # Mostramos el mensaje de éxito si existe en la memoria
    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message
    
    # Se define la conexión una sola vez al principio.
    conn = get_db_connection()

    usuarios = conn.query("SELECT idusuario, apodo FROM tbl_usuarios ORDER BY idusuario",ttl=0)
    usuarios = {apodo: id_usuario for id_usuario, apodo in usuarios.itertuples(index=False)}

    usuario_seleccionado = st.selectbox("Usuario", options=list(usuarios.keys()))

    cuotas_sin_pagar = conn.query("""
        SELECT tbc.idcuota, tbc.fecha_vencimiento, tbc.monto,tbc.numero_cuota,tbt.fecha,tbu.apodo,ccg.nombre AS categoria,
                 ct.idtarjeta,ct.nombre AS tarjeta,tbt.descripcion, tbt.detalle,tbt.monto_total, tbt.meses_total
        FROM tbl_cuotas tbc
        JOIN tbl_transacciones tbt USING (idtransaccion)
        JOIN tbl_usuarios tbu USING (idusuario)
        JOIN cat_tarjetas ct USING (idtarjeta)
        JOIN cat_categoriagasto ccg USING (idcategoriagasto)
        WHERE tbc.pagado = FALSE AND ct.idusuario = :id_usuario
        ORDER BY tbc.fecha_vencimiento ASC
    """, params={"id_usuario": usuarios[usuario_seleccionado]}, ttl=0)

    
    # (La primera parte de tu código, con la consulta, se mantiene igual)

    # Verificamos si hay cuotas antes de continuar
    if not cuotas_sin_pagar.empty:

        tab2, tab1 = st.tabs(["Pago por Tarjeta (agrupado)","Pago Detallado (uno por uno)"])
        # ----------------------------------------------------------------------------------
        # PESTAÑA 2: PAGO AGRUPADO POR TARJETA
        # ----------------------------------------------------------------------------------
        with tab2:
            st.info("Selecciona una tarjeta para ver el desglose de sus cuotas pendientes y pagarlas todas juntas.")
            
            # Usamos Pandas para crear el resumen a partir del DataFrame que ya tenemos
            df_resumen = cuotas_sin_pagar.groupby(['idtarjeta', 'tarjeta']).agg(
                numero_de_cuotas=('idcuota', 'count'),
                monto_total_a_pagar=('monto', 'sum')
            ).reset_index()

            # Creamos las opciones para el selectbox
            opciones = {f"{row.tarjeta} ({row.numero_de_cuotas} cuotas | ${row.monto_total_a_pagar:,.2f})": row.idtarjeta for row in df_resumen.itertuples()}
            
            tarjeta_seleccionada_str = st.selectbox("Seleccione la tarjeta a pagar:", options=opciones.keys())
            
            if tarjeta_seleccionada_str:
                id_tarjeta_seleccionada = opciones[tarjeta_seleccionada_str]

                st.write("#### Desglose de cuotas que se pagarán:")
                # Filtramos el DF original para mostrar el desglose
                desglose_df = cuotas_sin_pagar[cuotas_sin_pagar['idtarjeta'] == id_tarjeta_seleccionada]
                
                # 2. DEFINIR TODA LA CONFIGURACIÓN EN UN SOLO LUGAR
                column_config = {
                    "idcuota": st.column_config.NumberColumn("ID", disabled=True),
                    "fecha_vencimiento": "Fecha Límite de Pago",
                    "numero_cuota": "Mensualidad Nº",
                    "monto": st.column_config.NumberColumn("Monto", format="$%.2f"), # Formato de moneda aquí
                    "fecha": "Fecha de Transacción",
                    "apodo": "Responsable Transacción",
                    "categoria": "Categoría",
                    "tarjeta": st.column_config.TextColumn("Tarjeta", width="small"), # Ajuste de ancho aquí
                    "descripcion": "Descripción Compra",
                    "detalle": "Detalle Adicional",
                    "monto_total": st.column_config.NumberColumn("Monto Total Transacción", format="$%.2f"), # Formato de moneda aquí
                    "meses_total": "Total Meses",
                    "idtarjeta": None # Ocultar la columna de ID de tarjeta
                }

                # 3. MOSTRAR EL DATAFRAME CON SU CONFIGURACIÓN
                st.dataframe(
                    desglose_df,  # Pasamos el DataFrame de datos puros
                    column_config=column_config,
                    hide_index=True,
                    width='content'
                )

                fecha_pago_agrupado = st.date_input("Fecha de pago", key="fecha_agrupado")

                if st.button("Pagar Todas las Cuotas de esta Tarjeta", key="btn_agrupado"):
                    try:
                        with conn.session as s:
                            # Obtenemos los IDs de las cuotas del desglose
                            ids_a_pagar_agrupado = desglose_df['idcuota'].tolist()
                            sql_update = text("UPDATE tbl_cuotas SET fecha_pago = :fecha_pago WHERE idcuota = ANY(:ids)")
                            s.execute(sql_update, {"fecha_pago": fecha_pago_agrupado, "ids": ids_a_pagar_agrupado})
                            s.commit()
                            st.session_state.success_message = f"¡Todas las cuotas de la tarjeta '{tarjeta_seleccionada_str.split(' ')[0]}' fueron pagadas!"
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {str(e)}")
        # ----------------------------------------------------------------------------------
        # PESTAÑA 1: PAGO DETALLADO CON CHECKBOXES
        # ----------------------------------------------------------------------------------
        with tab1:
            df_seleccionable = cuotas_sin_pagar.copy()
            df_seleccionable.insert(0, "Pagar", False)
            
            st.info("Marca las casillas en la columna 'Pagar' y luego selecciona una fecha para actualizar las cuotas seleccionadas.")

            # --- 2. CONFIGURAR LAS COLUMNAS PARA EL EDITOR ---
            # Aquí definimos los nuevos nombres y formatos
            column_config = {
                "idcuota": st.column_config.NumberColumn("ID", disabled=True),
                "fecha_vencimiento": "Fecha Límite de Pago",
                "numero_cuota": "Mensualidad Nº",
                "monto": st.column_config.NumberColumn("Monto", format="$%.2f"),
                "fecha": "Fecha de Transacción",
                "apodo": "Responsable Transacción",
                "categoria": "Categoría",
                "tarjeta": "Tarjeta",
                "descripcion": "Descripción Compra",
                "detalle": "Detalle Adicional",
                "monto_total": st.column_config.NumberColumn("Monto Total Transacción", format="$%.2f"),
                "meses_total": "Total Meses",
                "idtarjeta": None # Ocultar la columna de ID de tarjeta
            }

            edited_df = st.data_editor(
                df_seleccionable,
                column_config=column_config,
                hide_index=True,
                key="data_editor_detallado",
                width='content'
            )

            fecha_pago_detallado = st.date_input("Fecha de pago", key="fecha_detallado")

            if st.button("Marcar seleccionadas como Pagadas", key="btn_detallado"):
                filas_a_pagar = edited_df[edited_df['Pagar'] == True]
                if not filas_a_pagar.empty:
                    ids_a_pagar = filas_a_pagar['idcuota'].tolist()
                    try:
                        with conn.session as s:
                            sql_update = text("UPDATE tbl_cuotas SET fecha_pago = :fecha_pago WHERE idcuota = ANY(:ids)")
                            s.execute(sql_update, {"fecha_pago": fecha_pago_detallado, "ids": ids_a_pagar})
                            s.commit()
                            st.session_state.success_message = f"¡Se marcaron {len(ids_a_pagar)} cuota(s) como pagadas!"
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {str(e)}")
                else:
                    st.warning("No has seleccionado ninguna cuota.")
    else:
        st.info("¡Felicidades! No hay cuotas pendientes de pago para este usuario.")
