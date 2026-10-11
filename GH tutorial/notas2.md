```bash
git branch        # Muestra todas las ramas locales (* indica la rama activa)
git branch -a     # Muestra ramas locales y remotas (GitHub)
```

MEJOR USAR switch que checkout

* sirven para cambiar te de rama
    * switch main
    * checkout main

* cambiarte a una rama nueva
    * switch -c hotfix/error-login
    * checkout -b hotfix/error-login


## FLECHA DE CREAR NUEVA RAMA

Me dicen que deje lo que este haciendo y me cambie a una nueva rama para arreglar algo

Para eso, hago lo siguiente:

con switch creo una RAMA LOCAL
ahi voy añadiendo mis cambios y commits

y la subo a GITHUB (remoto) con
* git push -u ... #la primera vez
* git push #los demas cambios

GUARDAS LO QUE ESTBAS HACIENDO EN TU RAMA

```bash
# Guerdas tus cambios pendientes o haces commit
git switch main                    # Cambias a main limpiamente
git switch -c hotfix/error-login   # Creas una rama limpia para solucionar el bug
# Corriges el error...
```

## FLECHA DE ABRIR NUEVA RAMA

SE PODRIA HACER GIT PULL REQUEST (PR) para que alguien revise tus cambios y los fusione a main

O 

```bash
# 1. Creas y te cambias a la nueva rama
git switch -c feature/login

# 2. Haces tus cambios y guardas tus commits
git add .
git commit -m "Añade formulario de login"

# 3. La PRIMERA vez que subes la rama
git push -u origin feature/login

# 4. Para los SIGUIENTES cambios en esa misma rama
git push
```


---

Inciso de fetch y merge

*para revisar por la mañanas lo nuevo que han hehco los compas en el codigo ( y no te fias como para hacer un pull)

```bash
git fetch origin/origin

# git diff main origin/main

# Asegúrate de estar en tu rama local
git switch main

# Une los cambios de la referencia remota traída con fetch
git merge origin/main
```

## FLECHA DE CERRAR NUEVA RAMA

### *hacer un compare and pull request* en GitHub

```bash
Sincronizas tu maquina local 
# 1. Regresa a tu rama main local
git switch main[cite: 1]

# 2. Descarga los cambios de GitHub (que ahora ya incluyen tu feature/persona)
git pull[cite: 1]

# 3. Elimina la rama localmente (ya no hace falta porque está en main)
git branch -d feature/persona

# 4. (Opcional) Elimina la rama en GitHub desde la consola (si no le diste al botón en la web)
git push origin --delete feature/persona
```




