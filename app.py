import streamlit as st
from  catalogos import *
from connection_db import *
from insert_transaction import insert_transaction

st.set_page_config(
    page_title="Sistema de Gestión de Gastos",
    page_icon="💰",
    layout="wide"  # Modo ancho activado
)


# Interfaz principal
def main():
    st.title("📝 Sistema de Gestión de Gastos")
    menu_option = st.selectbox("Menú Principal", ["Registrar Transacción", "Administrar Catálogos"])
    
    # Registrar nueva transacción
    if menu_option == "Registrar Transacción":
        insert_transaction()
    
    elif menu_option == "Administrar Catálogos":
        administrar_catalogos()
    # Otras secciones (Ver Transacciones, Catalogos)...
    # [Implementación similar usando queries a PostgreSQL]




if __name__ == "__main__":
    main()