# -*- coding: utf-8 -*-
"""
일기예보 방송 대시보드 (HTML) 생성기
=========================================

목적: 플레이어에게 공지하는 '지방 기상청 방송' 스타일의 단일 HTML 파일을
매일 자동 생성. 픽셀 아트(pixel_weather_map.py)와 달리 실제 기온/습도
수치와 예보 방송문을 한 화면에서 모두 보여주는 정보 위주 대시보드.

climate_v2(=pokemon_climate_model_v2.py)의 시뮬레이터를 그대로 불러와
지역별 결과 + generate_forecast() 문구를 HTML 템플릿에 꽂아 넣는다.
"""

import os
from pokemon_climate_model_v2 import (
    build_example_map,
    RegionClimateSimulator,
    season_of_day,
)

# 사용자가 구술한 도로망을 반영한 전체 지도 배치 (viewBox 0 0 460 320 기준)
# 물리 좌표(x,y)를 그대로 스케일링해서 화면에 반영 (scale=45, margin=40)
NODE_LAYOUT = {
    "토리노":     {"abbr": "토리노",  "pos": (40, 40)},
    "1번도로":    {"abbr": "Rt.01",     "pos": (85, 40)},
    "밀라노":     {"abbr": "밀라노",  "pos": (130, 40)},
    "2번도로":    {"abbr": "Rt.02",     "pos": (175, 40)},
    "베로나":     {"abbr": "베로나",  "pos": (220, 40)},
    "3번도로":    {"abbr": "Rt.03",     "pos": (265, 40)},
    "베네치아":   {"abbr": "베네치아",  "pos": (310, 40)},
    "4번도로":    {"abbr": "Rt.04",     "pos": (355, 40)},
    "트리에스테": {"abbr": "트리에스테", "pos": (400, 40)},
    "5번도로":    {"abbr": "Rt.05",     "pos": (153, 85)},
    "파르마":     {"abbr": "파르마",   "pos": (198, 85)},
    "6번도로":    {"abbr": "Rt.06",     "pos": (243, 130)},
    "볼로냐":     {"abbr": "볼로냐", "pos": (288, 175)},
    "7번도로":    {"abbr": "Rt.07",     "pos": (310, 220)},
    "피렌체":     {"abbr": "피렌체", "pos": (288, 265)},
    "8번도로":    {"abbr": "Rt.08",     "pos": (243, 265)},
    "피사":       {"abbr": "피사",    "pos": (198, 265)},
    "9번도로":    {"abbr": "Rt.09",     "pos": (153, 220)},
    "제노바":     {"abbr": "제노바",   "pos": (108, 175)},
    "10번도로":   {"abbr": "Rt.10",    "pos": (40, 175)},
    "라벤나":     {"abbr": "라벤나", "pos": (333, 175)},
}

TERRAIN_COLOR = {"coastal": "#378ADD", "mountain": "#888780", "plain": "#639922"}
TERRAIN_LABEL = {"coastal": "해안", "mountain": "산악", "plain": "평지"}

