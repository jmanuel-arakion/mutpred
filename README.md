# mutpred — Preparación de estructuras PDB para predicción de mutaciones

Herramienta para descargar estructuras proteicas del [Protein Data Bank (RCSB)](https://www.rcsb.org/), extraer un modelo y una cadena específicos, y generar archivos PDB y FASTA listos para análisis posteriores (predicción de mutaciones, conservación evolutiva, etc.).

## Características

- Descarga automática de estructuras en formato PDB o mmCIF desde RCSB.
- Selección de modelo (útil para estructuras NMR con múltiples modelos).
- Extracción de una cadena individual.
- Manejo de residuos no estándar (MSE → Met, SEC → Sec, PYL → Pyl).
- Filtrado de localizaciones alternativas (altloc).
- Generación de archivo FASTA con la secuencia de la cadena extraída.

## Requisitos del sistema

- Python 3.8 o superior
- `pip` (gestor de paquetes de Python)
- Conexión a internet (para descargar estructuras de RCSB)

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/jtuxman/mutpred.git
cd mutpred
```

### 2. (Recomendado) Crear un entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Las librerías necesarias son:

| Librería | Versión mínima | Descripción |
|---|---|---|
| **requests** | ≥ 2.20 | Cliente HTTP para descargar archivos de RCSB PDB |
| **biopython** | ≥ 1.79 | Parsing de estructuras PDB/mmCIF, extracción de cadenas y secuencias |

## Uso

```bash
# Uso básico: descarga PDB 1V90, extrae cadena A
python prepare_pdb.py --pdb 1V90 --chain A --outdir data

# Seleccionar un modelo específico (ej. modelo 0 de estructura NMR)
python prepare_pdb.py --pdb 1V90 --chain A --model 0 --outdir data

# Con prefijo personalizado para los archivos de salida
python prepare_pdb.py --pdb 1V90 --chain A --model 0 --outdir data --prefix mi_proteina
```

### Argumentos

| Argumento | Requerido | Descripción |
|---|---|---|
| `--pdb` | Sí | Código PDB (ej. `1V90`, `4HHB`) |
| `--chain` | Sí | Cadena a extraer (ej. `A`, `B`) |
| `--model` | No | ID del modelo a usar (por defecto: el primero) |
| `--outdir` | No | Directorio de salida (por defecto: `data`) |
| `--prefix` | No | Prefijo para archivos de salida (por defecto: `<pdb>_<chain>_m<model>`) |

### Archivos generados

Para `--pdb 1V90 --chain A --model 0 --outdir data`:

```
data/
├── 1v90.pdb              # Estructura original descargada
├── 1v90_A_m0.chain.pdb   # Cadena A, modelo 0 en formato PDB
└── 1v90_A_m0.fasta       # Secuencia FASTA de la cadena extraída
```

## Licencia

MIT
