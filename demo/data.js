// DATOS SINTÉTICOS: sirven para probar la aplicación, no son mediciones.
// Coordenadas en grados; temperaturas superficiales en °C.
// minerales: porcentajes de [plagioclasa, piroxeno, olivino], normalizados a 100.
// Solo se representan estas tres familias, no toda la composición de la roca.
const minerales = ['Plagioclasa', 'Piroxeno', 'Olivino'];

const muestrasLuna = [
  { lat: 0.67, lon: 23.47, roca: 'Basalto', min: -173, max: 107, minerales: [45, 50, 5] },
  { lat: 1.20, lon: 23.90, roca: 'Basalto', min: -170, max: 110, minerales: [40, 50, 10] },
  { lat: 0.20, lon: 22.80, roca: 'Basalto', min: -176, max: 105, minerales: [50, 45, 5] },
  { lat: 2.50, lon: 25.00, roca: 'Basalto', min: -168, max: 113, minerales: [35, 50, 15] },
  { lat: -43.31, lon: -11.36, roca: 'Anortosita', min: -180, max: 85, minerales: [90, 8, 2] },
  { lat: -43.80, lon: -10.80, roca: 'Anortosita', min: -183, max: 82, minerales: [85, 12, 3] },
  { lat: -42.70, lon: -12.00, roca: 'Anortosita', min: -178, max: 89, minerales: [95, 4, 1] },
  { lat: -41.00, lon: -9.00, roca: 'Anortosita', min: -175, max: 94, minerales: [80, 15, 5] },
  { lat: 9.62, lon: -20.08, roca: 'Brecha', min: -175, max: 100, minerales: [65, 30, 5] },
  { lat: 10.10, lon: -20.50, roca: 'Brecha', min: -172, max: 103, minerales: [60, 30, 10] },
  { lat: 9.00, lon: -19.50, roca: 'Brecha', min: -178, max: 98, minerales: [70, 25, 5] },
  { lat: 12.00, lon: -18.00, roca: 'Brecha', min: -169, max: 109, minerales: [55, 30, 15] },
];

// Los lugares existen, pero sus perfiles numéricos también son inventados.
const lugaresTierra = [
  { nombre: 'Lanzarote', pais: 'España', lat: 29.01, lon: -13.75, roca: 'Basalto', min: 8, max: 58, minerales: [45, 45, 10] },
  { nombre: 'Mauna Loa', pais: 'Estados Unidos', lat: 19.48, lon: -155.61, roca: 'Basalto', min: -5, max: 45, minerales: [40, 45, 15] },
  { nombre: 'Desierto de Atacama', pais: 'Chile', lat: -24.50, lon: -69.25, roca: 'Andesita', min: -15, max: 55, minerales: [65, 30, 5] },
  { nombre: 'Macizo de Nain', pais: 'Canadá', lat: 56.55, lon: -61.68, roca: 'Anortosita', min: -35, max: 25, minerales: [90, 8, 2] },
  { nombre: 'Ofiolita de Semail', pais: 'Omán', lat: 23.15, lon: 57.30, roca: 'Peridotita', min: 12, max: 65, minerales: [5, 20, 75] },
  { nombre: 'Campo de lava de Ódáðahraun', pais: 'Islandia', lat: 65.00, lon: -17.00, roca: 'Basalto', min: -25, max: 30, minerales: [50, 40, 10] },
];
