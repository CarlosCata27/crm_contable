import streamlit as st
from connection_db import get_db_connection
from datetime import date
import pandas as pd
from sqlalchemy import text

def insert_transaction():
    st.header("Nueva Transacción")
    
    # Se define la conexión una sola vez al principio.
    conn = get_db_connection()
    
    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message

    with st.form("transaccion_form"):
        # Obtener usuarios
        df_usuarios = conn.query("SELECT idusuario, apodo FROM tbl_usuarios ORDER BY idusuario",ttl=0)
        ## Iterar correctamente sobre el DataFrame.
        usuarios = {apodo: id_usuario for id_usuario, apodo in df_usuarios.itertuples(index=False)}

        # Obtener categorías
        df_categorias = conn.query("SELECT idcategoriagasto, nombre FROM cat_categoriagasto",ttl=0)
        ## Iterar correctamente sobre el DataFrame.
        categorias = {nombre: id_categoria for id_categoria, nombre in df_categorias.itertuples(index=False)}
        
        # Obtener tarjetas 
        df_tarjetas = conn.query("""
            SELECT t.idtarjeta, t.nombre, COALESCE(u.apodo, 'Sin asignar') AS apodo 
            FROM cat_tarjetas t
            LEFT JOIN tbl_usuarios u ON t.idusuario = u.idusuario
        """,ttl=0)
        ## Iterar correctamente sobre el DataFrame.
        tarjetas = { f"{nombre} ({apodo})": id_tarjeta for id_tarjeta, nombre, apodo in df_tarjetas.itertuples(index=False)}

        # --- Campos del formulario (sin cambios) ---
        col1, col2 = st.columns(2)
        fecha = col1.date_input("Fecha", value=date.today())
        categoria_seleccionada = col2.selectbox("Categoría", options=list(categorias.keys()))
        
        col3, col4 = st.columns(2)
        usuario_seleccionado = col3.selectbox("Usuario", options=list(usuarios.keys()))
        tarjeta_seleccionada = col4.selectbox("Método de Pago", options=list(tarjetas.keys()))

        descripcion = st.text_input("Descripción")
        detalle = st.text_area("Detalle Adicional")

        col5, col6 = st.columns(2)
        monto = col5.number_input("Monto Total", min_value=0.0, step=0.50)
        meses = col6.number_input("Meses", min_value=1, value=1)

        submitted = st.form_submit_button("Guardar Transacción")
        
        if submitted:
            ## CAMBIO 2: No se vuelve a llamar a get_db_connection(). Reutilizamos 'conn'.
            try:
                # Mapear las selecciones del formulario a sus IDs
                id_usuario = usuarios[usuario_seleccionado]
                id_categoria = categorias[categoria_seleccionada]
                id_tarjeta = tarjetas[tarjeta_seleccionada]

                ## CAMBIO 3: Usar conn.query() para obtener el ID de vuelta.
                # Es más seguro usar parámetros con nombre (:param) en lugar de %s.

                print(id_categoria, id_usuario, id_tarjeta)

                with conn.session as s:
                    sql = text("""
                        INSERT INTO tbl_transacciones (
                            fecha, idusuario, idcategoriagasto, idtarjeta,
                            descripcion, detalle, monto_total, meses_total
                        ) VALUES (
                        :fecha, :id_usuario, :id_categoria, :id_tarjeta,
                        :descripcion, :detalle, :monto, :meses
                        )
                        RETURNING idtransaccion
                    """)
                    result_df = s.execute(sql, params={
                        "fecha": fecha, 
                        "id_usuario": id_usuario,
                        "id_categoria": id_categoria,
                        "id_tarjeta": id_tarjeta,
                        "descripcion": descripcion,
                        "detalle": detalle,
                        "monto": monto,
                        "meses": meses
                    })
                    
                    # Obtener el ID del DataFrame resultante
                    trans_id = result_df.fetchone()[0]
                    s.commit()
                    st.session_state.success_message = f"¡Transacción registrada con éxito! ID: {trans_id}"
                    st.rerun()
                    
                
            except Exception as e:
                st.error(f"Error al guardar la transacción: {str(e)}")