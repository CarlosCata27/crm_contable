import streamlit as st
from connection_db import get_db_connection
import pandas as pd
from sqlalchemy import text


def administrar_catalogos():
    st.header("📚 Administración de Catálogos")
    
    # Conexión a la base de datos
    conn = get_db_connection()

    # Selector de catálogo
    catalogo = st.selectbox(
        "Seleccionar Catálogo", 
        ["Categorías de Gastos", "Usuarios", "Tarjetas"],
        key="catalogo_selector"
    )
    
    if catalogo == "Categorías de Gastos":
        administrar_categorias(conn)
    elif catalogo == "Tarjetas":
        administrar_tarjetas(conn)
    elif catalogo == "Usuarios":
        administrar_usuarios(conn)

def administrar_categorias(conn):
    st.subheader("Categorías de Gastos")

    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message
    
    # Selector de acción: Agregar o Editar
    accion = st.radio("Acción", ["Agregar nueva categoría", "Editar categoría existente"], horizontal=True)

    # Mostrar categorías existentes
    categorias = conn.query("SELECT idcategoriagasto, nombre, tipo FROM cat_categoriagasto ORDER BY tipo, nombre",ttl=0)

    if not categorias.empty:
        st.write("### Categorías Existentes")
        categorias_representation = categorias.rename(columns={'idcategoriagasto': 'ID', 'nombre': 'Nombre', 'tipo': 'Tipo'})
        st.dataframe(categorias_representation)
    else:
        st.info("No hay categorías registradas")
    
    if accion == "Agregar nueva categoría":
        # Formulario para nueva categoría
        with st.form("nueva_categoria_form", clear_on_submit=True):
            st.write("### Agregar Nueva Categoría")
            nombre = st.text_input("Nombre de la Categoría", max_chars=50)
            tipo = st.selectbox("Tipo", ["Fijo", "Variable"])
            
            
            
            submitted = st.form_submit_button("Guardar Categoría")
            
            if submitted:
                if not nombre:
                    st.error("El nombre es obligatorio")
                else:
                    try:
                        with conn.session as s:
                            sql = text("""INSERT INTO cat_categoriagasto (nombre, tipo) VALUES (:nombre, :tipo)""")
                            s.execute(sql, {"nombre": nombre.strip(), "tipo": tipo})
                            s.commit()
                            st.session_state.success_message = f"¡Categoría '{nombre}' guardada exitosamente!"
                            st.rerun()

                    except Exception as e:
                        # Si hay un error de SQL, el rollback es implícito, pero es bueno tenerlo
                        st.error(f"Error durante la operación: {str(e)}")
    else:  # Editar categoría existente
        if categorias.empty:
            st.warning("No hay categorías disponibles para editar")
            return
            
        # Seleccionar categoría a editar
        categorias_opciones = {f"{row.nombre} (ID: {row.idcategoriagasto})": row.idcategoriagasto for row in categorias.itertuples(index=False)}
        categoria_seleccionada = st.selectbox("Seleccione categoría a editar", options=list(categorias_opciones.keys()))

        # Obtener ID de la categoría seleccionada
        categoria_id = categorias_opciones[categoria_seleccionada]
        
        # Obtener datos actuales de la categoría usando el DataFrame que ya tenemos
        categoria_actual = categorias[categorias['idcategoriagasto'] == categoria_id].iloc[0]

        if not categoria_actual.empty:
            with st.form("editar_categoria_form"):
                st.write(f"### Editando categoría: {categoria_actual['nombre']}")
                nuevo_nombre = st.text_input("Nombre", value=categoria_actual['nombre'], max_chars=50)
                nuevo_tipo = st.selectbox("Tipo", ["Fijo", "Variable"], 
                                         index=0 if categoria_actual['tipo'] == "Fijo" else 1)

                submitted = st.form_submit_button("Actualizar Categoría")
                
                if submitted:
                    try:
                        session = conn.session
                        with session as s:
                            s.execute(
                                text("""UPDATE cat_categoriagasto SET nombre = :nombre, tipo = :tipo WHERE idcategoriagasto = :id"""),
                                params={"nombre": nuevo_nombre.strip(), "tipo": nuevo_tipo, "id": categoria_id}
                            )
                            s.commit()
                        st.session_state.success_message = f"¡Categoría '{nuevo_nombre}' actualizada exitosamente!"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {str(e)}")
                        s.rollback()