# 도시/도로별 설명 + 출현 포켓몬 (예시 형식 - 실제 내용은 이후 채워 넣을 것)
REGION_INFO = {
    "토리노": {
        "description": "겨울과 오컽트의 도시. 알프스 자락에서 여름에도 눈이 내려온다. 도심에서도 마터호른과 몽블랑이 보인다.",
    },
    "1번도로": {
        "description": "토리노 고원을 등지고 내려오는 도로. 여름에는 시원한 트래킹 코스, 겨울에는 험난한 강설 코스.",
        "pokemon": ["구구", "이올브"],
    },
    "밀라노": {
        "description": "산업과 패션의 도시. 이탈리아 북부의 경제 중심지. 세계의 패셔니스타들이 모이는 곳. 콘테스트도 자주 열린다.",
        "pokemon": ["구구", "이올브"],
    },
    "2번도로": {
        "description": "밀라노와 베로나를 잇는 도로. 포 강을 옆에 낀 평탄한 길. 여름에는 자전거 여행객이 많다.",
        "pokemon": ["구구", "이올브"],
    },
    "베로나": {
        "description": "로미오와 줄리엣의 도시. 아레나 디 베로나가 유명하며, 여름에는 오페라 공연이 열린다.",
        "pokemon": ["구구", "이올브"],
    },  
    "3번도로": {
        "description": "베로나와 베네치아를 잇는 도로. 여름에는 강한 햇빛과 습기로 인해 주의가 필요하다.",
        "pokemon": ["구구", "이올브"],  
    },
    "베네치아": {
        "description": "물과 황금의 도시. 곤돌라와 운하, 상업으로 유명하며, 여름에는 관광객이 많다.",
        "pokemon": ["구구", "이올브"],
    },
    "4번도로": {
        "description": "베네치아와 트리에스테를 잇는 도로. 해안선을 따라 이어지는 곡선 도로. 여름에는 해양 스포츠가 활발하다.",
        "pokemon": ["구구", "이올브"], 
    },
    "트리에스테": {
        "description": "카페와 느와르의 도시. 외국과 국경을 접한 유명한 국제 항구. 커피, 카페와 호텔이 유명하며, 물안개 낀 아침은 수많은 느와르 영화의 배경이 되었다.",
        "pokemon": ["구구", "이올브"], 
    },    

    "5번도로": {
        "description": "밀라노와 파르마를 잇는 도로. 쌀과 농작물이 풍성히 자라는 황금 들판.",
        "pokemon": ["구구", "이올브"], 
    },
    "파르마": {
        "description": "목축업과 수도원의 도시. 파르마지아노 레지아노 치즈와 햄으로 유명하며, 도시의 수도사들이 전통 방식대로 빚은 식자재를 최고로 친다.",
        "pokemon": ["구구", "이올브"],
    },
    "6번도로": {
        "description": "파르마와 볼로냐를 잇는 도로. 고고트와 밀탱크의 산지 목장을 옆으로 하고, 식량 운송 트럭과 푸드 트럭이 많이 다닌다.",
        "pokemon": ["구구", "이올브"], 
    },
    "볼로냐": {
        "description": "대학과 미식의 도시. 세계에서 가장 오래된 포켓몬 아카데미가 유명하다. 남부에서 중부로 넘어가는 관문도시로, 북부의 식자재와 중부의 문화가 섞여 수많은 미식을 만들어냈다.",
        "pokemon": ["구구", "이올브"], 
    },
    "7번도로": {
        "description": "볼로냐와 피렌체를 잇는 도로. 산맥을 통과하는 험난한 길. 겨울에는 눈이 많이 쌓인다.",
        "pokemon": ["구구", "이올브"],
    },
    "피렌체": {
        "description": "예술과 르네상스의 도시. 미켈란젤로, 다빈치 등 예술가들의 작품이 많으며, 여름에는 관광객이 몰린다. 로마로 향하는 카시아 가도의 시작점.",
        "pokemon": ["구구", "이올브"], 
    },
    "8번도로": {
        "description": "피렌체와 피사를 잇는 도로.",
        "pokemon": ["구구", "이올브"],
    },
    "피사": {
        "description": "사탑과 연구의 도시. 피사의 사탑으로 유명하며, 바다를 낀 호텔과 대학에선 학회가 열린다.",
        "pokemon": ["구구", "이올브"],
    },
    "9번도로": {
        "description": "피사와 제노바를 잇는 도로. 해안선을 따라 이어지며, 산맥과 바다를 함께 볼 수 있는 경치 좋은 길.",
        "pokemon": ["구구", "이올브"],
    },
    "제노바": {
        "description": "항구와 무역의 도시. 제노바 항구와 구시가지가 유명하며, 해양 무역과 관련된 문화가 발달했다.",
        "pokemon": ["구구", "이올브"],
    },
    "10번도로": {
        "description": "제노바와 토리노를 잇는 도로. 겨울에는 눈이 많이 쌓여 도보는 차단된다.",
        "pokemon": ["구구", "이올브"],
    }
}

