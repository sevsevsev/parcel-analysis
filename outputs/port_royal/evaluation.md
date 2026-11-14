# Site evaluation: port_royal

Property: 3.995 acres (all parcels merged), 1 parcels. Thresholds: slope <= 15%, setback 25 ft, stream buffer 100 ft, wetland buffer 50 ft.

## 1. Buildable area

- **Buildable: 0.648 acres (16.2% of property)**
- If slopes up to 25% were accepted: 1.885 acres
- Area removed by each constraint (overlapping): steep 2.90 ac, setback 1.06 ac, flood 0.00 ac, wetland_buffer 0.00 ac, drainage_way_buffer 0.67 ac

_No contiguous buildable patch of at least 0.25 acres._

### By parcel

|   PARCELID | address            |   parcel_acres |   buildable_acres |   buildable_pct |   steep_acres |
|-----------:|:-------------------|---------------:|------------------:|----------------:|--------------:|
|     505727 | 225 PORT ROYAL AVE |          3.995 |             0.648 |            16.2 |           2.9 |

## 2. Sun exposure

- Latitude 40.0489. A flat, unshaded site here gets 8.8 h of sun on Dec 21.
- Mean direct sun on Dec 21: 8.0 h over the property, 8.2 h over the buildable area
- Mean direct sun Mar 21: 10.9 h; Jun 21: 13.3 h
- Winter solar index (direct-beam energy relative to flat unshaded ground, Dec 21): 1.17 over the property, 1.05 over the buildable area. South slopes score above 1, north slopes below.
- South-facing or flat ground: 49.0% of property
- Buildable ground with at least 4 h of winter sun: 0.648 acres
- Shading is from terrain only (bare-earth DEM). Tree canopy and neighbouring houses are not modelled.

### Aspect

| aspect     |   acres |   buildable_acres |   pct |
|:-----------|--------:|------------------:|------:|
| flat (<3%) |   0.045 |             0.04  |   1.1 |
| N          |   0.005 |             0.002 |   0.1 |
| NE         |   0.002 |             0.002 |   0.1 |
| E          |   0.005 |             0.003 |   0.1 |
| SE         |   0.11  |             0.01  |   2.8 |
| S          |   1.164 |             0.083 |  29.1 |
| SW         |   0.638 |             0.162 |  16   |
| W          |   1.653 |             0.3   |  41.4 |
| NW         |   0.373 |             0.047 |   9.3 |

### By parcel

|   PARCELID | address            |   dec21_sun_hours_mean |   dec21_solar_index |   jun21_sun_hours_mean |   south_or_flat_pct |
|-----------:|:-------------------|-----------------------:|--------------------:|-----------------------:|--------------------:|
|     505727 | 225 PORT ROYAL AVE |                      8 |                1.17 |                   13.3 |                  49 |

## 3. Stormwater

- Run-on: 13.55 acres of off-site land drain onto the property
- Concentrated flow paths (>= 1.0 ac contributing) inside property: about 270 ft
- Depressions that would pond (> 0.5 ft deep): 0.000 acres

### Where runoff leaves the property

|   contributing_acres | parcel             |
|---------------------:|:-------------------|
|                14.84 | 225 PORT ROYAL AVE |
|                 0.41 | 225 PORT ROYAL AVE |

### Soils (SSURGO, dominant component)

- Hydrologic soil groups: B 100.0% (A and B absorb rain well, C and D shed runoff): **100.0% absorbs well**
- Hydric soils: 0.000 acres; poorly drained: 0.000 acres
- Shallowest restrictive layer: 210 cm (6.9 ft) below the surface

| musym   | muname                                                           | hydgrp   | drainagecl   | hydricrating   |   acres |   pct |
|:--------|:-----------------------------------------------------------------|:---------|:-------------|:---------------|--------:|------:|
| McE     | Manor and Chester extremely stony loams, 25 to 50 percent slopes | B        | Well drained | No             |   1.544 |  38.6 |
| MaD     | Manor loam, 15 to 25 percent slopes                              | B        | Well drained | No             |   1.42  |  35.5 |
| MaC     | Manor loam, 8 to 15 percent slopes                               | B        | Well drained | No             |   0.843 |  21.1 |
| MaB     | Manor loam, 3 to 8 percent slopes                                | B        | Well drained | No             |   0.188 |   4.7 |

