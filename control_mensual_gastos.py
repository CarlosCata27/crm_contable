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
    print(usuarios)


    df_usuarios = usuarios.rename(columns={"idusuario": "ID Usuario", "apodo": "Apodo","ingreso_mensual":"Ingreso Mensual"}).style.format({"Ingreso Mensual": "${:,.2f}"})
    st.dataframe(df_usuarios)
