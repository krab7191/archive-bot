from utils import fmt_json

def test_fmt_json():
  res = fmt_json({ "a": "b" })
  assert res == '{\n  "a": "b"\n}'