## 4. Growing ground

- Garden-grade ground (slope <= 8%, >= 8 h June sun, soil not wet): **0.188 acres**
- Orchard / terrace ground (slope <= 20%): 2.169 acres; pasture / meadow (slope <= 25%): 0.734 acres; wet ground: 0.000 acres; woodlot: 0.847 acres
- Cultivable ground (garden + orchard) that is NOT in the buildable area: 1.740 acres
- Usable for building, growing or grazing combined: 3.122 acres (78.1%)
- USDA prime farmland soils: 0.188 acres; farmland of statewide importance: 0.840 acres
- Mean June 21 sun over the property: 13.3 h (terrain shading only)

- A steep slope regulation covers 95.3% of the property, including 2.193 acres of the garden/orchard ground and 0.720 acres of the pasture ground; clearing or terracing there needs review

- Tree canopy (mapped): covers 55.9% of the property; 0.336 acres of buildable and 1.439 acres of garden/orchard ground are under canopy today

### By class

| class                     |   acres |   pct |   outside_buildable_acres |   jun21_sun_h_mean |   mar21_sun_h_mean |
|:--------------------------|--------:|------:|--------------------------:|-------------------:|-------------------:|
| garden                    |   0.188 |   4.7 |                     0.067 |               13.7 |               11.4 |
| orchard / terrace         |   2.169 |  54.3 |                     1.672 |               13.5 |               11   |
| pasture / meadow          |   0.734 |  18.4 |                     0.734 |               13.3 |               10.9 |
| wet ground                |   0     |   0   |                     0     |              nan   |              nan   |
| woodlot / steep or shaded |   0.847 |  21.2 |                     0.847 |               12.8 |               10.7 |
| existing buildings        |   0.057 |   1.4 |                     0.026 |               13.7 |               11.2 |

### By parcel

|   PARCELID | address            |   garden |   orchard / terrace |   pasture / meadow |   wet ground |   woodlot / steep or shaded |   existing buildings |
|-----------:|:-------------------|---------:|--------------------:|-------------------:|-------------:|----------------------------:|---------------------:|
|     505727 | 225 PORT ROYAL AVE |    0.188 |               2.169 |              0.734 |            0 |                       0.847 |                0.057 |

## 5. Zoning, services, access

### Zoning

| long_code   |   acres |
|:------------|--------:|
| RSD-1       |   3.995 |


### Road frontage (boundary within 40 ft of a centerline)

| road           |   frontage_ft |
|:---------------|--------------:|
| PORT ROYAL AVE |           362 |

### Existing structures

|   PARCELID | address            | building_name   |   approx_hgt |   square_ft |
|-----------:|:-------------------|:----------------|-------------:|------------:|
|     505727 | 225 PORT ROYAL AVE |                 |           28 |        1704 |
|     505727 | 225 PORT ROYAL AVE |                 |           11 |         719 |

## 6. Restrictions and context

- National Register historic district or property: Upper Roxborough Historic District / district / 2001 (2.478 ac, 62.0%)
- Local historic district: none on the property
- Conservation easement: 2010-PH-PA-CE-NL-17 / Natural Lands / Conservation (0.041 ac, 1.0%)
- Preserved farmland: layer not configured for this listing
- School district: layer not configured for this listing
- Traffic: no state route within 100 ft of the boundary (local roads are not counted)
- Soil suitability for a septic absorption field: Very limited 3.995 ac
- Soil suitability for a dwelling with basement: Very limited 2.963 ac, Somewhat limited 0.843 ac, Not limited 0.188 ac
- Frost-free growing season (soil survey): 162 to 185 days
