# Neo4j Schema Documentation

This document outlines the Neo4j graph database schema for the IFC to Neo4j Knowledge Graph project, including the enhanced topological relationships.

## Node Labels

### Core Node Labels

| Label          | Description                                     | Example IFC Types              |
|----------------|-------------------------------------------------|-------------------------------|
| `Project`      | IFC Project entity                              | IfcProject                    |
| `Site`         | Site in the building model                      | IfcSite                       |
| `Building`     | Building in the model                           | IfcBuilding                   |
| `Storey`       | Building storey (level/floor)                   | IfcBuildingStorey             |
| `Space`        | Spatial element (room, zone, etc.)              | IfcSpace                      |
| `Element`      | Base label for all physical elements            | IfcElement (abstract)         |
| `Wall`         | Wall element                                    | IfcWall, IfcWallStandardCase  |
| `Window`       | Window element                                  | IfcWindow                     |
| `Door`         | Door element                                    | IfcDoor                       |
| `Slab`         | Slab element (floors, roofs)                    | IfcSlab                       |
| `Beam`         | Beam element                                    | IfcBeam                       |
| `Column`       | Column element                                  | IfcColumn                     |
| `Railing`      | Railing element                                 | IfcRailing                    |
| `Furniture`    | Furniture element                               | IfcFurniture                  |
| `Material`     | Material definition                             | IfcMaterial                   |
| `PropertySet`  | Property set container                          | IfcPropertySet               |
| `Property`     | Individual property                             | IfcProperty                   |
| `Type`         | Type definition                                 | IfcElementType                |

### Topological Node Labels

These labels can be applied to elements to indicate their topological representation:

| Label      | Description                                        |
|------------|----------------------------------------------------|
| `Cell`     | 3D volumetric entity (typically spaces)            |
| `Face`     | 2D surface entity (typically walls, slabs, etc.)   |
| `Edge`     | 1D linear entity (typically beams, columns, etc.)  |
| `Vertex`   | 0D point entity                                    |

## Relationship Types

### Core Relationships

| Relationship Type   | Description                                           | Source → Target          |
|---------------------|-------------------------------------------------------|--------------------------|
| `CONTAINS`          | Spatial containment relationship                      | Site → Building         |
| `DEFINES`           | Type definition relationship                          | Type → Element          |
| `HAS_PROPERTY_SET`  | Element to property set relationship                  | Element → PropertySet   |
| `HAS_PROPERTY`      | Property set to property relationship                 | PropertySet → Property  |
| `IS_MADE_OF`        | Material association                                  | Element → Material      |
| `CONNECTED_TO`      | Physical connection between elements                  | Element → Element       |
| `BOUNDED_BY`        | Space boundary (derived from IFC)                     | Space → Element         |
| `HOSTED_BY`         | Opening in element                                    | Opening → Element       |
| `FILLS`             | Door/window fills opening                             | Door/Window → Opening   |
| `ADJACENT_TO`       | Adjacent elements (derived from IFC)                  | Element → Element       |
| `GROUPS`            | Element grouping                                      | Group → Element         |

### Topological Relationships

These relationships are derived from topological analysis:

| Relationship Type         | Description                                             | Source → Target             | Properties                                |
|---------------------------|---------------------------------------------------------|-----------------------------|-----------------------------------------|
| `ADJACENT`                | Elements are physically adjacent                         | Element → Element           | distanceTolerance, sharedFaceCount, etc. |
| `CONTAINS_TOPOLOGICALLY`  | One element contains another topologically               | Element → Element           | distanceTolerance, volume, etc.          |
| `IS_CONTAINED_IN`         | Inverse of CONTAINS_TOPOLOGICALLY                        | Element → Element           | distanceTolerance, volume, etc.          |
| `BOUNDS_SPACE`            | Element forms a boundary of a space                      | Element → Space             | boundaryType, area, etc.                 |
| `IS_BOUNDED_BY`           | Space is bounded by an element                           | Space → Element             | boundaryType, area, etc.                 |
| `CONNECTS_SPACES`         | Element (e.g., door) connects spaces                     | Element → Space             | connectionType, isPassable, etc.         |
| `PATH_TO`                 | A navigable path exists between elements                 | Element → Element           | pathLength, stepCount, etc.              |

## Node Properties

Common properties for nodes include:

| Property Name    | Description                                  | Example Value            |
|------------------|----------------------------------------------|--------------------------|
| `GlobalId`       | Unique identifier from IFC                   | "2O2Fr$t4X7Zf8NOew3FNr2" |
| `Name`           | Name of the element                          | "Wall-01"                |
| `Description`    | Description of the element                   | "External Wall"          |
| `IFCType`        | IFC entity type                              | "IfcWall"                |
| `objectType`     | Object type from IFC                         | "STANDARD"               |
| `tag`            | Tag value from IFC                           | "W001"                   |
| `predefinedType` | Predefined type from IFC                     | "STANDARD"               |
| `topologicEntity`| Type of topological entity                   | "Cell", "Face", "Edge"   |

