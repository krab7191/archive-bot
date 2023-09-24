from sqlalchemy import Column, Text, DateTime, Integer
from base_class import Base, session

class Test(Base):
    __tablename__= "test"
    id = Column(Integer, primary_key=True)
    text = Column(Text)
    ts = Column(DateTime)

db = session()
test_rows = db.query(Test)
# print(test_rows)
for row in test_rows:
    print(row.value)


# once query is created can run updates like this
# test_rows.text = requst.text