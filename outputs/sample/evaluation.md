# Site evaluation: sample

Property: 15.087 acres, 4 parcels. Thresholds: slope <= 15%, setback 50 ft, stream buffer 100 ft, wetland buffer 50 ft.

## 1. Buildable area

- **Buildable: 2.475 acres (16.4% of property)**
- If slopes up to 25% were accepted: 3.056 acres
- Area removed by each constraint (overlapping): steep 0.68 ac, setback 3.85 ac, flood 11.99 ac, stream_buffer 2.89 ac, wetland_buffer 3.86 ac

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

- Latitude 40.1711. A flat, unshaded site here gets 8.5 h of sun on Dec 21.
- Mean direct sun on Dec 21: 8.4 h over the property, 8.5 h over the buildable area
- Mean direct sun Mar 21: 11.4 h; Jun 21: 14.4 h
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
| 101-A       |                    8.4 |                0.97 |                   14.4 |                74   |
| 101-B       |                    8.5 |                1    |                   14.5 |                83   |
| 102         |                    8.2 |                0.98 |                   14.2 |                55.6 |
| 103         |                    8.5 |                0.99 |                   14.5 |                74.3 |

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

## 4. Zoning, services, access

### Zoning

| ZONE   |   acres |
|:-------|--------:|
| AG     |   6.267 |
| R-1    |   8.82  |

- Public sewer service area coverage: None
- Public water service area coverage: None

### Road frontage (boundary within 40 ft of a centerline)

| road             |   frontage_ft |
|:-----------------|--------------:|
| Coventryville Rd |           404 |

## Maps

map_buildable.png, map_slope.png, map_sun_dec21.png, map_stormwater.png
