import streamlit as st
from  catalogos import *
from connection_db import *
from insert_transaction import insert_transaction
from payment_day import set_payment_day
from control_mensual_gastos import control_mensual
from last_movements_for_card import last_movements_for_each_card

st.set_page_config(
    page_title="Sistema de Gestión de Gastos",
    page_icon="💰",
    layout="wide"  # Modo ancho activado
)


# Interfaz principal
def main():
    st.title("📝 Sistema de Gestión de Gastos")
    menu_option = st.selectbox("Menú Principal", ["Registrar Transacción","Registrar pagos","Control de Gastos Mensual","Administrar Catálogos","Ultimos movimientos por Tarjeta"])
    
    # Registrar nueva transacción
    if menu_option == "Registrar Transacción":
        insert_transaction()
    
    elif menu_option == "Administrar Catálogos":
        administrar_catalogos()
    elif menu_option == "Registrar pagos":
        set_payment_day()
    elif menu_option == "Control de Gastos Mensual":
        control_mensual()
    elif menu_option == "Ultimos movimientos por Tarjeta":
        last_movements_for_each_card()
    # Otras secciones (Ver Transacciones, Catalogos)...
    # [Implementación similar usando queries a PostgreSQL]




if __name__ == "__main__":
    main()