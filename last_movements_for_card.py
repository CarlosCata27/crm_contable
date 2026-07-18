import streamlit as st
from connection_db import get_db_connection
import pandas as pd
from sqlalchemy import text

@st.dialog("⚠️ Confirmar Actualización")
def confirmar_guardado(cambios_dict, df_editado, df_original, mapa_us, mapa_cat, conexion):
    st.write("¿Estás seguro de que deseas guardar estas modificaciones en la base de datos? Esta acción no se puede deshacer.")
    
    col1, col2 = st.columns(2)
    
    if col1.button("Sí, Guardar Cambios", type="primary"):
        try:
            with conexion.session as s:
                for row_index in cambios_dict.keys():
                    row_index = int(row_index) 
                    id_trans = int(df_original.loc[row_index, 'idtransaccion'])
                    
                    # Extraer toda la fila
                    nueva_fecha = df_editado.loc[row_index, 'fecha']
                    nueva_desc = str(df_editado.loc[row_index, 'descripcion'])
                    nuevo_detalle = str(df_editado.loc[row_index, 'detalle'])
                    nuevo_monto = float(df_editado.loc[row_index, 'monto_total'])
                    
                    # Traducir los textos a IDs
                    apodo_sel = df_editado.loc[row_index, 'usuario_transaccion']
                    nuevo_id_usuario = int(mapa_us[apodo_sel])
                    
                    cat_sel = df_editado.loc[row_index, 'categoria_gasto']
                    nuevo_id_categoria = int(mapa_cat[cat_sel])

                    # El UPDATE a la BD
                    sql_update = text("""
                        UPDATE tbl_transacciones
                        SET fecha = :fecha, descripcion = :desc, detalle = :detalle,
                            monto_total = :monto, idusuario = :id_usuario, idcategoriagasto = :id_categoria
                        WHERE idtransaccion = :id
                    """)
                    s.execute(sql_update, {
                        "fecha": nueva_fecha, "desc": nueva_desc, "detalle": nuevo_detalle,
                        "monto": nuevo_monto, "id_usuario": nuevo_id_usuario,
                        "id_categoria": nuevo_id_categoria, "id": id_trans
                    })
                
                s.commit()
                # Guardamos el mensaje de éxito en memoria para que sobreviva al recargo de página
                st.session_state.success_message = "¡Los cambios se guardaron correctamente!"
                st.rerun() 
                
        except Exception as e:
            st.error(f"Error al actualizar la base de datos: {e}")
            
    if col2.button("Cancelar"):
        st.rerun()

