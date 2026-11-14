# Site evaluation: port_royal

Property: 3.995 acres (all parcels merged), 1 parcels. Thresholds: slope <= 15%, setback 25 ft, stream buffer 100 ft, wetland buffer 50 ft.

## 1. Buildable area

- **Buildable: 0.644 acres (16.1% of property)**
- If slopes up to 25% were accepted: 1.886 acres
- Area removed by each constraint (overlapping): steep 2.90 ac, setback 1.06 ac, flood 0.00 ac, stream_buffer 0.00 ac, wetland_buffer 0.00 ac, drainage_way_buffer 0.67 ac

_No contiguous buildable patch of at least 0.25 acres._

### By parcel

|   PARCELID | address            |   parcel_acres |   buildable_acres |   buildable_pct |   steep_acres |
|-----------:|:-------------------|---------------:|------------------:|----------------:|--------------:|
|     505727 | 225 PORT ROYAL AVE |          3.992 |             0.644 |            16.1 |         2.897 |

## 2. Sun exposure

- Latitude 40.0489. A flat, unshaded site here gets 8.8 h of sun on Dec 21.
- Mean direct sun on Dec 21: 8.0 h over the property, 8.2 h over the buildable area
- Mean direct sun Mar 21: 10.9 h; Jun 21: 13.3 h
- Winter solar index (direct-beam energy relative to flat unshaded ground, Dec 21): 1.17 over the property, 1.05 over the buildable area. South slopes score above 1, north slopes below.
- South-facing or flat ground: 48.9% of property
- Buildable ground with at least 4 h of winter sun: 0.644 acres
- Shading is from terrain only (bare-earth DEM). Tree canopy and neighbouring houses are not modelled.

### Aspect

| aspect     |   acres |   buildable_acres |   pct |
|:-----------|--------:|------------------:|------:|
| flat (<3%) |   0.041 |             0.035 |   1   |
| N          |   0.003 |             0.002 |   0.1 |
| NE         |   0.003 |             0.003 |   0.1 |
| E          |   0.003 |             0.002 |   0.1 |
| SE         |   0.122 |             0.011 |   3.1 |
| S          |   1.152 |             0.079 |  28.9 |
| SW         |   0.636 |             0.167 |  15.9 |
| W          |   1.674 |             0.306 |  41.9 |
| NW         |   0.357 |             0.039 |   8.9 |

### By parcel

|   PARCELID | address            |   dec21_sun_hours_mean |   dec21_solar_index |   jun21_sun_hours_mean |   south_or_flat_pct |
|-----------:|:-------------------|-----------------------:|--------------------:|-----------------------:|--------------------:|
|     505727 | 225 PORT ROYAL AVE |                      8 |                1.17 |                   13.3 |                48.9 |

## 3. Stormwater

- Run-on: 14.80 acres of off-site land drain onto the property
- Concentrated flow paths (>= 1.0 ac contributing) inside property: about 240 ft
- Depressions that would pond (> 0.5 ft deep): 0.000 acres

### Where runoff leaves the property

|   contributing_acres | parcel             |
|---------------------:|:-------------------|
|                15.99 | 225 PORT ROYAL AVE |
|                 0.44 | 225 PORT ROYAL AVE |
|                 0.28 | 225 PORT ROYAL AVE |
|                 0.25 | 225 PORT ROYAL AVE |

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

- Garden-grade ground (slope <= 8%, >= 8 h June sun, soil not wet): **0.183 acres**
- Orchard / terrace ground (slope <= 20%): 2.190 acres; pasture / meadow (slope <= 25%): 0.717 acres; wet ground: 0.000 acres; woodlot: 0.846 acres
- Cultivable ground (garden + orchard) that is NOT in the buildable area: 1.758 acres
- Usable for building, growing or grazing combined: 3.119 acres (78.1%)
- USDA prime farmland soils: 0.184 acres; farmland of statewide importance: 0.844 acres
- Mean June 21 sun over the property: 13.3 h (terrain shading only)

- A steep slope regulation covers 95.4% of the property, including 2.209 acres of the garden/orchard ground and 0.706 acres of the pasture ground; clearing or terracing there needs review

- Tree canopy (mapped): covers 56.0% of the property; 0.340 acres of buildable and 1.435 acres of garden/orchard ground are under canopy today

### By class

| class                     |   acres |   pct |   outside_buildable_acres |   jun21_sun_h_mean |   mar21_sun_h_mean |
|:--------------------------|--------:|------:|--------------------------:|-------------------:|-------------------:|
| garden                    |   0.183 |   4.6 |                     0.063 |               13.7 |               11.4 |
| orchard / terrace         |   2.19  |  54.8 |                     1.695 |               13.5 |               11   |
| pasture / meadow          |   0.717 |  18   |                     0.717 |               13.3 |               10.8 |
| wet ground                |   0     |   0   |                     0     |              nan   |              nan   |
| woodlot / steep or shaded |   0.846 |  21.2 |                     0.846 |               12.8 |               10.7 |
| existing buildings        |   0.057 |   1.4 |                     0.027 |               13.6 |               11.2 |

### By parcel

|   PARCELID | address            |   garden |   orchard / terrace |   pasture / meadow |   wet ground |   woodlot / steep or shaded |   existing buildings |
|-----------:|:-------------------|---------:|--------------------:|-------------------:|-------------:|----------------------------:|---------------------:|
|     505727 | 225 PORT ROYAL AVE |    0.183 |                2.19 |              0.717 |            0 |                       0.846 |                0.057 |

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
- Nearest DEP-classified stream: Part of a bulk upload of corrections (102299, WWF(WARM WATER FISHES)) at 848 ft
- Soil suitability for a septic absorption field: Very limited 3.995 ac
- Soil suitability for a dwelling with basement: Very limited 2.963 ac, Somewhat limited 0.843 ac, Not limited 0.188 ac
- Frost-free growing season (soil survey): 162 to 185 days