WEATHER_GLYPH = {
    "쾌청": ("\u2600", "#F2B84B"),
    "맑음": ("\u2600", "#E8C87A"),
    "흐림": ("\u2601", "#9AA3AF"),
    "비": ("\u2614", "#4FD69C"),
    "뇌우": ("\u26A1", "#E4572E"),
    "눈": ("\u2744", "#CFE8FF"),
    "폭설": ("\u2744", "#FFFFFF"),
    "안개": ("\u2592", "#8A93A3"),
}

# =================================================================
# 도트(픽셀) 아이콘 정의: 8x8 그리드, 셀 하나 = CELL px 정사각형
# =================================================================

CELL = 3
GRID = 8


def _rects(cells, color, ox, oy):
    out = []
    for c, r in cells:
        x, y = ox + c * CELL, oy + r * CELL
        out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                    f'fill="{color}" shape-rendering="crispEdges"/>')
    return "".join(out)


TERRAIN_PIXELS = {
    "coastal": {
        "base": ([(c, r) for r in range(1, 6) for c in range(1, 7)], "#2C6FB0"),
        "accent": ([(1, 2), (3, 2), (5, 2), (2, 4), (4, 4), (6, 4)], "#7FC4F0"),
    },
    "mountain": {
        "base": ([(c, r) for r in range(2, 6) for c in range(1, 7)], "#726B62"),
        "accent": ([(3, 1), (4, 1), (2, 2), (3, 2), (4, 2), (5, 2)], "#EDEBE4"),
    },
    "plain": {
        "base": ([(c, r) for r in range(2, 6) for c in range(1, 7)], "#4C7A1F"),
        "accent": ([(2, 3), (5, 3), (3, 4), (6, 4)], "#7FB33E"),
    },
}