def last_movements_for_each_card():
    st.header("Últimos Movimientos por Tarjeta")

    # --- Mostrar mensaje de éxito si venimos del popup ---
    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message

    conn = get_db_connection()

    # -------------------------------------------------------------------------
    # 1. SOLUCIÓN A TARJETAS DUPLICADAS: Agregamos el apodo del usuario
    # -------------------------------------------------------------------------
    cards = conn.query("""
        SELECT t.idtarjeta, t.nombre, COALESCE(u.apodo, 'Sin asignar') AS apodo, 
            COUNT(tr.idtransaccion) as frecuencia
        FROM cat_tarjetas t
        LEFT JOIN tbl_usuarios u ON t.idusuario = u.idusuario
        LEFT JOIN tbl_transacciones tr ON t.idtarjeta = tr.idtarjeta
        GROUP BY t.idtarjeta, t.nombre, u.apodo
        ORDER BY frecuencia DESC, t.nombre ASC
        
    """, ttl=0)
    
    # El diccionario ahora tiene la llave "Nombre (Usuario)"
    mapa_tarjetas = {f"{row.nombre} ({row.apodo})": row.idtarjeta for row in cards.itertuples(index=False)}

    selected_card = st.selectbox("Tarjeta", options=list(mapa_tarjetas.keys()))
    key_selected_card = mapa_tarjetas[selected_card]

    # -------------------------------------------------------------------------
    # 2. DICCIONARIOS PARA USUARIOS Y CATEGORÍAS (Para los Selectbox)
    # -------------------------------------------------------------------------
    df_usuarios = conn.query("SELECT idusuario, apodo FROM tbl_usuarios", ttl=0)
    mapa_usuarios = {row.apodo: row.idusuario for row in df_usuarios.itertuples(index=False)}

    df_categorias = conn.query("SELECT idcategoriagasto, nombre FROM cat_categoriagasto", ttl=0)
    mapa_categorias = {row.nombre: row.idcategoriagasto for row in df_categorias.itertuples(index=False)}

    # Consulta principal (sin cambios mayores)
    transactions = conn.query("""
        SELECT 
                tt.idtransaccion, 
                tt.fecha,
                tu.apodo as usuario_transaccion,
                ccg.nombre as categoria_gasto,
                tt.descripcion,
                tt.detalle,
                tt.monto_total,
                tt.meses_total
        FROM tbl_transacciones tt
        JOIN tbl_usuarios tu USING (idusuario)
        JOIN cat_tarjetas ct USING (idtarjeta)
        JOIN cat_categoriagasto ccg USING (idcategoriagasto)
        WHERE tt.idtarjeta != 11 and tt.idtarjeta = :id_tarjeta
        ORDER BY tt.fecha DESC
        LIMIT 50
    """, params={"id_tarjeta": key_selected_card}, ttl=0)

    if not transactions.empty:
        st.subheader(f"Resumen de Gastos: {selected_card}")
        
        # -------------------------------------------------------------------------
        # 3. CONFIGURACIÓN DEL EDITOR (Añadimos SelectboxColumn)
        # -------------------------------------------------------------------------
        column_config = {
            "idtransaccion": st.column_config.NumberColumn("ID Transacción", disabled=True),
            "fecha": st.column_config.DateColumn("Fecha", format="DD-MM-YYYY"),
            "usuario_transaccion": st.column_config.SelectboxColumn(
                "Usuario",
                options=list(mapa_usuarios.keys()), # Opciones limitadas a los usuarios existentes
                required=True
            ), 
            "categoria_gasto": st.column_config.SelectboxColumn(
                "Categoría",
                options=list(mapa_categorias.keys()), # Opciones limitadas a las categorías existentes
                required=True
            ), 
            "descripcion": "Descripción",
            "detalle": "Detalle",
            "monto_total": st.column_config.NumberColumn("Monto", format="$%.2f", min_value=0.0),
            "meses_total": st.column_config.NumberColumn("Meses", disabled=False)
        }

        editor_key = f"editor_{key_selected_card}"

        edited_transactions_df = st.data_editor(
            transactions, 
            use_container_width=True, 
            hide_index=True, 
            column_config=column_config,
            key=editor_key
        )
        # 1. Leemos el diccionario de cambios en memoria
        cambios_diccionario = st.session_state[editor_key].get("edited_rows", {})

        # 2. Si hay cambios, armamos un resumen visual y elegante
        if cambios_diccionario:
            st.markdown("---")
            st.markdown("### 📝 Resumen de Cambios a Guardar")
            
            # Recorremos cada fila editada para mostrarla bonita
            for row_index, cambios in cambios_diccionario.items():
                row_index = int(row_index)
                # Extraemos la descripción para que el usuario sepa QUÉ transacción está modificando
                idtransaction = edited_transactions_df.loc[row_index, 'idtransaccion']
                desc_tx = edited_transactions_df.loc[row_index, 'descripcion']
                
                # Usamos un mensaje info o un bloque para separar cada transacción editada
                st.info(f"**Transacción:** {desc_tx} (ID: {idtransaction})")
                
                # Listamos específicamente qué columnas modificó en esa fila
                for columna, nuevo_valor in cambios.items():
                    # Limpiamos el nombre de la columna (ej: 'monto_total' -> 'Monto Total')
                    nombre_col_limpio = columna.replace("_", " ").title()
                    st.markdown(f"- 🔄 **{nombre_col_limpio}** cambiará a: `{nuevo_valor}`")

            st.write("") # Espacio en blanco

            # 3. Botón para abrir el popup de confirmación
            if st.button("Revisar y Confirmar Cambios", type="primary"):
                # Llamamos a la función del popup pasándole todas las variables que necesita
                confirmar_guardado(
                    cambios_diccionario, 
                    edited_transactions_df, 
                    transactions, 
                    mapa_usuarios, 
                    mapa_categorias, 
                    conn
                )

    else:
        st.warning(f"No hay transacciones registradas para la tarjeta: {selected_card}")