def administrar_tarjetas(conn):
    st.subheader("Tarjetas")

    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message
    
    # Selector de acción: Agregar o Editar
    accion = st.radio("Acción", ["Agregar nueva tarjeta", "Editar tarjeta existente"], horizontal=True)
    
    # Obtener usuarios para asignación
    usuarios = conn.query("SELECT idusuario, nombre FROM tbl_usuarios")
    usuarios_opciones = ["(Sin usuario asignado)"] + [f"{nombre} (ID: {id})" for id, nombre in usuarios.itertuples(index=False)]
    usuario_id_map = {f"{nombre} (ID: {id})": id for id, nombre in usuarios.itertuples(index=False)}
    
    
    # Mostrar tarjetas existentes
    tarjetas = conn.query("""
        SELECT t.idtarjeta, t.nombre AS tarjeta, u.idusuario, u.nombre AS usuario, t.dia_corte,t.dia_pago
        FROM cat_tarjetas t
        LEFT JOIN tbl_usuarios u ON u.idusuario = t.idusuario
        ORDER BY usuario asc, tarjeta desc
    """, ttl=0)

    if not tarjetas.empty:
        st.write("### Tarjetas Existentes")
        tarjetas_representacion = tarjetas.rename(columns={
            'idtarjeta': 'ID',
            'tarjeta': 'Tarjeta',
            'usuario': 'Dueño',
            'dia_corte': 'Día de Corte',
            'dia_pago': 'Día de Pago'
        }).drop(columns=['idusuario'])
        st.dataframe(tarjetas_representacion)
    else:
        st.info("No hay tarjetas registradas")
    
    if accion == "Agregar nueva tarjeta":
        # Formulario para nueva tarjeta
        with st.form("nueva_tarjeta_form", clear_on_submit=True):
            st.write("### Agregar Nueva Tarjeta")
            nombre = st.text_input("Nombre de la Tarjeta", max_chars=50)
            usuario_asignado = st.selectbox("Usuario Asignado", usuarios_opciones)
            dia_corte = st.number_input("Día de Corte", min_value=1, max_value=31, value=15)
            dia_pago = st.number_input("Día de Pago", min_value=1, max_value=31, value=30)
            
            submitted = st.form_submit_button("Guardar Tarjeta")
            
            if submitted:
                if not nombre:
                    st.error("El nombre es obligatorio")
                else:
                    try:
                        usuario_id = None
                        if usuario_asignado != "(Sin usuario asignado)":
                            usuario_id = usuario_id_map[usuario_asignado]
                        
                        session = conn.session
                        with session as s:
                            sql = text("INSERT INTO cat_tarjetas (nombre, idusuario,dia_corte,dia_pago) VALUES (:nombre, :idusuario, :dia_corte, :dia_pago)")
                            s.execute(
                                sql,
                                {
                                    "nombre": nombre.strip(),
                                    "idusuario": usuario_id,
                                    "dia_corte": dia_corte,
                                    "dia_pago": dia_pago
                                }
                            )
                            s.commit()
                            st.session_state.message = f"Tarjeta '{nombre}' guardada exitosamente!"
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")
    else:  # Editar tarjeta existente
        if tarjetas.empty:
            st.warning("No hay tarjetas disponibles para editar")
            return
            
        # Seleccionar tarjeta a editar
        tarjetas_opciones = {f"{row.nombre} (ID: {row.idtarjeta})":row.idtarjeta for row in tarjetas.itertuples(index=False)}
        tarjeta_seleccionada = st.selectbox("Seleccione tarjeta a editar", options=list(tarjetas_opciones.keys()))
        
        # Obtener ID de la tarjeta seleccionada
        tarjeta_id = tarjetas_opciones[tarjeta_seleccionada]

        # Obtener datos actuales de la tarjeta usando el DataFrame que ya tenemos
        tarjeta_actual = tarjetas[tarjetas['idtarjeta'] == tarjeta_id].iloc[0]
        
        if not tarjeta_actual.empty:
            # Determinar usuario actual asignado
            usuario_actual_key = "(Sin usuario asignado)"
            current_user_id = tarjeta_actual['idusuario']
            if pd.notna(current_user_id):
                # Invertimos el mapa para buscar por ID
                id_to_key_map = {v: k for k, v in usuario_id_map.items()}
                # Usamos .get() para evitar errores si un usuario fue borrado
                usuario_actual_key = id_to_key_map.get(current_user_id, "(Sin usuario asignado)")
            
            with st.form("editar_tarjeta_form"):
                st.write(f"### Editando tarjeta: {tarjeta_actual['nombre']}")
                nuevo_nombre = st.text_input("Nombre", value=tarjeta_actual['nombre'], max_chars=50)
                try:
                    indice_usuario_actual = usuarios_opciones.index(usuario_actual_key)
                except ValueError:
                    # Si el usuario ya no existe, por defecto ponemos "Sin asignar"
                    indice_usuario_actual = 0
                nuevo_usuario = st.selectbox("Usuario Asignado", usuarios_opciones, index=indice_usuario_actual)
                dia_corte = st.number_input("Día de Corte", min_value=1, max_value=31, value=int(tarjeta_actual['dia_corte']))
                dia_pago = st.number_input("Día de Pago", min_value=1, max_value=31, value=int(tarjeta_actual['dia_pago']))

                submitted = st.form_submit_button("Actualizar Tarjeta")
                
                if submitted:
                    try:
                        # Obtenemos el ID del usuario seleccionado (None si es "Sin asignar")
                        nuevo_usuario_id = usuario_id_map.get(nuevo_usuario)
                        with conn.session as s:
                            sql = text("UPDATE cat_tarjetas SET nombre = :nombre, idusuario = :idusuario, dia_corte = :dia_corte, dia_pago = :dia_pago WHERE idtarjeta = :idtarjeta")
                            s.execute(
                                sql,
                                {
                                    "nombre": nuevo_nombre.strip(),
                                    "idusuario": nuevo_usuario_id,
                                    "dia_corte": dia_corte,
                                    "dia_pago": dia_pago,
                                    "idtarjeta": tarjeta_id
                                }
                            )
                            s.commit()
                        st.session_state.success_message = f"¡Tarjeta '{nuevo_nombre}' actualizada exitosamente!"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {str(e)}")

