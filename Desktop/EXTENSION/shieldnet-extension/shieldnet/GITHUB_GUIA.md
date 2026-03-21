# 🐙 Cómo subir ShieldNet a GitHub (guía para el equipo)

## Primera vez — Solo quien sube el proyecto (tú)

### 1. Instalar Git
Descarga desde: https://git-scm.com/download/win
Instalar con todas las opciones por default.

### 2. Crear cuenta en GitHub
Ve a https://github.com y regístrate gratis.

### 3. Crear el repositorio en GitHub
1. Clic en el botón verde **"New"** (o el "+" arriba a la derecha)
2. Repository name: `shieldnet-extension`
3. Descripción: `Extensión de seguridad web — proyecto escolar`
4. Seleccionar **Public** (para que tus amigos lo vean gratis)
5. Clic en **"Create repository"**

### 4. Subir el proyecto desde tu PC
Abre **Git Bash** (se instala con Git) dentro de la carpeta `shieldnet/` y escribe:

```bash
git init
git add .
git commit -m "primer commit — ShieldNet v1.0"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/shieldnet-extension.git
git push -u origin main
```
> Cambia TU_USUARIO por tu nombre de usuario de GitHub

---

## Cuando hagas cambios — Subir actualizaciones

Cada vez que modifiques archivos:

```bash
git add .
git commit -m "descripción de qué cambiaste"
git push
```

Ejemplos de mensajes de commit:
- `"arreglo adblock youtube"`
- `"agrego nuevos dominios a lista negra"`
- `"mejoro detector de phishing"`

---

## Tus amigos — Descargar el proyecto por primera vez

```bash
git clone https://github.com/TU_USUARIO/shieldnet-extension.git
```

Eso les crea la carpeta `shieldnet-extension/` con todo el código.
Luego la cargan en `chrome://extensions` como siempre.

---

## Tus amigos — Cuando subes una actualización

Solo tienen que abrir Git Bash dentro de la carpeta del proyecto y escribir:

```bash
git pull
```

Y listo — tienen los cambios más recientes. Después recargan la extensión en `chrome://extensions` con el botón 🔄.

---

## Si alguien del equipo quiere subir cambios también

Primero tienes que darles acceso:
1. Ve a tu repo en GitHub
2. Settings → Collaborators → Add people
3. Pones el usuario de GitHub de tu amigo/a

Ellos hacen los cambios y suben así:
```bash
git add .
git commit -m "lo que cambiaron"
git push
```

Y tú bajas sus cambios con:
```bash
git pull
```

---

## Resumen rápido del flujo

```
Tú haces cambios → git add . → git commit -m "mensaje" → git push
Tus amigos actualizan → git pull → recargan extensión en chrome://extensions
```

---

## Archivo .gitignore recomendado
Crea un archivo llamado `.gitignore` en la carpeta del proyecto con esto:

```
*.zip
.DS_Store
Thumbs.db
node_modules/
```

Esto evita subir archivos innecesarios al repo.
