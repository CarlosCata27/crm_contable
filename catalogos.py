import streamlit as st
from connection_db import get_db_connection
import pandas as pd

def administrar_catalogos():
    st.header("📚 Administración de Catálogos")
    
    # Selector de catálogo
    catalogo = st.selectbox(
        "Seleccionar Catálogo", 
        ["Categorías de Gastos", "Tarjetas", "Usuarios"],
        key="catalogo_selector"
    )
    
    # Conexión a la base de datos
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        if catalogo == "Categorías de Gastos":
            administrar_categorias(cur, conn)
        elif catalogo == "Tarjetas":
            administrar_tarjetas(cur, conn)
        elif catalogo == "Usuarios":
            administrar_usuarios(cur, conn)

def administrar_categorias(cur, conn):
    st.subheader("Categorías de Gastos")
    
    # Selector de acción: Agregar o Editar
    accion = st.radio("Acción", ["Agregar nueva categoría", "Editar categoría existente"], horizontal=True)
    
    # Mostrar categorías existentes
    cur.execute("SELECT idcategoriagasto, nombre, tipo FROM cat_categoriagasto ORDER BY tipo, nombre")
    categorias = cur.fetchall()
    
    if categorias:
        st.write("### Categorías Existentes")
        df_categorias = pd.DataFrame(categorias, columns=["ID", "Nombre", "Tipo"])
        st.dataframe(df_categorias)
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
                        cur.execute(
                            "INSERT INTO cat_categoriagasto (nombre, tipo) VALUES (%s, %s)",
                            (nombre.strip(), tipo)
                        )
                        conn.commit()
                        st.success("¡Categoría agregada exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")
    else:  # Editar categoría existente
        if not categorias:
            st.warning("No hay categorías disponibles para editar")
            return
            
        # Seleccionar categoría a editar
        categorias_opciones = [f"{nombre} (ID: {id})" for id, nombre, _ in categorias]
        categoria_seleccionada = st.selectbox("Seleccione categoría a editar", options=categorias_opciones)
        
        # Obtener ID de la categoría seleccionada
        categoria_id = int(categoria_seleccionada.split("ID: ")[1].replace(")", ""))
        
        # Obtener datos actuales de la categoría
        cur.execute("SELECT nombre, tipo FROM cat_categoriagasto WHERE idcategoriagasto = %s", (categoria_id,))
        categoria_actual = cur.fetchone()
        
        if categoria_actual:
            with st.form("editar_categoria_form"):
                st.write(f"### Editando categoría: {categoria_actual[0]}")
                nuevo_nombre = st.text_input("Nombre", value=categoria_actual[0], max_chars=50)
                nuevo_tipo = st.selectbox("Tipo", ["Fijo", "Variable"], 
                                         index=0 if categoria_actual[1] == "Fijo" else 1)
                
                submitted = st.form_submit_button("Actualizar Categoría")
                
                if submitted:
                    try:
                        cur.execute(
                            "UPDATE cat_categoriagasto SET nombre = %s, tipo = %s WHERE idcategoriagasto = %s",
                            (nuevo_nombre.strip(), nuevo_tipo, categoria_id)
                        )
                        conn.commit()
                        st.success("¡Categoría actualizada exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {str(e)}")

