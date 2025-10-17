import streamlit as st
from connection_db import get_db_connection
from datetime import date
import pandas as pd

def insert_transaction():
    st.header("Nueva Transacción")
    
    # Se define la conexión una sola vez al principio.
    conn = get_db_connection()
    
    with st.form("transaccion_form"):
        # Obtener usuarios
        df_usuarios = conn.query("SELECT idusuario, apodo FROM tbl_usuarios",ttl=0)
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
        fecha = st.date_input("Fecha", value=date.today())
        usuario_seleccionado = st.selectbox("Usuario", options=list(usuarios.keys()))
        categoria_seleccionada = st.selectbox("Categoría", options=list(categorias.keys()))
        tarjeta_seleccionada = st.selectbox("Método de Pago", options=list(tarjetas.keys()))
        descripcion = st.text_input("Descripción")
        detalle = st.text_area("Detalle Adicional")
        monto = st.number_input("Monto Total", min_value=0.0, step=0.50)
        meses = st.number_input("Meses", min_value=1, value=1)
        
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
                sql = """
                    INSERT INTO tbl_transacciones (
                        fecha, idusuario, idcategoriagasto, idtarjeta,
                        descripcion, detalle, monto_total, meses_total
                    ) VALUES (
                        :fecha, :id_usuario, :id_categoria, :id_tarjeta,
                        :descripcion, :detalle, :monto, :meses
                    )
                    RETURNING idtransaccion
                """
                
                # conn.query() también funciona para INSERT...RETURNING
                result_df = conn.query(sql, params={
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
                trans_id = result_df.iloc[0]['idtransaccion']

                ## CAMBIO 4: Se elimina conn.commit(), no es necesario.
                st.success(f"¡Transacción registrada con éxito! ID: {trans_id}")
                
            except Exception as e:
                st.error(f"Error al guardar la transacción: {str(e)}")