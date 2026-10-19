"""
Synthetic Oura dump in the raw API shape, for tests and examples.

Nothing here comes from a real person. Dates start at an arbitrary fixed day and
every value is generated from a seeded RNG around the textbook-shaped offsets
below, so tests are reproducible and the repo never needs real data.
"""
import random
from datetime import date, datetime, timedelta

START = date(2030, 1, 1)


def make_dump(days=150, cycle_len=28, ovulation_day=14, ovulatory=True, seed=7,
              luteal=None):
    """
    Build an oura_data.json-shaped dict.

    Ovulatory: luteal days (after ovulation_day) get +0.30 °C skin temp, +2.5 bpm
    sleeping HR, -5 ms HRV and +0.4 breaths/min. Anovulatory: flat. Period tags
    cover cycle days 1-4.
    """
    rnd = random.Random(seed)
    luteal = luteal or {"temp": 0.30, "rhr": 2.5, "hrv": -5.0, "br": 0.4}
    readiness, sleep_daily, activity, spo2, stress, sleep, tags = [], [], [], [], [], [], []
    for i in range(days):
        day = START + timedelta(days=i)
        cd = i % cycle_len + 1
        lut = ovulatory and cd > ovulation_day
        iso = day.isoformat()
        temp = rnd.gauss(0, 0.08) + (luteal["temp"] if lut else 0.0)
        rhr = 58 + rnd.gauss(0, 1.2) + (luteal["rhr"] if lut else 0.0)
        hrv = 62 + rnd.gauss(0, 4) + (luteal["hrv"] if lut else 0.0)
        br = 15.2 + rnd.gauss(0, 0.2) + (luteal["br"] if lut else 0.0)
        readiness.append({"day": iso, "score": 80 + rnd.randint(-5, 5),
                          "temperature_deviation": round(temp, 2),
                          "temperature_trend_deviation": round(temp / 2, 2)})
        sleep_daily.append({"day": iso, "score": 78 + rnd.randint(-6, 6)})
        activity.append({"day": iso, "steps": 8000 + rnd.randint(-2000, 2000),
                         "active_calories": 400 + rnd.randint(-80, 80),
                         "high_activity_time": rnd.randint(0, 40) * 60,
                         "medium_activity_time": rnd.randint(10, 60) * 60,
                         "sedentary_time": rnd.randint(7, 11) * 3600})
        spo2.append({"day": iso, "spo2_percentage": {"average": round(97 + rnd.gauss(0, 0.4), 1)},
                     "breathing_disturbance_index": rnd.randint(0, 4)})
        stress.append({"day": iso, "stress_high": rnd.randint(1000, 6000),
                       "recovery_high": rnd.randint(3000, 9000)})
        bed = datetime(day.year, day.month, day.day, 23, 0) - timedelta(days=1)
        bed += timedelta(minutes=rnd.randint(-20, 20))
        total = 7 * 3600 + rnd.randint(-1800, 1800)
        sleep.append({"day": iso, "type": "long_sleep",
                      "bedtime_start": bed.isoformat() + "+00:00",
                      "bedtime_end": (bed + timedelta(seconds=total + 1800)).isoformat() + "+00:00",
                      "total_sleep_duration": total, "rem_sleep_duration": 5400,
                      "deep_sleep_duration": 4800, "light_sleep_duration": total - 10200,
                      "awake_time": 1800, "latency": rnd.randint(300, 1200),
                      "restless_periods": rnd.randint(150, 300),
                      "efficiency": round(92 + rnd.gauss(0, 1.5)),
                      "average_heart_rate": round(rhr, 1), "lowest_heart_rate": round(rhr - 4),
                      "average_hrv": round(hrv), "average_breath": round(br, 2)})
        if cd <= 4:
            tags.append({"tag_type_code": "menstruation", "start_day": iso})
    end = START + timedelta(days=days - 1)
    return {
        "_meta": {"fetched_at": end.isoformat()},
        "daily_readiness": {"data": readiness}, "daily_sleep": {"data": sleep_daily},
        "daily_activity": {"data": activity}, "daily_spo2": {"data": spo2},
        "daily_stress": {"data": stress}, "sleep": {"data": sleep},
        "enhanced_tag": {"data": tags},
    }
