# Site evaluation: port_royal

Property: 3.995 acres, 1 parcels. Thresholds: slope <= 15%, setback 25 ft, stream buffer 100 ft, wetland buffer 50 ft.

## 1. Buildable area

- **Buildable: 0.797 acres (19.9% of property)**
- If slopes up to 25% were accepted: 2.841 acres
- Area removed by each constraint (overlapping): steep 2.90 ac, setback 1.06 ac, flood 0.00 ac, wetland_buffer 0.00 ac

_No contiguous buildable patch of at least 0.25 acres._

### By parcel

|   PARCELID |   parcel_acres |   buildable_acres |   buildable_pct |   steep_acres |
|-----------:|---------------:|------------------:|----------------:|--------------:|
|     505727 |          3.995 |             0.797 |            19.9 |           2.9 |

## 2. Sun exposure

- Latitude 40.0489. A flat, unshaded site here gets 8.5 h of sun on Dec 21.
- Mean direct sun on Dec 21: 7.9 h over the property, 8.1 h over the buildable area
- Mean direct sun Mar 21: 10.9 h; Jun 21: 13.4 h
- Winter solar index (direct-beam energy relative to flat unshaded ground, Dec 21): 1.17 over the property, 1.06 over the buildable area. South slopes score above 1, north slopes below.
- South-facing or flat ground: 49.0% of property
- Buildable ground with at least 4 h of winter sun: 0.796 acres
- Shading is from terrain only (bare-earth DEM). Tree canopy and neighbouring houses are not modelled.

### Aspect

| aspect     |   acres |   buildable_acres |   pct |
|:-----------|--------:|------------------:|------:|
| flat (<3%) |   0.045 |             0.04  |   1.1 |
| N          |   0.005 |             0.002 |   0.1 |
| NE         |   0.002 |             0.002 |   0.1 |
| E          |   0.005 |             0.003 |   0.1 |
| SE         |   0.11  |             0.01  |   2.8 |
| S          |   1.164 |             0.103 |  29.1 |
| SW         |   0.638 |             0.23  |  16   |
| W          |   1.653 |             0.358 |  41.4 |
| NW         |   0.373 |             0.05  |   9.3 |

### By parcel

|   PARCELID |   dec21_sun_hours_mean |   dec21_solar_index |   jun21_sun_hours_mean |   south_or_flat_pct |
|-----------:|-----------------------:|--------------------:|-----------------------:|--------------------:|
|     505727 |                    7.9 |                1.17 |                   13.4 |                  49 |

## 3. Stormwater

- Run-on: 13.55 acres of off-site land drain onto the property
- Concentrated flow paths (>= 1.0 ac contributing) inside property: about 270 ft
- Depressions that would pond (> 0.5 ft deep): 0.000 acres

### Where runoff leaves the property

|   contributing_acres |   parcel |
|---------------------:|---------:|
|                14.84 |   505727 |
|                 0.41 |   505727 |

### Soils (SSURGO, dominant component)

- Hydrologic soil groups: {'B': 100.0} (A/B infiltrate well, C/D shed runoff): **100.0% good infiltration**
- Hydric soils: 0.000 acres; poorly drained: 0.000 acres
- Shallowest restrictive layer: 210 cm

| musym   | muname                                                           | hydgrp   | drainagecl   | hydricrating   |   acres |   pct |
|:--------|:-----------------------------------------------------------------|:---------|:-------------|:---------------|--------:|------:|
| McE     | Manor and Chester extremely stony loams, 25 to 50 percent slopes | B        | Well drained | No             |   1.544 |  38.6 |
| MaD     | Manor loam, 15 to 25 percent slopes                              | B        | Well drained | No             |   1.42  |  35.5 |
| MaC     | Manor loam, 8 to 15 percent slopes                               | B        | Well drained | No             |   0.843 |  21.1 |
| MaB     | Manor loam, 3 to 8 percent slopes                                | B        | Well drained | No             |   0.188 |   4.7 |

## 4. Growing ground

- Garden-grade ground (slope <= 8%, >= 8 h June sun, soil not wet): **0.188 acres**
- Orchard / terrace ground (slope <= 20%): 2.169 acres; pasture / meadow (slope <= 25%): 0.734 acres; wet ground: 0.000 acres; woodlot: 0.847 acres
- Cultivable ground (garden + orchard) that is NOT in the buildable area: 1.591 acres
- Usable for building, growing or grazing combined: 3.122 acres (78.1%)
- USDA prime farmland soils: 0.188 acres; farmland of statewide importance: 0.840 acres
- Mean June 21 sun over the property: 13.4 h (terrain shading only)

- Tree canopy (mapped): covers 55.9% of the property; 0.430 acres of buildable and 1.439 acres of garden/orchard ground are under canopy today

### By class

| class                     |   acres |   pct |   outside_buildable_acres |   jun21_sun_h_mean |   mar21_sun_h_mean |
|:--------------------------|--------:|------:|--------------------------:|-------------------:|-------------------:|
| garden                    |   0.188 |   4.7 |                     0.05  |               13.8 |               11.3 |
| orchard / terrace         |   2.169 |  54.3 |                     1.541 |               13.6 |               10.9 |
| pasture / meadow          |   0.734 |  18.4 |                     0.734 |               13.3 |               10.7 |
| wet ground                |   0     |   0   |                     0     |              nan   |              nan   |
| woodlot / steep or shaded |   0.847 |  21.2 |                     0.847 |               12.9 |               10.7 |

### By parcel

|   PARCELID |   garden |   orchard / terrace |   pasture / meadow |   wet ground |   woodlot / steep or shaded |
|-----------:|---------:|--------------------:|-------------------:|-------------:|----------------------------:|
|     505727 |    0.188 |               2.169 |              0.734 |            0 |                       0.847 |

## 5. Zoning, services, access

### Zoning

| long_code   |   acres |
|:------------|--------:|
| RSD-1       |   3.995 |

- Public sewer service area coverage: None
- Public water service area coverage: None

### Road frontage (boundary within 40 ft of a centerline)

| road           |   frontage_ft |
|:---------------|--------------:|
| PORT ROYAL AVE |           362 |

### Existing buildings

|   PARCELID | address            | building_name   |   approx_hgt |   square_ft |
|-----------:|:-------------------|:----------------|-------------:|------------:|
|     505727 | 225 PORT ROYAL AVE |                 |           28 |        1704 |
|     505727 | 225 PORT ROYAL AVE |                 |           11 |         719 |

## Maps

map_buildable.png, map_slope.png, map_sun_dec21.png, map_solar_index_dec21.png, map_stormwater.png, map_growing.png
