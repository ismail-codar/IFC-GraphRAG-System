# TopologicPy IFC Graph Alignment Guide

## 1  Purpose

Provide a step‑by‑step reference for a coding agent to import an IFC file with **TopologicPy**, build a graph enriched with semantic data, clean and analyse that graph, and visualise both the graph and associated geometries.  The guide captures design decisions, parameter choices, and best practices demonstrated in the tutorial video/Jupyter notebook `graph_by_ifc.ipynb`.

---

## 2  Environment Setup

| Task                             | Command / Notes                     |
| -------------------------------- | ----------------------------------- |
| Install **TopologicPy** (latest) | `pip install --upgrade topologicpy` |
| Verify version                   | \`\`\`python                        |
| import topologicpy as tp         |                                     |
| print(tp.**version**)            |                                     |

# Confirms against PyPI and warns if outdated

````|
| (Dev only) Extend the module search path | ```python
import sys
sys.path.append(r"<path‑to‑topologic‑pi‑source>")
``` |

---
## 3  Importing an IFC File
```python
from topologicpy import Graph

ifc_file_path = r"C:/Users/<you>/Downloads/IFC_2x3_Duplex.ifc"
include_types = [
    "IfcSpace", "IfcSlab", "IfcRoof", "IfcWall", "IfcWallStandardCase",
    "IfcDoor", "IfcWindow"
]

graph = Graph.ByIFCPath(
    ifc_file_path,
    includeTypes=include_types,       # optional → import all if omitted
    transferDictionaries=True,        # attach IFC attributes to graph vertices
    useInternalVertex=True,           # guarantee vertex inside concave solids
    storeBRep=True,                   # embed B‑Rep as long string in dictionary
    removeCopperFaces=True            # de‑triangulate for cleaner geometry
)
````

### Parameter Insights

| Parameter                | Impact                                                                                                     | Trade‑off                                        |
| ------------------------ | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **transferDictionaries** | Preserves full IFC metadata on each node.                                                                  | Increases memory footprint.                      |
| **useInternalVertex**    | Uses a robust point‑in‑solid method so vertex is *inside* the object (critical for later spatial queries). | Slower import (\~O(n·log n) solid checks).       |
| **storeBRep**            | Allows later geometry reconstruction via `Topology.ByBRepString`.                                          | File → memory bloat; serialises to long strings. |
| **removeCopperFaces**    | Produces planar faces rather than triangulated mesh.                                                       | Extra geometry clean‑up cost.                    |

---

## 4  Cleaning Rogue Vertices

Vertices lacking valid B‑Rep strings (or whose B‑Rep fails to rebuild) are deemed **rogue** and removed.

```python
from topologicpy import Topology

topologies, rogues = [], []
for v in graph.Vertices():
    d = Topology.Dictionary(v)
    b_string = d.Value("BRep")
    if b_string:
        topo = Topology.ByBRepString(b_string)
        if isinstance(topo, Topology):
            Topology.SetDictionary(topo, d)
            topologies.append(topo)
        else:
            rogues.append(v)
    else:
        rogues.append(v)

for rv in rogues:
    graph = Graph.RemoveVertex(graph, rv)  # also drops incident edges
```

---

## 5  Graph Annotation & Metrics

1. **Global dictionary** (for easier legend labelling):

```python
graph = Topology.SetDictionary(graph, Topology.DictionaryByKeyValue("IfcName", "Graph"))
```

2. **Centrality analysis**

```python
centrality = Graph.ClosenessCentrality(graph)
for v in graph.Vertices():
    d = Topology.Dictionary(v)
    score = d.Value("closeness_centrality")
    d = Topology.DictionaryByKeyValue("closeness_centrality", score*20 + 4, d)
    Topology.SetDictionary(v, d)
```

The scaled score drives **vertex size** when plotting.

---

## 6  Visualisation

```python
from topologicpy import Topology

Topology.Show(
    graph,
    nameKey="IfcName",
    sagitta=0.05,          # curved edges (5 % of edge length)
    faceOpacity=0.1,
    vertexSizeKey="closeness_centrality",
    vertexLabelKey="IfcName",
    vertexGroupKey="IfcType",
    groups=["IfcSpace","IfcSlab","IfcRoof","IfcWall","IfcDoor","IfcWindow","Unknown"],
    legend=False,
    backgroundColour="white",
    size=[1024,900]
)
```

### Tips

* **Include `topologies`** in the argument list to render solids alongside the graph.
* Adjust *sagitta* or set `absolute=True` for a fixed pixel offset.

---

## 7  Connected Components (Graph Islands)

```python
components = Graph.ConnectedComponents(graph)
# Returned list is sorted by descending vertex count
primary = components[0]
```

Visualise individual islands:

```python
Topology.Show(components[:3])  # first three islands
```

---

## 8  Performance Benchmarks

| Operation                       | Notes                  | Example Time\*          |
| ------------------------------- | ---------------------- | ----------------------- |
| IFC import (with options above) | Large duplex model     | **≈ 1 min 46 s**        |
| Computing closeness centrality  | O(V+E) BFS per node    | negligible after import |
| Connected components            | Union‑find linear time | negligible              |

\*Measured on a typical dev laptop; times vary with model size and CPU.

---

## 9  Best Practices & Pitfalls

* **Selective import** (`includeTypes`) drastically reduces memory & parsing time.
* Always clean *rogue vertices* before analysis to avoid misleading metrics.
* Internal vertices are essential for point‑in‑solid queries but expensive—disable for quick exploratory loads.
* IFC graphs may be *disconnected* even for geometrically continuous buildings; for spatial reasoning prefer building a **Cell Complex** and its dual graph.
* Serialised B‑Reps inflate notebooks; consider external caching or on‑demand reconstruction.

---

## 10  Alignment Checklist for Coding Agent

1. 🔄 **Version check**: Warn if running TopologicPy < required version.
2. 📂 **Path abstraction**: Accept IFC path and includeTypes as parameters / CLI flags.
3. 🧹 **Integrity guardrails**:

   * Validate `Topology.ByBRepString` success.
   * Log rogue vertices and counts.
4. 🗄️ **Data persistence**: Offer toggles for `storeBRep` & internal vertices.
5. 📊 **Metric hooks**: Expose closeness, betweenness, degree centrality as pluggable analysers.
6. 🖼️ **Rendering presets**: Provide high‑contrast theme and export to PNG/SVG.
7. 🧪 **Unit tests**:fixture small IFC sample; assert vertex count after clean‑up; assert ≥ 1 connected component.

---

## 11  References

* **TopologicPy** docs: [https://topologic.app](https://topologic.app)
* IFC sample: `IFC_2x3_Duplex_Different.ifc` (BuildingSMART)
* Jupyter notebook: `graph_by_ifc.ipynb` in the notebook folder of the project repo.

---

### © 2025 Your Name — Released under MIT licence