WEATHER_PIXELS = {
    "쾌청": {"base": ([(3, 3), (4, 3), (3, 4), (4, 4), (3, 0), (4, 0), (3, 7), (4, 7),
                      (0, 3), (0, 4), (7, 3), (7, 4), (1, 1), (6, 1), (1, 6), (6, 6)],
                     "#F2B84B")},
    "맑음": {"base": ([(3, 3), (4, 3), (3, 4), (4, 4), (3, 0), (4, 0), (3, 7), (4, 7),
                      (0, 3), (0, 4), (7, 3), (7, 4)], "#E8C87A")},
    "흐림": {"base": ([(2, 3), (3, 3), (4, 3), (5, 3), (1, 4), (2, 4), (3, 4), (4, 4),
                      (5, 4), (6, 4), (2, 5), (3, 5), (4, 5), (5, 5)], "#9AA3AF")},
    "비": {
        "base": ([(2, 1), (3, 1), (4, 1), (5, 1), (1, 2), (2, 2), (3, 2), (4, 2),
                  (5, 2), (6, 2), (2, 3), (3, 3), (4, 3), (5, 3)], "#7A8492"),
        "accent": ([(1, 5), (1, 6), (3, 5), (3, 6), (5, 5), (5, 6)], "#4FD69C"),
    },
    "뇌우": {
        "base": ([(2, 1), (3, 1), (4, 1), (5, 1), (1, 2), (2, 2), (3, 2), (4, 2),
                  (5, 2), (6, 2), (2, 3), (3, 3), (4, 3), (5, 3)], "#5B6472"),
        "accent": ([(4, 4), (3, 5), (4, 5), (3, 6), (3, 7)], "#E4572E"),
    },
    "눈": {
        "base": ([(2, 1), (3, 1), (4, 1), (5, 1), (1, 2), (2, 2), (3, 2), (4, 2),
                  (5, 2), (6, 2), (2, 3), (3, 3), (4, 3), (5, 3)], "#C7CDD6"),
        "accent": ([(1, 5), (3, 5), (5, 5), (1, 7), (3, 7), (5, 7)], "#FFFFFF"),
    },
    "폭설": {
        "base": ([(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (1, 1), (2, 1),
                  (3, 1), (4, 1), (5, 1), (6, 1), (2, 2), (3, 2), (4, 2), (5, 2)],
                 "#B9C0CB"),
        "accent": ([(0, 4), (2, 4), (4, 4), (6, 4), (1, 6), (3, 6), (5, 6), (7, 6)]
                   + [(c, 7) for c in range(8)], "#FFFFFF"),
    },
    "안개": {"base": ([(0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2),
                      (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4),
                      (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6)],
                     "#8A93A3")},
}


CITY_MARKER = ([(6, 6), (7, 6), (6, 7), (7, 7)], "#EDE9DD")


def draw_terrain_icon(terrain, cx, cy, is_city=False):
    ox, oy = cx - (GRID * CELL) / 2, cy - (GRID * CELL) / 2
    layers = TERRAIN_PIXELS[terrain]
    svg = _rects(*layers["base"], ox, oy)
    if "accent" in layers:
        svg += _rects(*layers["accent"], ox, oy)
    if is_city:
        svg += _rects(*CITY_MARKER, ox, oy)
    return svg


def draw_weather_icon(weather, cx, cy):
    ox, oy = cx - (GRID * CELL) / 2, cy - (GRID * CELL) / 2
    layers = WEATHER_PIXELS.get(weather)
    if not layers:
        return ""
    svg = _rects(*layers["base"], ox, oy)
    if "accent" in layers:
        svg += _rects(*layers["accent"], ox, oy)
    return svg


def classify_terrain(loc) -> str:
    if loc.coastal:
        return "coastal"
    if loc.altitude >= 300:
        return "mountain"
    return "plain"


def build_map_background() -> str:
    """레트로 2D 픽셀 타일(잔디) 배경으로 지도 전체를 채운다."""
    parts = [
        '<defs><pattern id="grassTile" width="8" height="8" '
        'patternUnits="userSpaceOnUse">'
        '<rect width="8" height="8" fill="#3E6B1F"/>'
        '<rect x="0" y="0" width="4" height="4" fill="#4C8226"/>'
        '<rect x="4" y="4" width="4" height="4" fill="#4C8226"/>'
        '</pattern></defs>',
        '<rect x="0" y="0" width="460" height="320" fill="url(#grassTile)" '
        'shape-rendering="crispEdges"/>',
    ]
    return "".join(parts)


def build_map_svg(cmap, results) -> str:
    parts = ['<svg viewBox="0 0 460 320" width="100%" role="img" '
             'aria-label="지방 지도와 지역별 날씨. 지역을 클릭하면 상세 정보를 볼 수 있습니다.">']
    parts.append(build_map_background())

    # 도로(연결선)는 실제 cmap 연결관계 기준으로 그림 - 아직 연결이 없으면 선도 없음
    drawn = set()
    for name in NODE_LAYOUT:
        loc = cmap.locations.get(name)
        if not loc:
            continue
        for nb in loc.neighbors:
            if nb not in NODE_LAYOUT:
                continue
            edge = tuple(sorted((name, nb)))
            if edge in drawn:
                continue
            drawn.add(edge)
            x1, y1 = NODE_LAYOUT[edge[0]]["pos"]
            x2, y2 = NODE_LAYOUT[edge[1]]["pos"]
            parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                          f'stroke="#4A5568" stroke-width="2" shape-rendering="crispEdges"/>')

    for name, layout in NODE_LAYOUT.items():
        x, y = layout["pos"]
        abbr = layout["abbr"]
        loc = cmap.locations[name]
        terrain = classify_terrain(loc)
        is_city = (loc.kind == "도시")
        weather = results[name].weather

        parts.append(
            f'<g class="node" id="node-{abbr}" tabindex="0" role="button" '
            f'aria-label="{name} 상세 정보 보기" '
            f'onclick="selectRegion(\'{abbr}\')" '
            f'onkeypress="if(event.key===\'Enter\')selectRegion(\'{abbr}\')">'
        )
        parts.append(f'<rect class="node-hit" x="{x - 18}" y="{y - 32}" width="36" height="46" fill="transparent"/>')
        parts.append(draw_weather_icon(weather, x, y - 24))
        parts.append(draw_terrain_icon(terrain, x, y, is_city))
        parts.append(f'<text x="{x}" y="{y + 22}" text-anchor="middle" '
                      f'font-size="11" fill="#C9CFDA" '
                      f'font-family="ui-monospace, monospace">{abbr}</text>')
        parts.append('</g>')

    parts.append('</svg>')
    return "".join(parts)


