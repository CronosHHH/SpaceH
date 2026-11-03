// 1. Cálculos: funciones pequeñas que no dependen de la interfaz.
// Devuelve la distancia en km entre dos coordenadas lunares en grados (haversine).
function distanciaLunar(a, b) {
  // Convierte grados a radianes para las operaciones trigonométricas.
  const radianes = grados => grados * Math.PI / 180;
  const diferenciaLat = radianes(b.lat - a.lat);
  const diferenciaLon = radianes(b.lon - a.lon);
  const h = Math.sin(diferenciaLat / 2) ** 2
    + Math.cos(radianes(a.lat)) * Math.cos(radianes(b.lat)) * Math.sin(diferenciaLon / 2) ** 2;
  return 2 * 1737.4 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h))));
}

// Promedia temperaturas (°C) y porcentajes minerales de una lista no vacía de muestras.
function perfilMedio(muestras) {
  // Calcula la media aritmética de una lista no vacía de números.
  const media = valores => valores.reduce((suma, valor) => suma + valor, 0) / valores.length;
  return {
    min: media(muestras.map(muestra => muestra.min)),
    max: media(muestras.map(muestra => muestra.max)),
    minerales: minerales.map((_, i) => media(muestras.map(muestra => muestra.minerales[i]))),
  };
}

// Añade al lugar sus similitudes y puntuación ponderada (0–100) frente al perfil lunar.
// Requiere pesos no negativos con suma mayor que cero y fracciones minerales que sumen 100 %.
function comparar(lugar, perfil, pesoTemperatura, pesoMinerales) {
  const diferenciaTemperatura = (Math.abs(lugar.min - perfil.min) + Math.abs(lugar.max - perfil.max)) / 2;
  const diferenciaMinerales = lugar.minerales.reduce((suma, valor, i) => suma + Math.abs(valor - perfil.minerales[i]), 0);
  const temperatura = 100 * Math.max(0, 1 - diferenciaTemperatura / 200);
  const composicion = 100 * (1 - diferenciaMinerales / 200);
  const puntuacion = (temperatura * pesoTemperatura + composicion * pesoMinerales) / (pesoTemperatura + pesoMinerales);
  return { ...lugar, temperatura, composicion, puntuacion };
}

// 2. Interfaz: leer el formulario, calcular el perfil y mostrar el ranking.
// Busca un elemento HTML por su identificador.
const elemento = id => document.getElementById(id);
const formulario = elemento('controls');
// Formatea un número en español con un máximo de un decimal.
const numero = valor => valor.toLocaleString('es-ES', { maximumFractionDigits: 1 });

