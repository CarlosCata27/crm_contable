import streamlit as st
from connection_db import get_db_connection
from datetime import date

def insert_transaction():
    st.header("Nueva Transacción")
    
    with st.form("transaccion_form"):
        # Obtener datos dinámicos de la BD
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Obtener usuarios
            cur.execute("SELECT idusuario, apodo FROM tbl_usuarios")
            usuarios = {row[1]: row[0] for row in cur.fetchall()}
            
            # Obtener categorías
            cur.execute("SELECT idcategoriagasto, nombre FROM cat_categoriagasto")
            categorias = {row[1]: row[0] for row in cur.fetchall()}
            
            # Obtener tarjetas
            cur.execute("SELECT idtarjeta, nombre FROM cat_tarjetas")
            tarjetas = {row[1]: row[0] for row in cur.fetchall()}
        
        # Campos del formulario
        fecha = st.date_input("Fecha", value=date.today())
        usuario = st.selectbox("Usuario", options=list(usuarios.keys()))
        categoria = st.selectbox("Categoría", options=list(categorias.keys()))
        tarjeta = st.selectbox("Método de Pago", options=list(tarjetas.keys()))
        descripcion = st.text_input("Descripción")
        detalle = st.text_area("Detalle Adicional")
        monto = st.number_input("Monto Total", min_value=0.0, step=0.01)
        meses = st.number_input("Meses", min_value=1, value=1)
        
        # Manejo de compras a meses
        if meses > 1:
            mes_inicio = st.date_input("Primer Pago", value=date.today())
        else:
            mes_inicio = fecha
        
        submitted = st.form_submit_button("Guardar Transacción")
        
        if submitted:
            with get_db_connection() as conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO tbl_transacciones (
                            fecha, idusuario, idcategoriagasto, idtarjeta,
                            descripcion, detalle, monto_total, meses_total, mes_inicio
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING idtransaccion
                        """,
                        (
                            fecha, 
                            usuarios[usuario], 
                            categorias[categoria],
                            tarjetas[tarjeta],
                            descripcion,
                            detalle,
                            monto,
                            meses,
                            mes_inicio
                        )
                    )
                    trans_id = cur.fetchone()[0]
                    conn.commit()
                    st.success(f"¡Transacción registrada! ID: {trans_id}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")