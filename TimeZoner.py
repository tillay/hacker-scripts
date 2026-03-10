from datetime import datetime, timezone, timedelta
import pytz, time

now = datetime.now().astimezone()
def a(num): return f"\033[{num}m"
matches, their_offset = [], None

print(f"\n{a(4)}{a(96)}Ultra Supreme Timezone Reverser 3000 Ultimate Edition\n{a(0)}")

your_time_str = input(f"{a(4)}{a(31)}Your{a(0)} time message was sent at ({a(34)}HH{a(0)}:{a(31)}MM{a(0)}): ")
their_time_str = input(f"{a(4)}{a(32)}Their{a(0)} time message was sent at ({a(34)}HH{a(0)}:{a(31)}MM{a(0)}): ")
day_sent = input(f"Day message sent ({a(32)}MM{a(0)}/{a(33)}DD{a(0)}) (optional): ").split("/")
if len(day_sent) < 2: day_sent = [now.month, now.day]

try:
    month, day = int(day_sent[0]), int(day_sent[1])
    your_offset = datetime.fromtimestamp(time.mktime(datetime(now.year, month, day, now.hour, now.minute).timetuple())).astimezone().utcoffset().total_seconds() / 3600
    utc_ref = datetime.strptime(your_time_str, "%H:%M").replace(year=now.year, month=month, day=day, tzinfo=timezone(timedelta(hours=your_offset))).astimezone(pytz.UTC)
    their_clock = datetime.strptime(their_time_str, "%H:%M").replace(year=now.year, month=month, day=day)
except ValueError:
    print(f"{a(91)}Malformed time or date!{a(0)}")
    exit(1)

for country, timezones in pytz.country_timezones.items():
    for zone in timezones:
        pytz_zone = pytz.timezone(zone)
        local_time = utc_ref.astimezone(pytz_zone)

        local_minutes = local_time.hour * 60 + local_time.minute
        target_minutes = their_clock.hour * 60 + their_clock.minute

        diff = min(abs(local_minutes - target_minutes), 1440 - abs(local_minutes - target_minutes))
        pretty_timezone = str(pytz_zone).split("/")[1].replace("_", " ")

        if diff <= 14 and not any(name == pretty_timezone for _, name in matches):
            their_offset = local_time.utcoffset().total_seconds() / 3600
            matches.append([country, pretty_timezone])

if their_offset is None:
    print(f"{a(93)}No matching timezones found!{a(0)}")
    exit(1)
else:
    print(f"\nYour UTC offset: {a(31)}{'+' if your_offset >= 0 else ''}{your_offset}")
    print(f"{a(0)}Sender UTC offset: {a(93)}{'+' if their_offset >= 0 else ''}{their_offset}{a(0)}")
    print(f"Sender offset from you: {a(92)}{'+' if their_offset >= your_offset else ''}{their_offset - your_offset}")
    if input(f"\n{a(0)}Found {a(93)}{len(matches)}{a(0)} matches. Print matches? Y/n: ").lower() in ["y", ""]:
        for pair in matches: print(f"{a(96)}{pytz.country_names[pair[0]]}{a(0)} - {a(94)}{pair[1]}{a(0)}")