// Valida el formulario, filtra las muestras por radio y actualiza mapa, perfil y ranking.
function actualizar() {
  const punto = { lat: elemento('lat').valueAsNumber, lon: elemento('lon').valueAsNumber };
  const radio = elemento('radius').valueAsNumber;
  const pesoTemperatura = elemento('temperature').valueAsNumber;
  const pesoMinerales = elemento('composition').valueAsNumber;
  const total = pesoTemperatura + pesoMinerales;
  elemento('temperature-weight').textContent = `${numero(total ? 100 * pesoTemperatura / total : 0)} %`;
  elemento('composition-weight').textContent = `${numero(total ? 100 * pesoMinerales / total : 0)} %`;

  // Limpiar el resultado anterior evita mostrarlo como válido tras un error.
  elemento('profile').replaceChildren();
  elemento('results').replaceChildren();
  const valido = formulario.checkValidity();
  const muestras = valido ? muestrasLuna.filter(muestra => distanciaLunar(punto, muestra) <= radio) : [];
  elemento('sample-points').innerHTML = muestrasLuna.map(muestra => `
    <circle cx="${muestra.lon + 180}" cy="${90 - muestra.lat}" r="1.5"
      fill="${muestras.includes(muestra) ? '#ffcb83' : '#96adbd'}"><title>${muestra.lat}°, ${muestra.lon}° · ${muestra.roca}</title></circle>
  `).join('');
  elemento('selected-point').style.display = valido ? '' : 'none';
  if (valido) elemento('selected-point').setAttribute('transform', `translate(${punto.lon + 180} ${90 - punto.lat})`);

  if (!valido) {
    elemento('status').textContent = 'Introduce latitud de −90 a 90°, longitud de −180 a 180° y radio de 1 a 1.000 km.';
    return;
  }
  if (total === 0) {
    elemento('status').textContent = 'Asigna un peso mayor que cero a alguna variable.';
    return;
  }
  if (!muestras.length) {
    elemento('status').textContent = 'Sin datos: no hay muestras en este círculo. Amplía el radio o elige uno de los tres ejemplos.';
    return;
  }

  const perfil = perfilMedio(muestras);
  const rocas = [...new Set(muestras.map(muestra => muestra.roca))].join(', ');
  elemento('status').textContent = `${muestras.length} de ${muestrasLuna.length} muestras dentro de ${numero(radio)} km · ${rocas}`;
  elemento('profile').innerHTML = `
    <div class="profile-values">
      <div><span>Media de mínimas superficiales</span><strong>${numero(perfil.min)} °C</strong></div>
      <div><span>Media de máximas superficiales</span><strong>${numero(perfil.max)} °C</strong></div>
    </div>
    <ul class="mineral-list">${minerales.map((mineral, i) => `<li>${mineral}: ${numero(perfil.minerales[i])} %</li>`).join('')}</ul>
    <p class="hint">Perfil sintético de las muestras seleccionadas. Mínimas y máximas sin periodo de observación.</p>`;

  const ranking = lugaresTierra.map(lugar => comparar(lugar, perfil, pesoTemperatura, pesoMinerales))
    .sort((a, b) => b.puntuacion - a.puntuacion);
  elemento('results').innerHTML = `
    <div class="table-scroll"><table>
      <caption class="hint">Similitudes de ejemplo sobre 100 · ${ranking.length} candidatos</caption>
      <thead><tr><th scope="col">Lugar / roca</th><th scope="col">Temperatura</th><th scope="col">Minerales</th><th scope="col">Total</th></tr></thead>
      <tbody>${ranking.map((lugar, i) => `
        <tr>
          <td><a href="https://www.openstreetmap.org/?mlat=${lugar.lat}&mlon=${lugar.lon}#map=10/${lugar.lat}/${lugar.lon}" target="_blank" rel="noopener noreferrer">${i + 1}. ${lugar.nombre} ↗</a><small>${lugar.pais} · ${lugar.roca} · ${lugar.lat}°, ${lugar.lon}°</small></td>
          <td>${numero(lugar.temperatura)}<small>${lugar.min} a ${lugar.max} °C</small></td>
          <td>${numero(lugar.composicion)}<small>${minerales.map((mineral, j) => `${mineral} ${lugar.minerales[j]} %`).join(' · ')}</small></td>
          <td class="score">${numero(lugar.puntuacion)}</td>
        </tr>`).join('')}</tbody>
    </table></div>`;
}

// Recalcula al editar un control y marca como personalizado el punto introducido a mano.
formulario.addEventListener('input', evento => {
  if (['lat', 'lon'].includes(evento.target.id)) elemento('region').value = 'custom';
  actualizar();
});

// Ejecuta la comparación al enviar el formulario, sin recargar la página.
formulario.addEventListener('submit', evento => {
  evento.preventDefault();
  actualizar();
});

// Copia las coordenadas del ejemplo elegido y recalcula sus coincidencias.
elemento('region').addEventListener('change', evento => {
  const muestra = muestrasLuna[Number(evento.target.value)];
  elemento('lat').value = muestra.lat;
  elemento('lon').value = muestra.lon;
  actualizar();
});

// Convierte la posición del clic en coordenadas lunares y compara el nuevo punto.
elemento('moon-map').addEventListener('click', evento => {
  const mapa = evento.currentTarget.getBoundingClientRect();
  elemento('lon').value = Math.max(-180, Math.min(180, (evento.clientX - mapa.left) / mapa.width * 360 - 180)).toFixed(2);
  elemento('lat').value = Math.max(-90, Math.min(90, 90 - (evento.clientY - mapa.top) / mapa.height * 180)).toFixed(2);
  elemento('region').value = 'custom';
  actualizar();
});

// Muestra los resultados iniciales al cargar la página.
actualizar();