def administrar_tarjetas(cur, conn):
    st.subheader("Tarjetas")
    
    # Selector de acción: Agregar o Editar
    accion = st.radio("Acción", ["Agregar nueva tarjeta", "Editar tarjeta existente"], horizontal=True)
    
    # Obtener usuarios para asignación
    cur.execute("SELECT idusuario, nombre FROM tbl_usuarios")
    usuarios = cur.fetchall()
    usuarios_opciones = ["(Sin usuario asignado)"] + [f"{nombre} (ID: {id})" for id, nombre in usuarios]
    usuario_id_map = {f"{nombre} (ID: {id})": id for id, nombre in usuarios}
    
    # Mostrar tarjetas existentes
    cur.execute("""
        SELECT t.idtarjeta, t.nombre, u.nombre AS usuario 
        FROM cat_tarjetas t
        LEFT JOIN tbl_usuarios u ON u.idusuario = t.idusuario
        ORDER BY t.nombre
    """)
    tarjetas = cur.fetchall()
    
    if tarjetas:
        st.write("### Tarjetas Existentes")
        df_tarjetas = pd.DataFrame(tarjetas, columns=["ID", "Nombre", "Usuario Asignado"])
        st.dataframe(df_tarjetas)
    else:
        st.info("No hay tarjetas registradas")
    
    if accion == "Agregar nueva tarjeta":
        # Formulario para nueva tarjeta
        with st.form("nueva_tarjeta_form", clear_on_submit=True):
            st.write("### Agregar Nueva Tarjeta")
            nombre = st.text_input("Nombre de la Tarjeta", max_chars=50)
            usuario_asignado = st.selectbox("Usuario Asignado", usuarios_opciones)
            
            submitted = st.form_submit_button("Guardar Tarjeta")
            
            if submitted:
                if not nombre:
                    st.error("El nombre es obligatorio")
                else:
                    try:
                        usuario_id = None
                        if usuario_asignado != "(Sin usuario asignado)":
                            usuario_id = usuario_id_map[usuario_asignado]
                        
                        cur.execute(
                            "INSERT INTO cat_tarjetas (nombre, idusuario) VALUES (%s, %s)",
                            (nombre.strip(), usuario_id)
                        )
                        conn.commit()
                        st.success("¡Tarjeta agregada exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")
    else:  # Editar tarjeta existente
        if not tarjetas:
            st.warning("No hay tarjetas disponibles para editar")
            return
            
        # Seleccionar tarjeta a editar
        tarjetas_opciones = [f"{nombre} (ID: {id})" for id, nombre, _ in tarjetas]
        tarjeta_seleccionada = st.selectbox("Seleccione tarjeta a editar", options=tarjetas_opciones)
        
        # Obtener ID de la tarjeta seleccionada
        tarjeta_id = int(tarjeta_seleccionada.split("ID: ")[1].replace(")", ""))
        
        # Obtener datos actuales de la tarjeta
        cur.execute("SELECT nombre, idusuario FROM cat_tarjetas WHERE idtarjeta = %s", (tarjeta_id,))
        tarjeta_actual = cur.fetchone()
        
        if tarjeta_actual:
            # Determinar usuario actual asignado
            usuario_actual_key = "(Sin usuario asignado)"
            if tarjeta_actual[1]:
                for key, id_val in usuario_id_map.items():
                    if id_val == tarjeta_actual[1]:
                        usuario_actual_key = key
                        break
            
            with st.form("editar_tarjeta_form"):
                st.write(f"### Editando tarjeta: {tarjeta_actual[0]}")
                nuevo_nombre = st.text_input("Nombre", value=tarjeta_actual[0], max_chars=50)
                nuevo_usuario = st.selectbox("Usuario Asignado", usuarios_opciones, 
                                            index=usuarios_opciones.index(usuario_actual_key))
                
                submitted = st.form_submit_button("Actualizar Tarjeta")
                
                if submitted:
                    try:
                        nuevo_usuario_id = None
                        if nuevo_usuario != "(Sin usuario asignado)":
                            nuevo_usuario_id = usuario_id_map[nuevo_usuario]
                        
                        cur.execute(
                            "UPDATE cat_tarjetas SET nombre = %s, idusuario = %s WHERE idtarjeta = %s",
                            (nuevo_nombre.strip(), nuevo_usuario_id, tarjeta_id)
                        )
                        conn.commit()
                        st.success("¡Tarjeta actualizada exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {str(e)}")