def build_region_data_json(cmap, results) -> str:
    import json
    data = {}
    for name, layout in NODE_LAYOUT.items():
        r = results[name]
        loc = cmap.locations[name]
        terrain = classify_terrain(loc)
        glyph, _ = WEATHER_GLYPH.get(r.weather, ("?", "#9AA3AF"))
        info = REGION_INFO.get(name, {})
        data[layout["abbr"]] = {
            "name": name,
            "weather": r.weather,
            "glyph": glyph,
            "temperature": round(r.temperature, 1),
            "humidity": round(r.humidity),
            "terrain": f'{TERRAIN_LABEL[terrain]} {loc.kind}',
            "description": info.get("description", ""),
            "pokemon": info.get("pokemon", []),
        }
    return json.dumps(data, ensure_ascii=False)


def build_table_rows(results, order) -> str:
    rows = []
    for name in order:
        r = results[name]
        abbr = NODE_LAYOUT[name]["abbr"]
        glyph, glyph_color = WEATHER_GLYPH.get(r.weather, ("?", "#9AA3AF"))
        rows.append(
            f'<tr id="row-{abbr}">'
            f'<td class="cell-name">{abbr}</td>'
            f'<td class="cell-weather" style="color:{glyph_color}">{glyph} {r.weather}</td>'
            f'<td class="cell-num">{r.temperature:.1f}\u2103</td>'
            f'<td class="cell-num">{r.humidity:.0f}%</td>'
            "</tr>"
        )
    return "\n".join(rows)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{region_name} 기상청 - {day_label}</title>
