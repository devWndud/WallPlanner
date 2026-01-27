from datetime import datetime, date, timedelta
from io import BytesIO
import math
import os

from flask import Flask, request, send_file, abort
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        abort(400, description=f"Invalid date format for value '{value}', expected YYYY-MM-DD")


def get_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Try to load a nicer system font; fall back to PIL's default if unavailable.
    """
    possible_fonts = [
        # Windows – 한글 지원 (맑은 고딕)
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/malgunbd.ttf",
        # macOS
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        # Linux (Noto / DejaVu 등)
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in possible_fonts:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    # Fallback
    return ImageFont.load_default()


def draw_life_calendar(
    goal: str,
    start_date: date,
    goal_date: date,
    width: int,
    height: int,
    dday_events: list | None = None,
) -> Image.Image:
    # Colors
    bg_color = (15, 15, 15)
    text_color = (220, 220, 220)
    accent_color = (255, 110, 70)
    done_color = (245, 245, 245)
    remaining_color = (70, 70, 70)
    dday_color = (120, 190, 255)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Title
    # 조금 더 크게, 원본 디자인 느낌에 가깝게
    title_font = get_font(size=int(height * 0.035))
    title_text = goal or "Life Calendar"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_y = int(height * 0.38)
    draw.text(
        ((width - title_w) // 2, title_y),
        title_text,
        fill=text_color,
        font=title_font,
    )

    # D-day summary text (multiple events) - content만 계산, 실제 위치는 하단 근처에서 그림
    today = date.today()
    dday_font = get_font(size=int(height * 0.02))

    parsed_ddays: list[tuple[date, str]] = []
    if dday_events:
        for e in dday_events:
            d_date = e.get("date")
            label = e.get("label") or ""
            if not isinstance(d_date, date):
                continue
            parsed_ddays.append((d_date, label))

    # Date calculations
    total_days = (goal_date - start_date).days + 1
    if total_days <= 0:
        total_days = 1

    elapsed_days = (min(today, goal_date) - start_date).days + 1
    elapsed_days = max(0, min(elapsed_days, total_days))
    days_left = max(0, (goal_date - today).days)
    progress_ratio = elapsed_days / total_days if total_days > 0 else 0

    # Grid layout (approximate to screenshot: several rows of dots centered)
    # 가로 점 개수 15칸
    cols = 15
    rows = math.ceil(total_days / cols)

    # 제목 아래에 일정 간격을 두고 그리드 배치
    grid_top = title_y + title_h + int(height * 0.06)
    grid_bottom = int(height * 0.58)
    grid_height = max(1, grid_bottom - grid_top)
    grid_width = int(width * 0.8)

    # 셀 크기와 원 크기를 분리해서 셀 사이에 여유 간격을 준다.
    # 가로/세로 간격이 같도록 cell_size를 공통으로 사용.
    cell_size = min(grid_width / cols, grid_height / rows)
    cell_w = cell_h = cell_size

    # 실제 사용되는 그리드 크기(가로/세로)를 다시 계산해서 정확히 중앙에 배치.
    used_grid_width = cell_size * cols
    used_grid_height = cell_size * rows
    extra_h_space = grid_width - used_grid_width
    extra_v_space = grid_height - used_grid_height

    grid_left = (width - used_grid_width) / 2
    grid_top = grid_top + max(0, extra_v_space / 2)

    # 가로/세로 모두 셀 크기의 70%만 사용해서 원들 사이 간격을 조금 더 넓게
    circle_diameter = cell_size * 0.7
    radius = circle_diameter / 2

    day_index = 0
    current_index = elapsed_days - 1 if elapsed_days > 0 else -1

    # Map from day index to d-day info (for coloring)
    dday_index_map: dict[int, tuple[date, str]] = {}
    if parsed_ddays:
        for d_date, label in parsed_ddays:
            idx = (d_date - start_date).days
            if 0 <= idx < total_days:
                dday_index_map[idx] = (d_date, label)

    for r in range(rows):
        for c in range(cols):
            if day_index >= total_days:
                break

            # 각 셀의 중앙에 위치시키기 (살짝 반올림해서 계단 현상 줄이기)
            cx = grid_left + cell_w * (c + 0.5)
            cy = grid_top + cell_h * (r + 0.5)

            if day_index == current_index and today <= goal_date:
                color = accent_color
            elif day_index in dday_index_map:
                color = dday_color
            elif day_index < elapsed_days - 1:
                color = done_color
            else:
                color = remaining_color

            bbox = [
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
            ]
            draw.ellipse(bbox, fill=color)

            day_index += 1

    # Bottom text (days left + percentage)
    info_font = get_font(size=int(height * 0.025))
    days_left_text = f"{days_left}d left"
    percent_text = f"{round(progress_ratio * 100)}%"

    days_bbox = draw.textbbox((0, 0), days_left_text, font=info_font)
    days_w = days_bbox[2] - days_bbox[0]
    # 하단 텍스트의 기준 Y (조금 위쪽)
    info_y = int(height * 0.73)

    sep = " · "
    sep_bbox = draw.textbbox((0, 0), sep, font=info_font)
    sep_w = sep_bbox[2] - sep_bbox[0]

    percent_bbox = draw.textbbox((0, 0), percent_text, font=info_font)
    percent_w = percent_bbox[2] - percent_bbox[0]

    # 먼저 여러 개의 D-day 텍스트를 info_y 기준으로 위에 쌓아 올림
    if parsed_ddays:
        dday_lines: list[str] = []
        total_dday_height = 0
        line_spacing = int(height * 0.005)

        for d_date, label in parsed_ddays:
            delta = (d_date - today).days
            if delta > 0:
                prefix = f"D-{delta}"
            elif delta == 0:
                prefix = "D-day"
            else:
                prefix = f"D+{abs(delta)}"

            text = f"{prefix}  {label}"
            dday_lines.append(text)
            bbox = draw.textbbox((0, 0), text, font=dday_font)
            line_h = bbox[3] - bbox[1]
            total_dday_height += line_h + line_spacing

        total_dday_height -= line_spacing  # 마지막 줄 이후 여백 제거
        # D-day 블록이 info_y 기준으로 살짝 위에 위치하도록 시작 위치 계산
        dday_start_y = info_y - total_dday_height - int(height * 0.015)

        current_y = dday_start_y
        for text in dday_lines:
            bbox = draw.textbbox((0, 0), text, font=dday_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.text(
                ((width - text_w) // 2, current_y),
                text,
                fill=text_color,
                font=dday_font,
            )
            current_y += text_h + line_spacing

    # 그 아래에 Xd left · YY% 표시
    total_w = days_w + sep_w + percent_w
    x = (width - total_w) // 2
    draw.text((x, info_y), days_left_text, fill=accent_color, font=info_font)
    x += days_w
    draw.text((x, info_y), sep, fill=text_color, font=info_font)
    x += sep_w
    draw.text((x, info_y), percent_text, fill=text_color, font=info_font)

    return img


@app.route("/goal")
def goal_image():
    goal = request.args.get("goal", default="Life Calendar")
    goal_date_str = request.args.get("goal_date")
    start_date_str = request.args.get("start_date")

    if not goal_date_str or not start_date_str:
        abort(400, description="Missing required query params 'goal_date' and/or 'start_date'")

    goal_date = parse_date(goal_date_str)
    start_date = parse_date(start_date_str)

    try:
        width = int(request.args.get("width", 1080))
        height = int(request.args.get("height", 2340))
    except ValueError:
        abort(400, description="Invalid 'width' or 'height', must be integers")

    width = max(200, min(width, 4000))
    height = max(200, min(height, 4000))

    # Parse multiple D-day events from query string.
    # Format: ddays=YYYY-MM-DD:Title,YYYY-MM-DD:Another Title
    raw_ddays = request.args.get("ddays", "")
    dday_events = []
    if raw_ddays:
        for part in raw_ddays.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" not in part:
                # If no label is provided, just treat the whole thing as the date
                date_str, label = part, ""
            else:
                date_str, label = part.split(":", 1)
            try:
                d_date = parse_date(date_str.strip())
            except Exception:
                # parse_date already aborts with 400, but in case it's overridden,
                # skip invalid entries here.
                continue
            dday_events.append({"date": d_date, "label": label.strip()})

    img = draw_life_calendar(goal, start_date, goal_date, width, height, dday_events=dday_events)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="image/png",
        as_attachment=False,
        download_name="life_calendar.png",
    )


if __name__ == "__main__":
    app.run(debug=True)


