# Tutorial de Git

## Índice

1. [Git básico](#git-básico)
2. [Repositorios remotos](#repositorios-remotos)
3. [Ramas](#ramas)
4. [Merge, switch, rebase y fetch](#merge-switch-rebase-y-fetch)
5. [Commits atómicos](#commits-atómicos)
6. [Conventional Commits](#conventional-commits)
7. [Convención de nombres para ramas](#convención-de-nombres-para-ramas)

---

## Git básico

Git es un sistema de control de versiones distribuido. Sirve para registrar cambios, volver a estados anteriores y colaborar con otras personas sin perder el historial del proyecto.

### Configuración inicial

```bash
git config --global user.name "CronosHHH"
git config --global user.email "149625033+CronosHHH@users.noreply.github.com"
```

### Comandos esenciales

```bash
git init
git status
git add ./
git commit -m "mensaje"
git log
```

### Qué hace cada uno

- `git init`: inicializa un repositorio Git en la carpeta actual y crea la carpeta oculta `.git`.
- `git status`: muestra en qué rama estás y qué cambios están listos para añadirse o confirmarse.
- `git add ./`: añade al seguimiento todos los archivos nuevos o modificados del directorio actual.
- `git commit -m "mensaje"`: guarda un cambio en el historial.
- `git log`: muestra el historial de commits.

> Nota: si ya estás dentro de un proyecto y ejecutas `git init`, Git crea la estructura necesaria en esa carpeta. No se usa para "crear el proyecto", sino para convertir una carpeta en repositorio.

---

## Repositorios remotos

Cuando trabajas con GitHub, el repositorio remoto suele llamarse `origin`.

### Conectar un remoto

```bash
git branch -M main
git remote add origin https://github.com/tu_usuario/tu_repo.git
git push -u origin main
```

### Qué significa

- `git branch -M main`: renombra la rama actual a `main`.
- `git remote add origin ...`: vincula tu repositorio local con el repositorio remoto.
- `git push -u origin main`: sube la rama `main` y deja configurado el upstream para no repetirlo después.

### Pull y push

- `git push`: envía tus cambios al remoto.
- `git pull`: trae cambios del remoto y los integra en tu copia local.

---

## Ramas

Las ramas permiten trabajar en cambios aislados sin afectar la rama principal.

### Crear y cambiar de rama

```bash
git branch nombre-rama
git checkout nombre-rama
git checkout -b nombre-rama
```

### Explicación

- `git branch nombre-rama`: crea una rama nueva.
- `git checkout nombre-rama`: cambia a esa rama.
- `git checkout -b nombre-rama`: crea y cambia a la rama en un solo paso.

> Hoy en día, para trabajo diario suele preferirse `git switch` para cambiar de rama y `git restore` para descartar cambios en archivos.

---

## Merge, switch, rebase y fetch

Esta parte completa las operaciones más útiles que faltaban.

### `git switch`

Se usa para cambiar entre ramas de forma más clara que `checkout`.

```bash
git switch main
git switch -c feature/nueva-funcion
```

- `git switch main`: cambia a la rama `main`.
- `git switch -c feature/nueva-funcion`: crea y cambia a una rama nueva.

### `git rebase`

Reescribe la base de una rama para que parezca que empezó desde otro punto del historial.

```bash
git switch feature/nueva-funcion
git rebase main
```

- `rebase` ordena los commits sobre la rama objetivo.
- Suele dar un historial más lineal, pero hay que usarlo con cuidado si la rama ya fue compartida.

### `git merge`

Sirve para unir el historial de una rama dentro de otra.

```bash
git switch main
git merge feature/nueva-funcion
```

- `merge` combina los cambios de `feature/nueva-funcion` con `main`.
- Si ambas ramas tocaron las mismas líneas, Git puede pedir resolver conflictos.

### `git fetch`

Trae información del remoto sin mezclarla automáticamente con tu rama local.

```bash
git fetch origin
```

- `fetch` actualiza referencias remotas como `origin/main`.
- Es útil para revisar cambios antes de hacer `merge` o `rebase`.

> ```text
> git pull = git fetch + git merge
> 
> [GitHub Remoto]
>        |
>        |  1. git fetch (Trae los datos de forma segura)
>        v
> [Historial Local (origin/main)]
>        |
>        |  2. git merge (Une los datos a tus archivos)
>        v
> [Tu Código Actual (main)]
> ```

### Diferencia rápida

- `switch`: cambias de rama.
- `merge`: unes ramas.
- `rebase`: reubicas commits para ordenar el historial.
- `fetch`: traes cambios remotos sin integrarlos todavía.

---

## Commits atómicos

Un commit atómico contiene un solo cambio lógico y específico.

### Idea principal

- Un commit debe resolver una sola cosa.
- Debe ser fácil de entender, revisar y revertir.
- Si hace falta deshacerlo, el impacto debe ser pequeño.

### Ejemplo

- Bien: un commit para corregir un error en un pipeline YAML.
- Bien: otro commit separado para actualizar la documentación.
- Mal: mezclar refactorización, pruebas y cambios de estilo en un único commit sin relación clara.

---

## Conventional Commits

Es una convención para escribir mensajes de commit con un formato claro:

```bash
<tipo>: <descripción como si dieras una orden>
```

### Tipos comunes

- `feat`: añade una funcionalidad nueva.
- `fix`: corrige un bug.
- `docs`: cambia solo documentación.
- `refactor`: reorganiza código sin cambiar su comportamiento.
- `test`: añade o modifica pruebas.
- `chore`: tareas de mantenimiento o configuración.

### Tabla de ejemplos

| Tipo | Propósito | Ejemplo |
| --- | --- | --- |
| `feat` | Añadir una nueva funcionalidad. | `git commit -m "feat: add data cleaning function for text columns"` |
| `fix` | Corregir un error. | `git commit -m "fix: resolve path error in pipeline yaml configuration"` |
| `docs` | Cambiar documentación. | `git commit -m "docs: update ml pipeline architecture section in readme"` |
| `refactor` | Reorganizar código sin cambiar comportamiento. | `git commit -m "refactor: convert jupyter cell logic into modular python functions"` |
| `test` | Añadir o modificar pruebas. | `git commit -m "test: add unit test for text processing module"` |
| `chore` | Tareas de mantenimiento. | `git commit -m "chore: update github actions workflow to v3"` |

> En la práctica, el mensaje debe leerse como una orden breve y concreta sobre lo que hace el cambio.

---

## Convención de nombres para ramas

Las ramas también deben tener nombres claros y orientados a una sola tarea.

### Regla general

Usa un prefijo y una descripción corta con guiones:

```text
<tipo>/<breve-descripcion>
```

### Tabla de ejemplo

| Tipo de rama | Propósito | Ejemplo |
| --- | --- | --- |
| `feature/` o `feat/` | Nueva funcionalidad. | `feature/data-normalization` |
| `bugfix/` o `fix/` | Corrección de errores. | `bugfix/yaml-path-error` |
| `hotfix/` | Parche urgente en producción. | `hotfix/pipeline-auth-crash` |
| `docs/` | Cambios de documentación. | `docs/update-architecture-md` |
| `refactor/` | Limpieza o reestructuración de código. | `refactor/modularize-jupyter` |
| `test/` | Pruebas unitarias o de integración. | `test/unit-processing-module` |
| `chore/` | Mantenimiento o configuración. | `chore/upgrade-azure-cli` |

### Crear una rama

```bash
git switch -c feature/data-normalization
```

---

## Resumen rápido

- `init` crea el repositorio local.
- `status`, `add`, `commit` y `log` cubren el flujo básico diario.
- `switch` cambia de rama, `merge` une ramas, `rebase` reordena historial y `fetch` trae cambios remotos.
- Los commits atómicos y Conventional Commits hacen más legible el historial.
- Los nombres de ramas deben ser cortos, claros y consistentes.
