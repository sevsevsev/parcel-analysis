# Site evaluation: sample

Property: 15.087 acres (all parcels merged), 4 parcels. Thresholds: slope <= 15%, setback 50 ft, stream buffer 100 ft, wetland buffer 50 ft.

## 1. Buildable area

- **Buildable: 2.475 acres (16.4% of property)**
- If slopes up to 25% were accepted: 2.475 acres
- Area removed by each constraint (overlapping): steep 0.68 ac, setback 3.85 ac, flood 11.99 ac, stream_buffer 2.89 ac, wetland_buffer 3.86 ac, drainage_way_buffer 1.97 ac

### Largest contiguous building pads

|   pad |   acres | approx_dims_ft   |   mean_slope_pct | parcel   |
|------:|--------:|:-----------------|-----------------:|:---------|
|     1 |   2.475 | 596 x 254        |              1.8 | 101-B    |

### By parcel

| PARCEL_ID   |   parcel_acres |   buildable_acres |   buildable_pct |   steep_acres |
|:------------|---------------:|------------------:|----------------:|--------------:|
| 101-A       |          5.051 |             2.098 |            41.5 |         0.147 |
| 101-B       |          3.03  |             0.376 |            12.4 |         0.005 |
| 102         |          4.05  |             0     |             0   |         0.519 |
| 103         |          2.957 |             0     |             0   |         0.005 |

## 2. Sun exposure

- Latitude 40.1711. A flat, unshaded site here gets 8.8 h of sun on Dec 21.
- Mean direct sun on Dec 21: 8.6 h over the property, 8.7 h over the buildable area
- Mean direct sun Mar 21: 11.6 h; Jun 21: 14.2 h
- Winter solar index (direct-beam energy relative to flat unshaded ground, Dec 21): 0.98 over the property, 1.0 over the buildable area. South slopes score above 1, north slopes below.
- South-facing or flat ground: 70.9% of property
- Buildable ground with at least 4 h of winter sun: 2.475 acres
- Shading is from terrain only (bare-earth DEM). Tree canopy and neighbouring houses are not modelled.

### Aspect

| aspect     |   acres |   buildable_acres |   pct |
|:-----------|--------:|------------------:|------:|
| flat (<3%) |   9.183 |             2.261 |  60.9 |
| N          |   0.95  |             0.053 |   6.3 |
| NE         |   1.127 |             0.016 |   7.5 |
| E          |   0.925 |             0.005 |   6.1 |
| SE         |   0.629 |             0.028 |   4.2 |
| S          |   0.347 |             0.002 |   2.3 |
| SW         |   0.544 |             0.002 |   3.6 |
| W          |   0.528 |             0.057 |   3.5 |
| NW         |   0.854 |             0.051 |   5.7 |

### By parcel

| PARCEL_ID   |   dec21_sun_hours_mean |   dec21_solar_index |   jun21_sun_hours_mean |   south_or_flat_pct |
|:------------|-----------------------:|--------------------:|-----------------------:|--------------------:|
| 101-A       |                    8.6 |                0.97 |                   14.2 |                74   |
| 101-B       |                    8.7 |                1    |                   14.2 |                83   |
| 102         |                    8.4 |                0.98 |                   14   |                55.6 |
| 103         |                    8.7 |                0.99 |                   14.2 |                74.3 |

## 3. Stormwater

- Run-on: 23.56 acres of off-site land drain onto the property
- Concentrated flow paths (>= 1.0 ac contributing) inside property: about 1870 ft
- Depressions that would pond (> 0.5 ft deep): 0.253 acres

### Where runoff leaves the property

|   contributing_acres | parcel   |
|---------------------:|:---------|
|                19.57 | 102      |
|                 3.8  | 101-B    |
|                 3.38 | 101-B    |
|                 2.28 | 101-B    |
|                 2.15 | 101-A    |

## 4. Growing ground

- Garden-grade ground (slope <= 8%, >= 8 h June sun, soil not wet): **11.065 acres**
- Orchard / terrace ground (slope <= 20%): 1.460 acres; pasture / meadow (slope <= 25%): 0.147 acres; wet ground: 2.342 acres; woodlot: 0.073 acres
- Cultivable ground (garden + orchard) that is NOT in the buildable area: 10.051 acres
- Usable for building, growing or grazing combined: 12.672 acres (84.0%)
- USDA prime farmland soils: 0.000 acres; farmland of statewide importance: 0.000 acres
- Mean June 21 sun over the property: 14.2 h (terrain shading only)

### By class

| class                     |   acres |   pct |   outside_buildable_acres |   jun21_sun_h_mean |   mar21_sun_h_mean |
|:--------------------------|--------:|------:|--------------------------:|-------------------:|-------------------:|
| garden                    |  11.065 |  73.3 |                     8.597 |               14.2 |               11.7 |
| orchard / terrace         |   1.46  |   9.7 |                     1.453 |               13.9 |               11.3 |
| pasture / meadow          |   0.147 |   1   |                     0.147 |               13.5 |               10.9 |
| wet ground                |   2.342 |  15.5 |                     2.342 |               14.2 |               11.6 |
| woodlot / steep or shaded |   0.073 |   0.5 |                     0.073 |               13.2 |               10.7 |
| existing buildings        |   0     |   0   |                     0     |              nan   |              nan   |

### By parcel

| PARCEL_ID   |   garden |   orchard / terrace |   pasture / meadow |   wet ground |   woodlot / steep or shaded |   existing buildings |
|:------------|---------:|--------------------:|-------------------:|-------------:|----------------------------:|---------------------:|
| 101-A       |    3.71  |               0.36  |              0.016 |        0.964 |                       0     |                    0 |
| 101-B       |    2.911 |               0.119 |              0     |        0     |                       0     |                    0 |
| 102         |    2.404 |               0.891 |              0.131 |        0.551 |                       0.073 |                    0 |
| 103         |    2.041 |               0.09  |              0     |        0.826 |                       0     |                    0 |

## 5. Zoning, services, access

### Zoning

| ZONE   |   acres |
|:-------|--------:|
| AG     |   6.267 |
| R-1    |   8.82  |


### Road frontage (boundary within 40 ft of a centerline)

| road             |   frontage_ft |
|:-----------------|--------------:|
| Coventryville Rd |           404 |

## 6. Restrictions and context

- National Register historic district or property: layer not configured for this listing
- Local historic district: layer not configured for this listing
- Conservation easement: layer not configured for this listing
- Preserved farmland: layer not configured for this listing
- School district: layer not configured for this listing
