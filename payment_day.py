import streamlit as st
from connection_db import get_db_connection
import pandas as pd
from sqlalchemy import text

def get_column_config(ocultar_tarjeta=False):
    return {
        "idtransaccion": st.column_config.NumberColumn("ID Transacción", disabled=True),
        "idcuota": st.column_config.NumberColumn("ID Cuota", disabled=True),
        "fecha": "Fecha de Transacción",
        "apodo": "Responsable",
        "monto_total": st.column_config.NumberColumn("Monto Total", format="$%.2f"),
        "meses_total": "Total Meses",
        "numero_cuota": "Mensualidad Nº",
        "monto": st.column_config.NumberColumn("Monto", format="$%.2f"),
        "fecha_vencimiento": "Fecha Límite de Pago",
        "descripcion": "Descripción Compra",
        "detalle": st.column_config.TextColumn("Detalle Adicional", width="medium"),
        "categoria": "Categoría",
        
        # ---> ¡AQUÍ ESTÁ TU IF TERNARIO! <---
        "tarjeta": None if ocultar_tarjeta else "Tarjeta", 
        
        "estado_cuota": "Estado",
        "idtarjeta": None # Oculto
    }

def set_payment_day():
    st.header("Registrar Pagos por Tarjetas")

    # Mostramos el mensaje de éxito si existe en la memoria
    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message
    
    conn = get_db_connection()

    usuarios = conn.query("SELECT idusuario, apodo FROM tbl_usuarios WHERE idusuario in (1,2) ORDER BY idusuario", ttl=0)
    usuarios = {apodo: id_usuario for id_usuario, apodo in usuarios.itertuples(index=False)}

    usuario_seleccionado = st.selectbox("Usuario", options=list(usuarios.keys()))

    # 1. TRAEMOS TODAS LAS CUOTAS SIN PAGAR (Quitamos el límite de fecha del WHERE)
    cuotas_sin_pagar = conn.query("""
        SELECT tbt.idtransaccion, tbc.idcuota, tbc.fecha_vencimiento, tbc.monto, tbc.numero_cuota, tbt.fecha, tbu.apodo, ccg.nombre AS categoria,
                 ct.idtarjeta, ct.nombre AS tarjeta, tbt.descripcion, tbt.detalle, tbt.monto_total, tbt.meses_total
        FROM tbl_cuotas tbc
        JOIN tbl_transacciones tbt USING (idtransaccion)
        JOIN tbl_usuarios tbu USING (idusuario)
        JOIN cat_tarjetas ct USING (idtarjeta)
        JOIN cat_categoriagasto ccg USING (idcategoriagasto)
        WHERE tbc.pagado = FALSE AND ct.idusuario = :id_usuario
        ORDER BY tbc.fecha_vencimiento ASC, tbt.fecha ASC
    """, params={"id_usuario": usuarios[usuario_seleccionado]}, ttl=0)

    if not cuotas_sin_pagar.empty:
        
        # ----------------------------------------------------------------------------------
        # 2. CLASIFICACIÓN AUTOMÁTICA CON PANDAS
        # ----------------------------------------------------------------------------------
        hoy = pd.Timestamp.today().normalize()
        # Consideramos "Vigente" cualquier cuota que venza en los próximos 35 días 
        # (cubre el ciclo actual completo de cualquier tarjeta)
        limite_vigente = hoy + pd.DateOffset(days=35) 
        
        fechas_vencimiento = pd.to_datetime(cuotas_sin_pagar['fecha_vencimiento'])
        
        # Asignamos los estados
        cuotas_sin_pagar['estado_cuota'] = '🟢 Vigente' # Por defecto
        cuotas_sin_pagar.loc[fechas_vencimiento < hoy, 'estado_cuota'] = '🔴 Vencida'
        cuotas_sin_pagar.loc[fechas_vencimiento > limite_vigente, 'estado_cuota'] = '🔵 Adelantada (Futuro)'

        orden_base = [
            "idtransaccion",
            "idcuota",
            "fecha",
            "apodo",
            "monto_total",
            "meses_total",
            "numero_cuota",
            "monto",
            "fecha_vencimiento",
            "descripcion",
            "detalle",
            "categoria",
            "tarjeta",
            "estado_cuota",
            "idtarjeta"
        ]
        
        # Aplicamos el orden al DataFrame maestro antes de hacer cualquier otra cosa
        cuotas_sin_pagar = cuotas_sin_pagar[orden_base]

        # Separamos los DataFrames para las pestañas
        df_pago_normal = cuotas_sin_pagar[cuotas_sin_pagar['estado_cuota'] != '🔵 Adelantada (Futuro)'].copy()
        df_adelantado = cuotas_sin_pagar[cuotas_sin_pagar['estado_cuota'] == '🔵 Adelantada (Futuro)'].copy()

        # Creamos las 3 pestañas
        tab1, tab2, tab3 = st.tabs(["Pago Agrupado (Vencido/Vigente)", "Pago Detallado", "Adelantar Pagos (Futuro)"])
        
        # ----------------------------------------------------------------------------------
        # PESTAÑA 1: PAGO AGRUPADO (Solo Vencido y Vigente)
        # ----------------------------------------------------------------------------------
        with tab1:
            if df_pago_normal.empty:
                st.success("¡Al día! No tienes pagos vencidos ni vigentes próximos para este usuario.")
            else:
                st.info("Selecciona una tarjeta para ver el desglose de sus cuotas pendientes normales y pagarlas juntas.")
                
                df_resumen = df_pago_normal.groupby(['idtarjeta', 'tarjeta']).agg(
                    numero_de_cuotas=('idcuota', 'count'),
                    monto_total_a_pagar=('monto', 'sum')
                ).reset_index()

                opciones = {f"{row.tarjeta} ({row.numero_de_cuotas} cuotas | ${row.monto_total_a_pagar:,.2f})": row.idtarjeta for row in df_resumen.itertuples()}
                tarjeta_seleccionada_str = st.selectbox("Seleccione la tarjeta a pagar:", options=opciones.keys(), key="sel_agrupado")
                
                if tarjeta_seleccionada_str:
                    id_tarjeta_seleccionada = opciones[tarjeta_seleccionada_str]

                    st.write("#### Desglose de cuotas que se pagarán:")
                    desglose_df = df_pago_normal[df_pago_normal['idtarjeta'] == id_tarjeta_seleccionada]
                    
                    st.dataframe(
                        desglose_df, 
                        column_config=get_column_config(ocultar_tarjeta=True),
                        hide_index=True,
                        use_container_width=True
                    )

                    fecha_pago_agrupado = st.date_input("Fecha de pago", key="fecha_agrupado")

                    if st.button("Pagar Todas las Cuotas de esta Tarjeta", key="btn_agrupado"):
                        try:
                            with conn.session as s:
                                ids_a_pagar = desglose_df['idcuota'].tolist()
                                sql_update = text("UPDATE tbl_cuotas SET fecha_pago = :fecha_pago, pagado = TRUE WHERE idcuota = ANY(:ids)")
                                s.execute(sql_update, {"fecha_pago": fecha_pago_agrupado, "ids": ids_a_pagar})
                                s.commit()
                                st.session_state.success_message = f"¡Todas las cuotas de la tarjeta '{tarjeta_seleccionada_str.split(' ')[0]}' fueron pagadas!"
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {str(e)}")

        # ----------------------------------------------------------------------------------
        # PESTAÑA 2: PAGO DETALLADO (Solo Vencido y Vigente)
        # ----------------------------------------------------------------------------------
        with tab2:
            if df_pago_normal.empty:
                st.success("No hay pagos pendientes para mostrar aquí.")
            else:
                st.info("Marca las casillas para pagar cuotas vigentes o vencidas de forma individual.")

                # --- NUEVO: FILTRO POR TARJETA ---
                tarjetas_disponibles_t2 = ["Todas"] + df_pago_normal['tarjeta'].unique().tolist()
                filtro_tarjeta_t2 = st.selectbox("Filtrar por tarjeta:", options=tarjetas_disponibles_t2, key="filtro_t2")

                # Aplicamos el filtro
                if filtro_tarjeta_t2 == "Todas":
                    df_seleccionable = df_pago_normal.copy()
                else:
                    df_seleccionable = df_pago_normal[df_pago_normal['tarjeta'] == filtro_tarjeta_t2].copy()

                df_seleccionable.insert(0, "Pagar", False)
                
                debo_ocultar = filtro_tarjeta_t2 != "Todas"

                edited_df = st.data_editor(
                    df_seleccionable,
                    column_config=get_column_config(ocultar_tarjeta=debo_ocultar),
                    hide_index=True,
                    key="editor_detallado",
                    use_container_width=True
                )

                fecha_pago_detallado = st.date_input("Fecha de pago", key="fecha_detallado")

                if st.button("Marcar seleccionadas como Pagadas", key="btn_detallado"):
                    filas_a_pagar = edited_df[edited_df['Pagar'] == True]
                    if not filas_a_pagar.empty:
                        ids_a_pagar = filas_a_pagar['idcuota'].tolist()
                        try:
                            with conn.session as s:
                                sql_update = text("UPDATE tbl_cuotas SET fecha_pago = :fecha_pago, pagado = TRUE WHERE idcuota = ANY(:ids)")
                                s.execute(sql_update, {"fecha_pago": fecha_pago_detallado, "ids": ids_a_pagar})
                                s.commit()
                                st.session_state.success_message = f"¡Se pagaron {len(ids_a_pagar)} cuota(s) exitosamente!"
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {str(e)}")
                    else:
                        st.warning("No has seleccionado ninguna cuota.")

        # ----------------------------------------------------------------------------------
        # PESTAÑA 3: ADELANTAR PAGOS (Solo cuotas futuras)
        # ----------------------------------------------------------------------------------
        with tab3:
            if df_adelantado.empty:
                st.info("No tienes cuotas futuras (adelantadas) pendientes de pago.")
            else:
                st.warning("Estas cuotas corresponden a meses futuros. Selecciónalas solo si deseas adelantar pagos.")

                # --- NUEVO: FILTRO POR TARJETA ---
                tarjetas_disponibles_t3 = ["Todas"] + df_adelantado['tarjeta'].unique().tolist()
                filtro_tarjeta_t3 = st.selectbox("Filtrar por tarjeta:", options=tarjetas_disponibles_t3, key="filtro_t3")

                # Aplicamos el filtro
                if filtro_tarjeta_t3 == "Todas":
                    df_adelantable = df_adelantado.copy()
                else:
                    df_adelantable = df_adelantado[df_adelantado['tarjeta'] == filtro_tarjeta_t3].copy()

                df_adelantable.insert(0, "Adelantar", False)

                debo_ocultar = filtro_tarjeta_t3 != "Todas"

                edited_adelanto = st.data_editor(
                    df_adelantable,
                    column_config=get_column_config(ocultar_tarjeta=debo_ocultar),
                    hide_index=True,
                    key="editor_adelantado",
                    use_container_width=True
                )

                fecha_pago_adelantado = st.date_input("Fecha de pago adelantado", key="fecha_adelantado")

                if st.button("Adelantar Pagos Seleccionados", key="btn_adelantado"):
                    filas_a_pagar = edited_adelanto[edited_adelanto['Adelantar'] == True]
                    if not filas_a_pagar.empty:
                        ids_a_pagar = filas_a_pagar['idcuota'].tolist()
                        try:
                            with conn.session as s:
                                sql_update = text("UPDATE tbl_cuotas SET fecha_pago = :fecha_pago, pagado = TRUE WHERE idcuota = ANY(:ids)")
                                s.execute(sql_update, {"fecha_pago": fecha_pago_adelantado, "ids": ids_a_pagar})
                                s.commit()
                                st.session_state.success_message = f"¡Se adelantaron {len(ids_a_pagar)} cuota(s) exitosamente!"
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {str(e)}")
                    else:
                        st.warning("No has seleccionado ninguna cuota para adelantar.")

    else:
        st.info("¡Felicidades! No hay absolutamente ninguna cuota pendiente de pago para este usuario.")