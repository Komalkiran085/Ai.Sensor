from datetime import datetime, timezone


class ShiftSimulator:
    SHIFTS = [
        {"name": "Morning", "start_hour": 6, "end_hour": 14},
        {"name": "Afternoon", "start_hour": 14, "end_hour": 22},
        {"name": "Night", "start_hour": 22, "end_hour": 6},
    ]
    CHANGEOVER_MINUTES = 15

    def get_current_shift(self) -> dict:
        hour = datetime.now(timezone.utc).hour
        for s in self.SHIFTS:
            if s["start_hour"] <= hour < s["end_hour"] or (s["start_hour"] > s["end_hour"] and (hour >= s["start_hour"] or hour < s["end_hour"])):
                minutes_into = (hour - s["start_hour"]) * 60 + datetime.now(timezone.utc).minute
                minutes_left = (s["end_hour"] - s["start_hour"]) * 60 - minutes_into if s["end_hour"] > s["start_hour"] else ((24 - s["start_hour"] + s["end_hour"]) * 60 - minutes_into)
                return {
                    "shift_name": s["name"],
                    "start_hour": s["start_hour"],
                    "end_hour": s["end_hour"],
                    "minutes_remaining": max(0, minutes_left),
                    "changeover_soon": minutes_left <= self.CHANGEOVER_MINUTES,
                    "is_changeover": minutes_left <= 5,
                    "fatigue_risk": minutes_into > 360,
                }
        return {"shift_name": "Unknown", "changeover_soon": False, "is_changeover": False, "fatigue_risk": False, "minutes_remaining": 0}
