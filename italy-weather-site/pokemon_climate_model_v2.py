# -*- coding: utf-8 -*-
"""
포켓몬 TRPG 가상 지방 기후 시뮬레이터 v2
==========================================

이번 버전에서 추가된 것
------------------------
1) 기온 + 습도를 각각 모델링하고, 그 조합(+강수 여부)으로 날씨 라벨을 분류
   (쾌청/맑음/흐림/비/뇌우/눈/폭설/안개)
2) 지형 영향 반영: 고도(기온 감률), 해안 인접(기온 진폭 완화 + 습도 상승),
   산그림자(바람그늘, rain shadow: 산맥 뒤쪽은 건조해짐)
3) 실제 맵: 도시/도로를 노드로 하는 그래프(Map)를 만들고, 노드별로
   서로 다른 날씨가 나오게 함
4) '전선(기단)'이 맵 위를 이동하는 것을 시뮬레이션해서, 그 이동 경로를
   기반으로 일기예보 문장을 자동 생성 (정확도는 신경 쓰지 않음 -
   실제 이동에는 무작위성이 섞여 있어서 예보가 빗나갈 수도 있음)

설계 철학
---------
- "오늘의 상태는 어제 상태 + 계절/지형 기준값에만 의존한다"는 마르코프 성질은
  기온/습도(AR(1))와 전선의 이동(현재 위치 -> 인접 노드) 모두에 유지됩니다.
- 정확한 기상학 시뮬레이션이 아니라 TRPG용 "그럴듯한 연출"이 목적이므로,
  물리식 대신 직관적인 가중치/규칙 기반으로 단순화했습니다.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# =================================================================
# 0. 기본 상수
# =================================================================

SEASONS = ["봄", "여름", "가을", "겨울"]

# 강수/기온으로부터 최종 날씨 라벨을 정하기 위한 임계값들
FOG_HUMIDITY_THRESHOLD = 88
CLEAR_HUMIDITY_THRESHOLD = 35   # 이 이하면 "쾌청"
MILD_HUMIDITY_THRESHOLD = 60    # 이 이하면 "맑음", 넘으면 "흐림"
SNOW_TEMP_THRESHOLD = 1.0
HEAVY_PRECIP_THRESHOLD = 0.55
PRECIP_THRESHOLD = 0.15


# =================================================================
# 1. 지형/위치: 맵 그래프
# =================================================================

@dataclass
class Location:
    name: str
    kind: str = "도로"            # "도시" 또는 "도로"
    x: float = 0.0
    y: float = 0.0                # y가 클수록 북쪽(더 추운 위도)이라고 가정
    altitude: float = 0.0         # 고도(m)
    coastal: bool = False         # 바다와 인접한 지역인가
    mountain_shadow: float = 0.0  # 0(바람받이, 습윤) ~ 1(산그림자, 건조)
    front_spawn_weight: float = 1.0  # 이 지역에서 전선이 새로 생겨날 상대적 확률
    neighbors: List[str] = field(default_factory=list)


class ClimateMap:
    def __init__(self, prevailing_wind: Tuple[float, float] = (0.2, 1.0)):
        self.locations: Dict[str, Location] = {}
        # 탁월풍(계 전체에서 전선이 대체로 흘러가는 방향). (dx, dy) 벡터.
        # 예: (0.2, 1.0) -> 대체로 남->북으로 흐르되 약간 동쪽으로 치우침
        self.prevailing_wind = prevailing_wind

    def add_location(self, loc: Location):
        self.locations[loc.name] = loc

    def connect(self, a: str, b: str):
        """도로로 두 지역을 양방향 연결."""
        self.locations[a].neighbors.append(b)
        self.locations[b].neighbors.append(a)

    def neighbors(self, name: str) -> List[Location]:
        return [self.locations[n] for n in self.locations[name].neighbors]


# =================================================================
# 2. 지형을 반영한 계절 기준값 계산
# =================================================================

SEASON_BASELINE = {
    "T_AVG": 12.0,
    "T_AMPLITUDE": 13.0,
    "PEAK_DAY": 200,
    "H_BASE": {"봄": 60, "여름": 75, "가을": 58, "겨울": 55},  # 계절별 기준 습도(%)
}


def _day_to_month(day_of_year: int) -> int:
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    d = day_of_year
    for i, dim in enumerate(days_in_month, start=1):
        if d <= dim:
            return i
        d -= dim
    return 12


def season_of_day(day_of_year: int) -> str:
    day_of_year = ((day_of_year - 1) % 365) + 1
    month = _day_to_month(day_of_year)
    if month in (3, 4, 5):
        return "봄"
    if month in (6, 7, 8):
        return "여름"
    if month in (9, 10, 11):
        return "가을"
    return "겨울"


def baseline_temperature(loc: Location, day_of_year: int) -> float:
    """지형을 반영한 그날의 '평년' 기온."""
    p = SEASON_BASELINE
    angle = 2 * math.pi * (day_of_year - p["PEAK_DAY"]) / 365.0
    seasonal = p["T_AVG"] + p["T_AMPLITUDE"] * math.cos(angle)

    # 해안 지역은 연교차(계절에 따른 변동폭)가 완만해짐
    if loc.coastal:
        seasonal = p["T_AVG"] + (seasonal - p["T_AVG"]) * 0.65

    # 고도가 높을수록 추워짐: 표준 기온감률 약 -6.5도 / 1000m
    lapse = -6.5 * (loc.altitude / 1000.0)

    return seasonal + lapse


def baseline_humidity(loc: Location, season: str) -> float:
    """지형을 반영한 그 계절의 '평년' 습도(%)."""
    h = SEASON_BASELINE["H_BASE"][season]

    if loc.coastal:
        h += 12  # 해안: 습도 상승

    # 산그림자(바람그늘) 정도에 비례해 건조해짐, 반대로 바람받이는 습해짐
    h += (0.4 - loc.mountain_shadow) * 25

    return max(15.0, min(95.0, h))


# =================================================================
# 3. 전선(기단) - 맵 위를 이동하며 날씨를 몰고 다니는 존재
# =================================================================

FRONT_KIND_BY_SEASON = {
    "봄": ["저기압", "약한 전선"],
    "여름": ["저기압", "장마전선", "국지성 뇌우"],
    "가을": ["약한 전선", "저기압"],
    "겨울": ["한랭전선", "저기압"],
}

# 전선 종류별 성질: 기온 보정, 습도 보정, 강도 감쇠 속도
FRONT_PROPERTIES = {
    "한랭전선": {"temp_shift": -8.0, "humidity_shift": 5, "decay": 0.22},
    "저기압": {"temp_shift": -1.0, "humidity_shift": 15, "decay": 0.30},
    "약한 전선": {"temp_shift": -2.0, "humidity_shift": 10, "decay": 0.35},
    "장마전선": {"temp_shift": -1.5, "humidity_shift": 25, "decay": 0.18},
    "국지성 뇌우": {"temp_shift": -3.0, "humidity_shift": 20, "decay": 0.5},
}


@dataclass
class WeatherFront:
    kind: str
    location: str        # 현재 위치한 노드 이름
    strength: float = 1.0  # 0~1, 시간이 지나며 감쇠
    age: int = 0


def most_likely_next_location(front: WeatherFront, cmap: ClimateMap) -> Optional[str]:
    """무작위성 없이, 탁월풍 방향과 가장 잘 맞는 인접 노드를 하나 고른다.
    -> 일기예보용 '예상 이동 경로' 계산에 사용."""
    cur = cmap.locations[front.location]
    wind = cmap.prevailing_wind
    best, best_score = None, -1e9
    for nb in cmap.neighbors(front.location):
        dx, dy = nb.x - cur.x, nb.y - cur.y
        dist = math.hypot(dx, dy) or 1.0
        score = (dx * wind[0] + dy * wind[1]) / dist
        if score > best_score:
            best_score, best = score, nb.name
    return best


class FrontSystem:
    """맵 전체에서 활동 중인 전선들을 관리."""

    def __init__(self, rng: random.Random):
        self.active: List[WeatherFront] = []
        self.rng = rng

    def step(self, cmap: ClimateMap, season: str):
        """하루 진행: 기존 전선 이동/감쇠 + 새 전선 발생."""
        # 1) 기존 전선 이동 (탁월풍 방향 + 약간의 무작위성 -> 예보가 빗나갈 수 있음)
        still_active = []
        for front in self.active:
            front.age += 1
            decay = FRONT_PROPERTIES[front.kind]["decay"] * 0.3
            if len(cmap.locations[front.location].neighbors) == 1:
                decay *= 2.0  # 막다른 지역(맵 끝자락)에 도달하면 더 빨리 소멸
            front.strength -= decay
            if front.strength <= 0.05 or front.age > 6:
                continue  # 소멸

            if self.rng.random() < 0.8:  # 80% 확률로 예측 방향대로 이동
                nxt = most_likely_next_location(front, cmap)
            else:  # 20% 확률로 아무 인접 노드나 -> 예보 오차 요인
                nbs = cmap.locations[front.location].neighbors
                nxt = self.rng.choice(nbs) if nbs else None

            if nxt:
                front.location = nxt
            still_active.append(front)
        self.active = still_active

        # 2) 새 전선 발생
        kinds = FRONT_KIND_BY_SEASON[season]
        for loc in cmap.locations.values():
            spawn_chance = 0.015 * loc.front_spawn_weight
            if self.rng.random() < spawn_chance:
                kind = self.rng.choice(kinds)
                self.active.append(WeatherFront(kind=kind, location=loc.name, strength=1.0))

    def influence_at(self, location_name: str) -> Tuple[float, Optional[WeatherFront]]:
        """해당 지역에 미치는 전선 영향력(0~1)과, 가장 강하게 영향을 주는 전선."""
        best_strength, best_front = 0.0, None
        for front in self.active:
            if front.location == location_name:
                s = front.strength
            elif location_name in [n for n in self._nb_names(front.location)]:
                s = front.strength * 0.4  # 인접 지역은 절반 이하로 선제 영향
            else:
                s = 0.0
            if s > best_strength:
                best_strength, best_front = s, front
        return best_strength, best_front

    def _nb_names(self, location_name: str) -> List[str]:
        return self._cmap_ref.locations[location_name].neighbors if self._cmap_ref else []

    # step()에서 맵을 참조할 수 있도록 별도 바인딩 (간단한 트릭)
    _cmap_ref: Optional[ClimateMap] = None

    def bind_map(self, cmap: ClimateMap):
        self._cmap_ref = cmap


# =================================================================
# 4. 날씨 라벨 분류
# =================================================================

def classify_weather(temp: float, humidity: float, precip_intensity: float) -> str:
    """기온 + 습도 + 강수강도(0~1)로부터 최종 날씨 라벨을 결정."""
    if precip_intensity > PRECIP_THRESHOLD:
        if temp <= SNOW_TEMP_THRESHOLD:
            return "폭설" if precip_intensity > HEAVY_PRECIP_THRESHOLD else "눈"
        if precip_intensity > HEAVY_PRECIP_THRESHOLD:
            return "뇌우"
        return "비"
    else:
        if humidity >= FOG_HUMIDITY_THRESHOLD:
            return "안개"
        if humidity <= CLEAR_HUMIDITY_THRESHOLD:
            return "쾌청"
        if humidity <= MILD_HUMIDITY_THRESHOLD:
            return "맑음"
        return "흐림"


WARNING_BY_LABEL = {
    "폭설": "폭설경보",
    "눈": "대설주의보",
    "뇌우": "강풍·호우주의보",
    "비": "호우주의보",
    "안개": "농무주의보",
    "흐림": None,
    "맑음": None,
    "쾌청": None,
}


# =================================================================
# 5. 지역별 상태(기온/습도의 AR(1) 추적)
# =================================================================

@dataclass
class LocationState:
    prev_temp_dev: float = 0.0
    prev_humidity_dev: float = 0.0


@dataclass
class DayResult:
    day_of_year: int
    location: str
    season: str
    temperature: float
    humidity: float
    weather: str


class RegionClimateSimulator:
    def __init__(self, cmap: ClimateMap, seed: Optional[int] = None,
                 temp_rho: float = 0.6, temp_sigma: float = 1.1,
                 humid_rho: float = 0.5, humid_sigma: float = 6.0):
        self.map = cmap
        self.rng = random.Random(seed)
        self.fronts = FrontSystem(self.rng)
        self.fronts.bind_map(cmap)
        self.states: Dict[str, LocationState] = {
            name: LocationState() for name in cmap.locations
        }
        self.temp_rho, self.temp_sigma = temp_rho, temp_sigma
        self.humid_rho, self.humid_sigma = humid_rho, humid_sigma

    def _step_location(self, loc: Location, day_of_year: int, season: str) -> DayResult:
        state = self.states[loc.name]
        influence, front = self.fronts.influence_at(loc.name)

        temp_shift = FRONT_PROPERTIES[front.kind]["temp_shift"] * influence if front else 0.0
        humid_shift = FRONT_PROPERTIES[front.kind]["humidity_shift"] * influence if front else 0.0

        base_t = baseline_temperature(loc, day_of_year)
        noise_t = self.rng.gauss(0, self.temp_sigma)
        dev_t = self.temp_rho * state.prev_temp_dev + noise_t
        state.prev_temp_dev = dev_t
        temperature = round(base_t + temp_shift + dev_t, 1)

        base_h = baseline_humidity(loc, season)
        noise_h = self.rng.gauss(0, self.humid_sigma)
        dev_h = self.humid_rho * state.prev_humidity_dev + noise_h
        state.prev_humidity_dev = dev_h
        humidity = max(5.0, min(100.0, base_h + humid_shift + dev_h))

        precip_intensity = influence * (humidity / 100.0) if front else 0.0
        weather = classify_weather(temperature, humidity, precip_intensity)

        return DayResult(day_of_year, loc.name, season, temperature, round(humidity, 1), weather)

    def simulate_day(self, day_of_year: int) -> Dict[str, DayResult]:
        season = season_of_day(day_of_year)
        self.fronts.step(self.map, season)
        return {
            name: self._step_location(loc, day_of_year, season)
            for name, loc in self.map.locations.items()
        }

    def generate_forecast(self) -> List[str]:
        """현재 활성화된 전선들을 바탕으로 '내일 예상' 방송 문구를 생성.
        (무작위 이동 요소가 있어 실제로는 빗나갈 수 있음)"""
        lines = []
        for front in self.fronts.active:
            nxt = most_likely_next_location(front, self.map)
            if not nxt:
                continue
            cur_loc, nxt_loc = self.map.locations[front.location], self.map.locations[nxt]
            dy, dx = nxt_loc.y - cur_loc.y, nxt_loc.x - cur_loc.x
            if abs(dy) >= abs(dx):
                direction = "북상" if dy > 0 else "남하"
            else:
                direction = "동진" if dx > 0 else "서진"

            # 도착지 예상 날씨를 대략적으로 미리 계산 (예보용 근사치)
            approx_temp = baseline_temperature(nxt_loc, 200) + \
                FRONT_PROPERTIES[front.kind]["temp_shift"] * min(front.strength, 1.0)
            approx_humidity = baseline_humidity(nxt_loc, season_of_day(200)) + \
                FRONT_PROPERTIES[front.kind]["humidity_shift"] * min(front.strength, 1.0)
            approx_precip = min(front.strength, 1.0) * (approx_humidity / 100.0)
            predicted_label = classify_weather(approx_temp, approx_humidity, approx_precip)
            warning = WARNING_BY_LABEL.get(predicted_label)

            if warning:
                lines.append(
                    f"{cur_loc.name}에 있던 {front.kind}이 {direction}하면서, "
                    f"{nxt_loc.name}에 {warning}가 발효될 가능성이 있습니다."
                )
            else:
                lines.append(
                    f"{cur_loc.name} 부근의 {front.kind}은 {direction}하며 세력이 약해질 전망입니다."
                )
        if not lines:
            lines.append("현재 지방 전역에 특별한 기상 변화는 관측되지 않았습니다.")
        return lines


# =================================================================
# 6. 데모: 예시 지방 맵
# =================================================================

def build_example_map() -> ClimateMap:
    """참고 지도(이탈리아 아펜니노 초안)의 피렌체 이북 도시 + 사용자가 구술한
    도로망을 반영한 지방 맵.

    구도: 토리노-1번도로-밀라노-2번도로-베로나-3번도로-베네치아-4번도로-트리에스테
    가 서->동 수평 본선. 밀라노에서 갈라져 나온 지선이
    5번도로-파르마-6번도로-볼로냐-7번도로-피렌체-8번도로-피사-9번도로-제노바-10번도로
    를 거쳐 다시 토리노로 돌아오는 순환로를 이룬다. (라벤나는 아직 도로 연결 없음)

    위치 관계(중요):
    - 볼로냐 바로 아래에 피렌체 (같은 x축)
    - 7번도로는 볼로냐-피렌체 축선에서 반 칸 오른쪽으로 살짝 비껴서 배치 (라벨 겹침 방지)
    - 피렌체 왼쪽에 8번도로, 8번도로 왼쪽에 피사
    - 피사와 제노바 사이에 9번도로
    - 10번도로는 제노바의 정서(正西)이자 토리노의 정남(正南)에 위치

    Location.x/y는 화면 좌표가 아니라 물리(바람 방향) 계산용 좌표다."""
    cmap = ClimateMap(prevailing_wind=(0.2, 1.0))

    # (이름, 종류, 해안여부, 고도, 산그림자, 물리 좌표 x, y)
    spec = [
        ("토리노",     "도시", False, 240, 0.0, 0,   0),
        ("1번도로",    "도로", False, 180, 0.0, 1,   0),
        ("밀라노",     "도시", False, 120, 0.0, 2,   0),
        ("2번도로",    "도로", False, 90,  0.0, 3,   0),
        ("베로나",     "도시", False, 60,  0.0, 4,   0),
        ("3번도로",    "도로", False, 30,  0.0, 5,   0),
        ("베네치아",   "도시", True,  1,   0.0, 6,   0),
        ("4번도로",    "도로", True,  2,   0.0, 7,   0),
        ("트리에스테", "도시", True,  2,   0.0, 8,   0),

        ("5번도로",    "도로", False, 80,  0.0, 2.5, 1),
        ("파르마",     "도시", False, 55,  0.0, 3.5, 1),
        ("6번도로",    "도로", False, 150, 0.0, 4.5, 2),
        ("볼로냐",     "도시", False, 54,  0.0, 5.5, 3),
        ("7번도로",    "도로", False, 700, 0.3, 6.0, 4),   # 볼로냐-피렌체 축선에서 반 칸 오른쪽
        ("피렌체",     "도시", False, 50,  0.0, 5.5, 5),   # 볼로냐와 같은 x축(바로 아래)
        ("8번도로",    "도로", False, 30,  0.0, 4.5, 5),   # 피렌체 왼쪽
        ("피사",       "도시", True,  5,   0.0, 3.5, 5),   # 8번도로 왼쪽
        ("9번도로",    "도로", True,  100, 0.0, 2.5, 4),   # 피사와 제노바 사이
        ("제노바",     "도시", True,  20,  0.0, 1.5, 3),
        ("10번도로",   "도로", False, 500, 0.4, 0,   3),

        ("라벤나",     "도시", True,  3,   0.0, 6.5, 3),
    ]

    for name, kind, coastal, altitude, shadow, px, py in spec:
        cmap.add_location(Location(
            name, kind, x=px, y=py, altitude=altitude,
            coastal=coastal, mountain_shadow=shadow, front_spawn_weight=1.0,
        ))

    # 서-동 본선
    main_chain = ["토리노", "1번도로", "밀라노", "2번도로", "베로나",
                  "3번도로", "베네치아", "4번도로", "트리에스테"]
    for a, b in zip(main_chain, main_chain[1:]):
        cmap.connect(a, b)

    # 밀라노에서 갈라져 나와 다시 토리노로 돌아오는 순환 지선
    loop = ["밀라노", "5번도로", "파르마", "6번도로", "볼로냐", "7번도로",
            "피렌체", "8번도로", "피사", "9번도로", "제노바", "10번도로", "토리노"]
    for a, b in zip(loop, loop[1:]):
        cmap.connect(a, b)

    # 라벤나는 아직 도로 연결 없음 - 추후 배치 예정

    return cmap


if __name__ == "__main__":
    cmap = build_example_map()
    sim = RegionClimateSimulator(cmap, seed=7)

    start_day = 340  # 겨울 초입 예시
    for offset in range(5):
        day = start_day + offset
        results = sim.simulate_day(day)

        print(f"\n===== {day}일차 ({season_of_day(day)}) 지역별 날씨 =====")
        print(f"{'지역':>8} {'기온(℃)':>8} {'습도(%)':>8} {'날씨':>6}")
        for name, r in results.items():
            print(f"{name:>8} {r.temperature:>8.1f} {r.humidity:>8.1f} {r.weather:>6}")

        print("--- 내일 예보 ---")
        for line in sim.generate_forecast():
            print(" -", line)