## Relationship Properties

Common properties for topological relationships include:

### ADJACENT Properties

| Property Name       | Description                                        | Example Value        |
|---------------------|----------------------------------------------------|----------------------|
| `relationshipSource`| Source of the relationship data                    | "topologicalAnalysis"|
| `distanceTolerance` | Tolerance used for adjacency detection             | 0.001                |
| `sharedFaceCount`   | Number of shared faces                             | 1                    |
| `sharedEdgeCount`   | Number of shared edges                             | 2                    |
| `sharedVertexCount` | Number of shared vertices                          | 4                    |
| `contactArea`       | Area of contact surface                            | 15.25                |

### CONTAINS_TOPOLOGICALLY Properties

| Property Name       | Description                                        | Example Value        |
|---------------------|----------------------------------------------------|----------------------|
| `relationshipSource`| Source of the relationship data                    | "topologicalAnalysis"|
| `distanceTolerance` | Tolerance used for containment detection           | 0.001                |
| `volume`            | Volume of containment                              | 125.5                |
| `containmentType`   | Type of containment (full or partial)              | "full"               |

### BOUNDS_SPACE Properties

| Property Name       | Description                                        | Example Value        |
|---------------------|----------------------------------------------------|----------------------|
| `relationshipSource`| Source of the relationship data                    | "topologicalAnalysis"|
| `boundaryType`      | Type of boundary (physical, virtual, etc.)         | "physical"           |
| `area`              | Area of boundary surface                           | 12.5                 |
| `normalVector`      | Normal vector of boundary surface                  | "[0,1,0]"            |

### CONNECTS_SPACES Properties

| Property Name       | Description                                        | Example Value        |
|---------------------|----------------------------------------------------|----------------------|
| `relationshipSource`| Source of the relationship data                    | "topologicalAnalysis"|
| `connectionType`    | Type of connection (door, window, opening)         | "door"               |
| `isPassable`        | Whether the connection is passable                 | true                 |
| `width`             | Width of connection                                | 0.9                  |
| `height`            | Height of connection                               | 2.1                  |

### PATH_TO Properties

| Property Name       | Description                                        | Example Value        |
|---------------------|----------------------------------------------------|----------------------|
| `relationshipSource`| Source of the relationship data                    | "topologicalAnalysis"|
| `pathLength`        | Length of the path                                 | 5.5                  |
| `stepCount`         | Number of steps in the path                        | 3                    |
| `pathType`          | Type of path (direct, through doors, etc.)         | "door-connected"     |
| `isAccessible`      | Whether the path is accessible                     | true                 |

## Constraints and Indexes

### Constraints

The schema defines uniqueness constraints to ensure data integrity:

```cypher
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Element) REQUIRE e.GlobalId IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.GlobalId IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Site) REQUIRE s.GlobalId IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (b:Building) REQUIRE b.GlobalId IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Storey) REQUIRE s.GlobalId IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Space) REQUIRE s.GlobalId IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (m:Material) REQUIRE m.Name IS UNIQUE
CREATE CONSTRAINT IF NOT EXISTS FOR (t:Type) REQUIRE t.GlobalId IS UNIQUE
```

### Indexes

Indexes are created to improve query performance:

```cypher
CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.IFCType)
CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.Name)
CREATE INDEX IF NOT EXISTS FOR (s:Space) ON (s.Name)
CREATE INDEX IF NOT EXISTS FOR (ps:PropertySet) ON (ps.Name)
CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.Name)
CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.topologicEntity)
```

## Example Queries

### Find adjacent elements to a specific wall

```cypher
MATCH (wall:Wall {Name: "Basic Wall:Generic - 200mm"})-[r:ADJACENT]->(element)
RETURN wall.Name as WallName, element.IFCType as ElementType, element.Name as ElementName
```

### Find spaces connected by doors

```cypher
MATCH (space1:Space)-[:IS_BOUNDED_BY]->(door:Door),
      (door)-[:BOUNDS_SPACE]->(space2:Space)
WHERE space1 <> space2
RETURN space1.Name as Space1, door.Name as Door, space2.Name as Space2
```

### Find containment hierarchy with topological relationships

```cypher
MATCH path = (building:Building)-[:CONTAINS*1..3]->(element:Element)
RETURN building.Name as Building, 
       [node in nodes(path)[1..-1] | node.Name] as Path,
       element.Name as Element,
       element.IFCType as ElementType
```

### Find shortest path between two spaces using topological relationships

```cypher
MATCH path = shortestPath((space1:Space {Name: "Room 101"})-[:ADJACENT|CONNECTS_SPACES*]-(space2:Space {Name: "Room 102"}))
RETURN [node in nodes(path) | node.Name] as PathNodes,
       [relationship in relationships(path) | type(relationship)] as RelTypes
``` 