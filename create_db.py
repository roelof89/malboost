# create SQLite db
from app imort db

db.create_all()
db.session.commit()