<style>
  :root {{
    --ink: #10192B;
    --panel: #16233A;
    --row-alt: #1C2A44;
    --amber: #F2B84B;
    --mint: #4FD69C;
    --alert: #E4572E;
    --paper: #E9E4D4;
    --muted: #7C8AA0;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--ink);
    color: var(--paper);
    font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', -apple-system, sans-serif;
    padding: 24px 16px 48px;
    position: relative;
  }}
  body::before {{
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
      to bottom, rgba(255,255,255,0.025) 0px, rgba(255,255,255,0.025) 1px,
      transparent 1px, transparent 3px
    );
  }}
  .wrap {{ max-width: 640px; margin: 0 auto; }}
  .headerbar {{
    display: flex; justify-content: space-between; align-items: baseline;
    border-bottom: 2px solid var(--amber); padding-bottom: 10px; margin-bottom: 18px;
  }}
  .headerbar h1 {{
    font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
    font-size: 20px; font-weight: 700; margin: 0; color: var(--amber);
    letter-spacing: 0.5px;
  }}
  .headerbar .meta {{
    font-family: ui-monospace, monospace; font-size: 13px; color: var(--muted);
  }}
  .onair {{
    display: inline-flex; align-items: center; gap: 6px;
    font-family: ui-monospace, monospace; font-size: 12px; color: var(--alert);
  }}
  .onair .dot {{
    width: 8px; height: 8px; border-radius: 50%; background: var(--alert);
    animation: pulse 1.6s ease-in-out infinite;
  }}
  @media (prefers-reduced-motion: reduce) {{ .onair .dot {{ animation: none; }} }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.25; }} }}
  .headline {{
    font-family: ui-monospace, monospace; font-size: 17px; font-weight: 700;
    color: var(--paper); background: var(--panel); border-left: 4px solid var(--amber);
    padding: 12px 14px; margin-bottom: 20px; line-height: 1.5;
  }}
  .panel {{ background: var(--panel); border-radius: 6px; padding: 14px; margin-bottom: 20px; }}
  .panel h2 {{
    font-family: ui-monospace, monospace; font-size: 13px; color: var(--muted);
    text-transform: uppercase; letter-spacing: 1px; margin: 0 0 10px;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{
    text-align: left; font-family: ui-monospace, monospace; font-size: 12px;
    color: var(--muted); font-weight: 400; padding: 6px 8px; border-bottom: 1px solid #2A3A56;
  }}
  td {{ padding: 8px; border-bottom: 1px solid #22304A; }}
  tr:nth-child(even) td {{ background: var(--row-alt); }}
  .cell-name {{ font-family: ui-monospace, monospace; color: var(--paper); font-weight: 700; }}
  .cell-num {{ font-family: ui-monospace, monospace; color: var(--mint); text-align: right; }}
  .cell-weather {{ font-weight: 700; }}
  .forecast p {{
    font-size: 15px; line-height: 1.8; margin: 0 0 10px; padding-left: 14px;
    border-left: 2px solid #2A3A56;
  }}
  .forecast p:last-child {{ margin-bottom: 0; }}
  .footer {{ font-family: ui-monospace, monospace; font-size: 11px; color: var(--muted); text-align: center; margin-top: 24px; }}
  .node {{ cursor: pointer; }}
  .node.selected rect.node-hit {{ fill: rgba(242,184,75,0.08); }}
  .node text {{ pointer-events: none; }}
  #detail-panel {{ font-family: ui-monospace, monospace; font-size: 13px; color: var(--muted); }}
  #detail-panel.filled {{ color: var(--paper); }}
  #detail-panel .d-name {{ font-size: 16px; font-weight: 700; color: var(--amber); }}
  #detail-panel .d-row {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #22304A; }}
  #detail-panel .d-row:last-child {{ border-bottom: none; }}
  #detail-panel .d-desc {{ margin-top: 8px; font-size: 12px; line-height: 1.6; color: var(--paper); }}
  #detail-panel .d-pokemon {{ margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }}
  #detail-panel .d-pokemon-chip {{
    font-size: 11px; padding: 3px 8px; border-radius: 10px;
    background: #24365A; color: var(--mint); border: 1px solid #2A3A56;
  }}
  tr.row-selected td {{ background: #24365A; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="headerbar">
    <h1>{region_name} 기상청</h1>
    <div class="meta">
      <span class="onair"><span class="dot"></span>ON AIR</span>
      &nbsp;DAY {day_of_year:03d} &middot; {season}
    </div>
  </div>

  <div class="headline">{headline}</div>

  <div class="panel">
    <h2>지역 지도 <span style="text-transform:none; letter-spacing:0;">(지역을 클릭해보세요)</span></h2>
    {map_svg}
    <div id="detail-panel">지역을 클릭하면 상세 정보가 여기 표시됩니다.</div>
  </div>

  <div class="panel">
    <h2>지역별 관측치</h2>
    <table>
      <thead><tr><th>지역</th><th>날씨</th><th style="text-align:right">기온</th><th style="text-align:right">습도</th></tr></thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>

  <div class="panel forecast">
    <h2>오늘의 예보 방송</h2>
    {forecast_paragraphs}
  </div>

  <div class="footer">본 예보는 지방 기상청의 관측 모델에 근거하며 실제와 다를 수 있습니다.</div>
</div>
<script>
const REGION_DATA = {region_data_json};
let selectedAbbr = null;

function selectRegion(abbr) {{
  if (selectedAbbr) {{
    const prevNode = document.getElementById('node-' + selectedAbbr);
    const prevRow = document.getElementById('row-' + selectedAbbr);
    if (prevNode) prevNode.classList.remove('selected');
    if (prevRow) prevRow.classList.remove('row-selected');
  }}

  selectedAbbr = abbr;
  const node = document.getElementById('node-' + abbr);
  const row = document.getElementById('row-' + abbr);
  if (node) node.classList.add('selected');
  if (row) row.classList.add('row-selected');

  const d = REGION_DATA[abbr];
  const panel = document.getElementById('detail-panel');
  if (!d) {{ return; }}
  panel.classList.add('filled');
  panel.innerHTML =
    '<div class="d-name">' + d.glyph + ' ' + d.name + '</div>' +
    '<div class="d-row"><span>날씨</span><span>' + d.weather + '</span></div>' +
    '<div class="d-row"><span>기온</span><span>' + d.temperature.toFixed(1) + '\u2103</span></div>' +
    '<div class="d-row"><span>습도</span><span>' + d.humidity + '%</span></div>' +
    '<div class="d-row"><span>지형</span><span>' + d.terrain + '</span></div>' +
    '<div class="d-desc">' + d.description + '</div>' +
    '<div class="d-pokemon">' + d.pokemon.map(function(p) {{
      return '<span class="d-pokemon-chip">' + p + '</span>';
    }}).join('') + '</div>';
}}
</script>
</body>
</html>
"""


def generate_forecast_dashboard(day_of_year: int, seed: int = 7,
                                 region_name: str = "이름없는 지방",
                                 out_dir: str = ".",
                                 out_filename: str = None) -> str:
    cmap = build_example_map()
    sim = RegionClimateSimulator(cmap, seed=seed)

    results = None
    start = day_of_year - 10 if day_of_year > 10 else 1
    for d in range(start, day_of_year + 1):
        results = sim.simulate_day(d)

    forecast_lines = sim.generate_forecast()
    headline = forecast_lines[0] if forecast_lines else "오늘은 특별한 기상 변화가 없습니다."
    forecast_paragraphs = "\n".join(f"<p>{line}</p>" for line in forecast_lines)

    order = list(NODE_LAYOUT.keys())
    html = PAGE_TEMPLATE.format(
        region_name=region_name,
        day_label=f"DAY {day_of_year:03d}",
        day_of_year=day_of_year,
        season=season_of_day(day_of_year),
        headline=headline,
        map_svg=build_map_svg(cmap, results),
        table_rows=build_table_rows(results, order),
        forecast_paragraphs=forecast_paragraphs,
        region_data_json=build_region_data_json(cmap, results),
    )

    # out_filename을 지정하면 매일 같은 파일(예: latest.html)을 덮어써서
    # 밴드에 올릴 링크 주소가 매일 바뀌지 않도록 할 수 있음
    filename = out_filename or f"forecast_day{day_of_year:03d}.html"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path, headline


def build_band_announcement(headline: str, dashboard_url: str,
                             region_name: str = "이름없는 지방") -> str:
    """밴드에 자동 게시할 짧은 텍스트(헤드라인 + 대시보드 링크)를 만든다."""
    return (
        f"{region_name} 기상청 오늘의 예보\n"
        f"{headline}\n"
        f"자세한 지역별 날씨는 여기서 확인하세요\n"
        f"{dashboard_url}"
    )


if __name__ == "__main__":
    path, headline = generate_forecast_dashboard(
        day_of_year=15, seed=11, region_name="이탈리아 지방"
    )
    print("saved:", path)
    print("headline:", headline)
    print("--- band post preview ---")
    print(build_band_announcement(headline, "https://example.com/weather/latest.html", "이탈리아 지방"))
