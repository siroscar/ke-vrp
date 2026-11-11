"""Interactive Leaflet map (folium) of a solved instance.

Toggle HGS vs greedy route layers, click stations for assigned vehicle + ETA, hover routes
for load / km / cost. Opens in any browser; tiles need an internet connection.
NB: route lines are straight segments between stops, not actual road geometry.
"""
from __future__ import annotations

import pathlib

import folium
from folium.plugins import Fullscreen, MiniMap

from .evaluate import Metrics, Route
from .fleet import VehicleSpec
from .instance import Instance

AREA_COLOR = {"urban": "#1f77b4", "peri": "#2ca02c", "remote": "#d62728"}
ROUTE_PALETTE = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#008080",
                 "#9a6324", "#800000", "#808000", "#000075", "#f032e6", "#469990"]
LABELS = {"hgs": "HGS (optimised)", "greedy_nn": "Greedy nearest-neighbour"}


def _clock(t_s: int, start_hour: int) -> str:
    m = start_hour * 60 + t_s // 60
    return f"{(m // 60) % 24:02d}:{m % 60:02d}"


def _route_stats(inst, fleet, mats, r: Route):
    dist, dur = mats[r.spec]
    v = fleet[r.spec]
    t = prev = load = d = 0
    stops = []
    for s in r.stops:
        st = inst.stations[s]
        node = s + 1
        t += int(dur[prev, node])
        d += int(dist[prev, node])
        t = max(t, st.tw_early_s)
        stops.append((s, t))
        t += st.service_s
        load += st.demand
        prev = node
    t += int(dur[prev, 0])
    d += int(dist[prev, 0])
    return dict(stops=stops, load=load, km=d / 10, back_s=t,
                cost=v.fixed_cost + d * v.cost_per_hm)


def build_map(inst: Instance, fleet: list[VehicleSpec], mats,
              solutions: dict[str, list[Route]], path,
              metrics: dict[str, Metrics] | None = None,
              n_unservable: int = 0, dispatch_hour: int = 6) -> pathlib.Path:
    m = folium.Map(location=[inst.depot_lat, inst.depot_lon], zoom_start=8,
                   tiles="OpenStreetMap", control_scale=True)
    folium.TileLayer("CartoDB positron", name="Light basemap").add_to(m)
    folium.TileLayer("Esri.WorldImagery", name="Satellite", attr="Esri").add_to(m)
    Fullscreen().add_to(m)
    MiniMap(toggle_display=True, position="bottomleft").add_to(m)

    # per-method assignment lookup + route stats
    assign: dict[str, dict[int, str]] = {}
    stats: dict[str, list[tuple[Route, dict, str]]] = {}
    for meth, routes in solutions.items():
        assign[meth], stats[meth] = {}, []
        counters: dict[int, int] = {}
        for r in routes:
            if not r.stops:
                continue
            counters[r.spec] = counters.get(r.spec, 0) + 1
            label = f"{fleet[r.spec].name} #{counters[r.spec]}"
            st = _route_stats(inst, fleet, mats, r)
            stats[meth].append((r, st, label))
            for k, (s, t) in enumerate(st["stops"], 1):
                assign[meth][s] = f"{label}: stop {k}, ETA {_clock(t, dispatch_hour)}"

    # stations
    sg = folium.FeatureGroup(name="Polling stations", show=True)
    for i, s in enumerate(inst.stations):
        rows = "".join(f"<br><b>{LABELS.get(meth, meth)}:</b> {assign[meth].get(i, 'unserved')}"
                       for meth in solutions)
        html = (f"<b>{s.id}</b> ({s.area})<br>demand {s.demand} boxes<br>"
                f"window {_clock(s.tw_early_s, dispatch_hour)}-{_clock(s.tw_late_s, dispatch_hour)}"
                f"<br>service {s.service_s // 60} min"
                f"{'' if s.road_ok else '<br><b>No road access: air only</b>'}{rows}")
        folium.CircleMarker(
            [s.lat, s.lon], radius=4 + s.demand ** 0.5,
            color="black" if not s.road_ok else AREA_COLOR[s.area],
            weight=3 if not s.road_ok else 1, fill=True, fill_color=AREA_COLOR[s.area],
            fill_opacity=0.85, popup=folium.Popup(html, max_width=320),
            tooltip=f"{s.id} ({s.area})").add_to(sg)
    sg.add_to(m)

    # route layers
    for n, (meth, items) in enumerate(stats.items()):
        g = folium.FeatureGroup(name=f"Routes: {LABELS.get(meth, meth)}", show=(n == 0))
        for k, (r, st, label) in enumerate(items):
            v = fleet[r.spec]
            pts = [[inst.depot_lat, inst.depot_lon]] + \
                  [[inst.stations[s].lat, inst.stations[s].lon] for s, _ in st["stops"]] + \
                  [[inst.depot_lat, inst.depot_lon]]
            tip = (f"<b>{label}</b> ({v.mode})<br>{len(r.stops)} stops, load {st['load']}/{v.capacity}"
                   f"<br>{st['km']:.0f} km, back {_clock(st['back_s'], dispatch_hour)}"
                   f"<br>cost KES {st['cost']:,}")
            folium.PolyLine(pts, color=ROUTE_PALETTE[k % len(ROUTE_PALETTE)],
                            weight=4 if v.mode == "air" else 2.5, opacity=0.85,
                            dash_array="10 8" if v.mode == "air" else None,
                            tooltip=folium.Tooltip(tip, sticky=True)).add_to(g)
        g.add_to(m)

    folium.Marker([inst.depot_lat, inst.depot_lon], tooltip="Depot (county hub)",
                  icon=folium.Icon(color="black", icon="star")).add_to(m)

    # legend + KPI table
    kpi = ""
    if metrics:
        kpi = "<table style='border-collapse:collapse;margin-top:6px'><tr><th align=left>Method</th>" \
              "<th>Cost (KES)</th><th>Veh.</th><th>Km</th><th>Last drop</th></tr>"
        for meth, mt in metrics.items():
            kpi += (f"<tr><td>{LABELS.get(meth, meth)}</td><td align=right>{mt.cost:,}</td>"
                    f"<td align=right>{sum(mt.vehicles_used.values())}</td>"
                    f"<td align=right>{mt.total_km:,.0f}</td>"
                    f"<td align=right>{_clock(int(mt.makespan_h * 3600), dispatch_hour)}</td></tr>")
        kpi += "</table>"
    legend = f"""
    <div style="position:fixed;bottom:24px;right:12px;z-index:9999;background:white;padding:10px 12px;
                border:1px solid #888;border-radius:6px;font:12px sans-serif;max-width:340px">
      <b>{inst.name}</b> ({len(inst.stations)} stations{f', {n_unservable} unservable' if n_unservable else ''})<br>
      <span style="color:{AREA_COLOR['urban']}">&#9679;</span> urban
      <span style="color:{AREA_COLOR['peri']}">&#9679;</span> peri-urban
      <span style="color:{AREA_COLOR['remote']}">&#9679;</span> remote
      &nbsp;|&nbsp; black ring = air only<br>
      solid line = road vehicle, dashed = helicopter<br>
      circle size ~ demand. Click a station for assignment + ETA.
      {kpi}
    </div>"""
    m.get_root().html.add_child(folium.Element(legend))
    folium.LayerControl(collapsed=False).add_to(m)

    lats = [s.lat for s in inst.stations] + [inst.depot_lat]
    lons = [s.lon for s in inst.stations] + [inst.depot_lon]
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(path))
    return path
