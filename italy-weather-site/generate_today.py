# -*- coding: utf-8 -*-
"""
GitHub Actions에서 매일 자정 실행되는 러너 스크립트.

실제 날짜의 day-of-year를 계산해서 오늘자 대시보드를 만들고,
docs/index.html 로 저장한다. (GitHub Pages가 /docs 폴더를 그대로
서빙하도록 설정해두면, 이 파일이 곧 공개 URL의 첫 화면이 된다.)
"""

import datetime
from weather_broadcast_dashboard import generate_forecast_dashboard

# 필요에 맞게 바꿔서 쓰세요.
REGION_NAME = "이탈리아 지방"
SEED = 11  # 지방 고유 시드 - 바꾸면 완전히 다른 기후 패턴이 생성됨


def main():
    day_of_year = datetime.date.today().timetuple().tm_yday
    path, headline = generate_forecast_dashboard(
        day_of_year=day_of_year,
        seed=SEED,
        region_name=REGION_NAME,
        out_dir="docs",
        out_filename="index.html",
    )
    print("generated:", path)
    print("headline:", headline)


if __name__ == "__main__":
    main()