def administrar_usuarios(cur, conn):
    st.subheader("Usuarios")
    
    # Selector de acción: Agregar o Editar
    accion = st.radio("Acción", ["Agregar nuevo usuario", "Editar usuario existente"], horizontal=True)
    
    # Mostrar usuarios existentes
    cur.execute("SELECT idusuario, nombre, apellido_paterno, apellido_materno, apodo, email FROM tbl_usuarios")
    usuarios = cur.fetchall()
    
    if usuarios:
        st.write("### Usuarios Existentes")
        df_usuarios = pd.DataFrame(
            usuarios, 
            columns=["ID", "Nombre", "Apellido Paterno", "Apellido Materno", "Apodo", "Email"]
        )
        st.dataframe(df_usuarios)
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

            col4, col5 = st.columns(2)
            apodo = col4.text_input("Apodo", max_chars=50)
            email = col5.text_input("Email", max_chars=50)
            
            submitted = st.form_submit_button("Guardar Usuario")
            
            if submitted:
                if not nombre or not apellido_paterno or not apellido_materno or not apodo:
                    st.error("Todos los datos son obligatorios (excepto email)")
                else:
                    try:
                        cur.execute(
                            "INSERT INTO tbl_usuarios (nombre, apellido_paterno, apellido_materno, apodo, email) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (nombre.strip(), apellido_paterno.strip(), 
                             apellido_materno.strip(), apodo.strip(), email.strip() if email else None)
                        )
                        conn.commit()
                        st.success("¡Usuario agregado exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")
    else:  # Editar usuario existente
        if not usuarios:
            st.warning("No hay usuarios disponibles para editar")
            return
            
        # Seleccionar usuario a editar
        usuarios_opciones = [f"{nombre} {apellido_paterno} (Apodo: {apodo}) (ID: {id})" 
                            for id, nombre, apellido_paterno, apellido_materno, apodo, email in usuarios]
        usuario_seleccionado = st.selectbox("Seleccione usuario a editar", options=usuarios_opciones)
        
        # Obtener ID del usuario seleccionado
        usuario_id = int(usuario_seleccionado.split("ID: ")[1].replace(")", ""))
        
        # Obtener datos actuales del usuario
        cur.execute("SELECT nombre, apellido_paterno, apellido_materno, apodo, email FROM tbl_usuarios WHERE idusuario = %s", (usuario_id,))
        usuario_actual = cur.fetchone()
        
        if usuario_actual:
            with st.form("editar_usuario_form"):
                st.write(f"### Editando usuario: {usuario_actual[0]}")
                col1, col2, col3 = st.columns(3)
                nuevo_nombre = col1.text_input("Nombre", value=usuario_actual[0], max_chars=50)
                nuevo_apellido_paterno = col2.text_input("Apellido Paterno", value=usuario_actual[1], max_chars=50)
                nuevo_apellido_materno = col3.text_input("Apellido Materno", value=usuario_actual[2], max_chars=50)

                col4, col5 = st.columns(2)
                nuevo_apodo = col4.text_input("Apodo", value=usuario_actual[3], max_chars=50)
                nuevo_email = col5.text_input("Email", value=usuario_actual[4] if usuario_actual[4] else "", max_chars=50)
                
                submitted = st.form_submit_button("Actualizar Usuario")
                
                if submitted:
                    if not nuevo_nombre or not nuevo_apellido_paterno or not nuevo_apellido_materno or not nuevo_apodo:
                        st.error("Todos los datos son obligatorios (excepto email)")
                    else:
                        try:
                            cur.execute(
                                "UPDATE tbl_usuarios SET nombre = %s, apellido_paterno = %s, apellido_materno = %s, apodo = %s, email = %s "
                                "WHERE idusuario = %s",
                                (nuevo_nombre.strip(), nuevo_apellido_paterno.strip(), 
                                 nuevo_apellido_materno.strip(), nuevo_apodo.strip(), 
                                 nuevo_email.strip() if nuevo_email else None, usuario_id)
                            )
                            conn.commit()
                            st.success("¡Usuario actualizado exitosamente!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {str(e)}")