def administrar_usuarios(conn):
    st.subheader("Usuarios")

    if 'success_message' in st.session_state:
        st.success(st.session_state.success_message)
        del st.session_state.success_message
    
    # Selector de acción: Agregar o Editar
    accion = st.radio("Acción", ["Agregar nuevo usuario", "Editar usuario existente"], horizontal=True)
    
    # Mostrar usuarios existentes
    usuarios = conn.query("SELECT idusuario, nombre, apellido_paterno, apellido_materno, apodo, email,ingreso_mensual FROM tbl_usuarios ORDER BY idusuario",ttl=0)


    if not usuarios.empty:
        st.write("### Usuarios Existentes")
        usuarios_representacion = usuarios.rename(
            columns={
                'idusuario': 'ID', 
                'nombre': 'Nombre', 
                'apellido_paterno': 'Apellido Paterno',
                'apellido_materno': 'Apellido Materno',
                'apodo': 'Apodo',
                'email': 'Email',
                'ingreso_mensual': 'Ingreso Mensual'
            }
        ).style.format({'Ingreso Mensual': '${:,.2f}'})
        st.dataframe(usuarios_representacion)
    else:
        st.info("No hay usuarios registrados")
    
    if accion == "Agregar nuevo usuario":
        # Formulario para nuevo usuario
        with st.form("nuevo_usuario_form", clear_on_submit=True):
            st.write("### Agregar Nuevo Usuario")
            col1, col2, col3 = st.columns(3)
            nombre = col1.text_input("Nombre", max_chars=50)
            apellido_paterno = col2.text_input("Apellido Paterno", max_chars=50)
            apellido_materno = col3.text_input("Apellido Materno", max_chars=50)

            col4, col5,col6 = st.columns(3)
            apodo = col4.text_input("Apodo", max_chars=50)
            email = col5.text_input("Email", max_chars=50)
            ingreso_mensual = col6.number_input("Ingreso Mensual", min_value=0, value=10000)

            submitted = st.form_submit_button("Guardar Usuario")
            
            if submitted:
                if not nombre or not apellido_paterno or not apellido_materno or not apodo:
                    st.error("Todos los datos son obligatorios (excepto email)")
                else:
                    try:
                        with conn.session as s:
                            sql = text("INSERT INTO tbl_usuarios (nombre, apellido_paterno, apellido_materno, apodo, email,ingreso_mensual) VALUES (:nombre, :apellido_paterno, :apellido_materno, :apodo, :email, :ingreso_mensual)")
                            s.execute(
                                sql,
                                {
                                    "nombre": nombre.strip(),
                                    "apellido_paterno": apellido_paterno.strip(),
                                    "apellido_materno": apellido_materno.strip(),
                                    "apodo": apodo.strip(),
                                    "email": email.strip() if email else None,
                                    "ingreso_mensual": ingreso_mensual
                                }
                            )
                            s.commit()
                            st.session_state.success_message = "¡Usuario agregado exitosamente!"
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")
    else:  # Editar usuario existente
        if usuarios.empty:
            st.warning("No hay usuarios disponibles para editar")
            return
            
        # Seleccionar usuario a editar
        usuarios_opciones = {f"{row.nombre} {row.apellido_paterno} (Apodo: {row.apodo}) (ID: {row.idusuario})":row.idusuario for row in usuarios.itertuples(index=False)}
        usuario_seleccionado = st.selectbox("Seleccione usuario a editar", options=list(usuarios_opciones.keys()))

        # Obtener ID del usuario seleccionado
        usuario_id = usuarios_opciones[usuario_seleccionado]

        # Obtener datos actuales del usuario
        usuario_actual = usuarios[usuarios['idusuario'] == usuario_id].iloc[0]
        if not usuario_actual.empty:
            with st.form("editar_usuario_form"):
                st.write(f"### Editando usuario: {usuario_actual['nombre']} {usuario_actual['apellido_paterno']}")
                col1, col2, col3 = st.columns(3)
                nuevo_nombre = col1.text_input("Nombre", value=usuario_actual['nombre'], max_chars=50)
                nuevo_apellido_paterno = col2.text_input("Apellido Paterno", value=usuario_actual['apellido_paterno'], max_chars=50)
                nuevo_apellido_materno = col3.text_input("Apellido Materno", value=usuario_actual['apellido_materno'], max_chars=50)

                col4, col5, col6 = st.columns(3)
                nuevo_apodo = col4.text_input("Apodo", value=usuario_actual['apodo'], max_chars=50)
                nuevo_email = col5.text_input("Email", value=usuario_actual['email'] if usuario_actual['email'] else "", max_chars=50)
                ingreso_mensual = col6.number_input("Ingreso Mensual", min_value=0, value=int(usuario_actual['ingreso_mensual']) if pd.notna(usuario_actual['ingreso_mensual']) else 0)

                submitted = st.form_submit_button("Actualizar Usuario")
                
                if submitted:
                    if not nuevo_nombre or not nuevo_apellido_paterno or not nuevo_apellido_materno or not nuevo_apodo or ingreso_mensual<=0:
                        st.error("Todos los datos son obligatorios (excepto email)")
                    else:
                        try:
                            with conn.session as s:
                                sql = text("UPDATE tbl_usuarios SET nombre = :nombre, apellido_paterno = :apellido_paterno, apellido_materno = :apellido_materno, apodo = :apodo, email = :email, ingreso_mensual=:ingreso_mensual "
                                            "WHERE idusuario = :idusuario")
                                s.execute(
                                    sql,
                                    {
                                        "nombre": nuevo_nombre.strip(),
                                        "apellido_paterno": nuevo_apellido_paterno.strip(),
                                        "apellido_materno": nuevo_apellido_materno.strip(),
                                        "apodo": nuevo_apodo.strip(),
                                        "email": nuevo_email.strip() if nuevo_email else None,
                                        "ingreso_mensual": ingreso_mensual,
                                        "idusuario": usuario_id
                                    }
                                )
                                s.commit()
                                st.session_state.success_message = f"¡Usuario {nuevo_nombre.strip()} actualizado exitosamente!"
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {str(e)}")

#CODIGO PARA PROBARLAS FUNCIONES SIN NECESIDAD DE HACER CAMBIOS EN DB 
# --- PASO 1: AÑADIR UN CHECKBOX PARA EL MODO DE PRUEBA (COLOCAR ANTES DE BOTON DE SUBMIT)---
""" is_dry_run = st.checkbox("Modo de prueba (no guardar en la BD)", value=True) """
# --- PASO 2: MODIFICAR LA SECCIÓN DE SUBMIT PARA INCLUIR ROLLBACK EN MODO DE PRUEBA (DESPUES DEL S.EXECUTE())---
""" if is_dry_run:
    s.rollback()
    st.info("MODO DE PRUEBA: El INSERT se ejecutó y se revirtió (ROLLBACK). No se guardaron datos.")
else:
    s.commit()
    st.session_state.success_message = "¡Categoría '...' guardada exitosamente!"
    st.rerun()
"""