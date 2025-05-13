import pytz
from datetime import datetime

paris_tz = pytz.timezone("Europe/Paris")
now = datetime.now(paris_tz)
timestamp = now.timestamp()

print(timestamp)
print(datetime.fromtimestamp(timestamp))  # Affiche l'heure locale
print(datetime.utcfromtimestamp(timestamp))  # Affiche l'heure UTC
